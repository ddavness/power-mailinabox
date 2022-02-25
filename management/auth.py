from daemon_error import AuthenticationServiceError, AUTH_STATUS, TRUSTED_ORIGIN, LOGIN_STATUS
import os
import os.path
import hmac
import json
import secrets
import hashlib
import utils

from base64 import urlsafe_b64encode as to_b64, urlsafe_b64decode as from_b64
from datetime import timedelta
from expiringdict import ExpiringDict
from math import inf
from mailconfig import get_mail_password, get_mail_user_privileges
from mfa import get_hash_mfa_state, validate_totp_token

DEFAULT_KEY_PATH = "/var/lib/mailinabox/api.key"
DEFAULT_AUTH_REALM = "Mail-in-a-Box Management Server"

class AuthService:
	def __init__(self):
		self.auth_realm = DEFAULT_AUTH_REALM
		self.key_path = DEFAULT_KEY_PATH
		self.init_system_api_key()

		self.trusted_origin_tokens = ExpiringDict(
			max_len=inf,
			max_age_seconds=timedelta(hours=60).total_seconds()
		)
		self.login_confirmation_tokens = ExpiringDict(
			max_len=inf,
			max_age_seconds=timedelta(minutes=10).total_seconds()
		)
		self.long_lived_sessions = ExpiringDict(
			max_len=inf,
			max_age_seconds=timedelta(hours=48).total_seconds()
		)
		self.short_lived_sessions = ExpiringDict(
			max_len=inf,
			max_age_seconds=timedelta(hours=6).total_seconds()
		)

	def init_system_api_key(self):
		"""Write an API key to a local file so local processes can use the API"""

		def create_file_with_mode(path, mode):
			# Based on answer by A-B-B: http://stackoverflow.com/a/15015748
			old_umask = os.umask(0)
			try:
				return os.fdopen(os.open(path, os.O_WRONLY | os.O_CREAT, mode), "w")
			finally:
				os.umask(old_umask)

		ctkey = secrets.token_bytes(64)

		os.makedirs(os.path.dirname(self.key_path), exist_ok=True)

		with create_file_with_mode(self.key_path, 0o640) as key_file:
			key_file.write(to_b64(ctkey).decode() + '\n')

		self.key = self.__genhash(ctkey)

	def __genhash(self, tokenbytes):
		"""
		Given a token, creates a semi-secure hash of it (i.e. not as strong as a password
		hash, but certainly not practical to crack before the token itself expires).

		The hash is not salted because otherwise we'd be unable to identify the bearer (an user
		can have multiple active tokens).

		The time to generate the hash is non-trivial but shouldn't be noticeable (<0.1s).
		"""

		hashed = tokenbytes
		for _ in range(1000):
			h = hashlib.sha3_512()
			h.update(hashed)
			hashed = h.digest()

		return hashed

	def check_trusted_origin(self, request):
		"""
		Test whether the Trusted-Origin-Token cookie and the X-Trusted-Origin-Token
		header are correctly set up,
		"""
		trusted_origin = request.cookies.get("_Host-Trusted-Origin-Token", "")
		trusted_origin_header = request.headers.get("X-Trusted-Origin-Token", None)
		toh = self.__genhash(from_b64(trusted_origin))

		if self.trusted_origin_tokens.get(toh, False):
			if trusted_origin == trusted_origin_header:
				# Chances that this is a CSFR attack are next to none. Origin is trusted.
				return True
			elif trusted_origin_header is None:
				# No header has been sent. This might still be a legitimate request, but do
				# not allow unsafe operations (aka everything except the document root)
				raise AuthenticationServiceError(TRUSTED_ORIGIN.HEADER_MISSING)
			else:
				# The header exists but is not equal to the token passed by the cookie.
				# Looks like a forged request
				raise AuthenticationServiceError(TRUSTED_ORIGIN.HEADER_MISMATCH)
		else:
			raise AuthenticationServiceError(TRUSTED_ORIGIN.TOKEN_INVALID)

	def authenticate_bearer(self, request):
		"""
		Test if the HTTP Authorization header matches a valid bearer key.

		Returns a tuple of the user's email address and a list of user privileges (e.g.
		("my@email", []) or ("my@email", ["admin"]);

		If the bearer is system API key, the user's email is returned as None since
		this key is not associated with a user.
		"""

		def parse_http_authorization_header(header):
			# Expects a Bearer token (for API usage only)
			if " " not in header:
				return None
			scheme, key = header.split(maxsplit=1)
			if scheme != "Bearer":
				return None
			return self.__genhash(from_b64(key))

		key = parse_http_authorization_header(request.headers.get("Authorization", ""))

		# If user passed the system API key, grant administrative privs. This key
		# is not associated with a user.
		if key == self.key:
			return (None, ["admin"])

		# TODO: User-generated API keys

		raise AuthenticationServiceError(AUTH_STATUS.TOKEN_INVALID)

	def authenticate(self, request, env):
		"""
		Test if the cookie sent with the request matches a currently active session.

		Returns a tuple of the user's email address and list of user privileges (e.g.
		("my@email", []) or ("my@email", ["admin"]);
		"""

		auth_cookie = request.cookies.get("_Host-Authentication-Token", "")

		ach = self.__genhash(from_b64(auth_cookie))
		short = self.short_lived_sessions.get(ach, None)
		long = self.long_lived_sessions.get(ach, None)

		if short is not None or long is not None:
			status = short if short is not None else long
			user = status.get("user")
			if status.get("validation") != self.create_validation_state_token(user, env):
				# Token is no longer valid due to a password/2FA configuration change
				self.invalidate_authentication_token(auth_cookie)
				raise AuthenticationServiceError(AUTH_STATUS.TOKEN_INVALID)

			# Get privileges for authorization. This call should never fail because by this
			# point we know the email address is a valid user --- unless the user has been
			# deleted after the session was granted. On error the call will return a tuple
			# of an error message and an HTTP status code.
			privs = get_mail_user_privileges(user, env)
			if isinstance(privs, tuple):
				raise ValueError(privs[0])

			return (user, privs)
		else:
			# The token doesn't exist, is invalid or has expired
			raise AuthenticationServiceError(AUTH_STATUS.TOKEN_INVALID)

	def attempt_login(self, payload, env):
		user = payload.get("username", None)
		issue_long_lived_token = payload.get("long_lived", False)
		password = payload.get("password", None)

		login_confirmation_token = payload.get("confirmation_token", None)
		totp_token = payload.get("totp_token", None)

		if login_confirmation_token is None:
			try:
				# Get the hashed password of the user, unless such user doesn't
				# exist.
				pw_hash = get_mail_password(user, env)

				# Use 'doveadm pw' to check credentials. doveadm will return
				# a non-zero exit status if the credentials are no good,
				# and check_call will raise an exception in that case.
				utils.shell('check_call', ["/usr/bin/doveadm", "pw", "-p", password, "-t", pw_hash])

				# User and password are ok

				if len(get_hash_mfa_state(user, env)) != 0:
					# MFA is enabled, require the respective token
					raise {
						"needs_mfa": True,
						"token": self.issue_confirmation_token(user)
					}
				else:
					# All good - issue a new authentication token!
					return {
						"needs_mfa": False,
						"token": self.issue_authentication_token(user, issue_long_lived_token, env)
					}
			except ValueError:
				# Login failed.
				raise AuthenticationServiceError(LOGIN_STATUS.USER_PASSWORD_INVALID)
		else:
			# We're performing the MFA part of the login

			# Validate that the confirmation token is valid
			cth = self.__genhash(from_b64(login_confirmation_token))
			if self.login_confirmation_tokens.get(cth, None) != user:
				raise AuthenticationServiceError(LOGIN_STATUS.MFA_AUTH_INVALID)

			try:
				validate_totp_token(user, totp_token, env)
				# Authentication complete!

				# Invalidate the confirmation token (as it's no longer going to be used)
				self.login_confirmation_tokens[cth] = None

				return self.issue_authentication_token(user, issue_long_lived_token, env)
			except ValueError:
				raise AuthenticationServiceError(LOGIN_STATUS.MFA_AUTH_INVALID)

	def create_validation_state_token(self, email, env):
		# Create a token that changes if the user's password or MFA options change
		# so that sessions become invalid if any of that information changes.
		msg = get_mail_password(email, env).encode("utf8")

		# Add to the message the current MFA state, which is a list of MFA information.
		# Turn it into a string stably.
		msg += b" " + json.dumps(get_hash_mfa_state(email, env),
								sort_keys=True).encode("utf8")

		# Make a HMAC using the system API key as a hash key.
		hash_key = self.key
		return hmac.new(hash_key, msg, digestmod="sha256").hexdigest()

	def __issue_token(self, where, what):
		token = secrets.token_bytes(64)
		where[self.__genhash(token)] = what

		return to_b64(token)

	def issue_authentication_token(self, username, islong, env):
		contents = {
			"user": username,
			"validation": self.create_validation_state_token(username, env)
		}
		if islong:
			return self.__issue_token(self.long_lived_sessions, contents)
		else:
			return self.__issue_token(self.short_lived_sessions, contents)

	def invalidate_authentication_token(self, token):
		self.short_lived_sessions[self.__genhash(from_b64(token))] = None
		self.long_lived_sessions[self.__genhash(from_b64(token))] = None

	def issue_trusted_origin_token(self, old=None):
		if old is not None:
			self.trusted_origin_tokens[self.__genhash(from_b64(old))] = None

		return self.__issue_token(self.trusted_origin_tokens, True)

	def issue_confirmation_token(self, for_who):
		return self.__issue_token(self.login_confirmation_tokens, for_who)
