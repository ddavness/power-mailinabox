# Provides API request and response decorators and utilities

import daemon_error

import enum
import auth
import json
import traceback

from flask import request, Response
from functools import wraps
from utils import load_environment

# User utilities

def json_response(data, status = 200):
	return Response(
		response = json.dumps(data, indent = 2, sort_keys = True) + '\n',
		status = status,
		mimetype = "application/json"
	)

def text_response(data, status = 200, ctype = "text/plain"):
	return Response(
		response = data,
		status = status,
		mimetype = ctype
	)

def no_content():
	return Response(
		response = b"",
		status = 204
	)

auth_service = auth.AuthService()

@enum.unique
class MimeType(enum.Enum):
	PLAIN_TEXT = "text/plain",
	JSON = "application/json"

def decide_error_mime_type(accept_header):
	header = "".join(accept_header.split())
	if header.strip() == "":
		header = "*/*"

	# Parse the header.
	args = []
	for choice in header.split(","):
		mods = choice.split(";")
		mimetype = mods[0]
		if mimetype not in ("text/plain", "application/json", "text/*", "application/*", "*/*"):
			continue
		q = 1
		for m in mods[1:]:
			if m.startswith("q="):
				try:
					q = float(m[2:])
				except:
					pass
				break
		args.append((mimetype, q))

	maxq = 0
	priority = 0
	internal_priorities = {"text/plain": 4, "application/json": 3, "text/*": 2, "application/*": 1, "*/*": 0}

	for arg in args:
		if maxq > arg[1]:
			# Client prefers what we're already proposing
			continue
		if maxq < arg[1]:
			# Client prefers the type we're analyzing
			maxq = arg[1]
			priority = internal_priorities[arg[0]]
			continue
		if internal_priorities[arg[0]] > priority:
			# Client doesn't mind the difference, so we'll follow our own schedule
			priority = internal_priorities[arg[0]]

	return [MimeType.PLAIN_TEXT, MimeType.JSON, MimeType.PLAIN_TEXT, MimeType.JSON, MimeType.PLAIN_TEXT][priority]

def generate_error_response(err: daemon_error.DaemonError, mimetype: MimeType):
	if mimetype == MimeType.JSON:
		r = json_response({
			"code": err.code_str,
			"message": err.message,
			**err.extra
		}, status = err.statuscode())

		return r
	else:
		r = text_response(err.message, status = err.statuscode())

		return r

def renew_trusted_origin_cookie(request, response):
	response.set_cookie(
		"_Host-Trusted-Origin-Token",
		auth_service.issue_trusted_origin_token(request.cookies.get("_Host-Trusted-Origin-Token", None)),
		max_age = 60 * 60 * 60,
		path="/admin",
		secure=True,
		httponly=False,
		samesite="Lax"
	)

def handle_errors(viewf):
	@wraps(viewf)
	def process_request(*args, **kwargs):
		# Check the Accept headers. These only apply to error messages as we can provide
		# a default representation. Errors will always be sent as text/plain UNLESS the
		# client explicitly prefers application/json. Anything else will be ignored.
		error_mime = decide_error_mime_type(request.headers.get("Accept", "text/plain"))

		# Determine content form to create a canonical form (when it's a POST/PUT)
		# We accept URL-encoded and JSON payloads. Anything else is a 415

		if request.method in ("POST", "PUT", "PATCH"):
			ct = request.headers.get("Content-Type", "application/x-www-form-urlencoded")
			contents = "".join(ct.split()).split(";")
			if "application/x-www-form-urlencoded" in contents:
				request.payload = request.form
			elif "application/json" in contents:
				request.payload = request.get_json()
			else:
				# Response is returned as plain text. 415 Media Not Supported means that
				# we don't speak whatever stuff they've uploaded to us
				return generate_error_response(daemon_error.ClientContentError(daemon_error.CLIENT_CONTENT.TYPE_NOT_SUPPORTED), error_mime)

		try:
			response = viewf(*args, **kwargs)
			if response is None:
				# We assume all is good. But we need to return something, we assume it's a No Content
				return no_content()

			return response
		except daemon_error.DaemonError as e:
			# User-side error (4xx)
			r = generate_error_response(e, error_mime)
			if type(e.code) == daemon_error.TRUSTED_ORIGIN and e.code != daemon_error.TRUSTED_ORIGIN.HEADER_MISSING:
				renew_trusted_origin_cookie(request, r)

			return r
		except:
			# Something else - this is an unexpected, most likely internal error
			traceback.print_exc()
			return generate_error_response(
				daemon_error.InternalServerError(daemon_error.INTERNAL_SERVER_ERROR.UNEXPECTED, traceback.format_exc()),
				error_mime
			)

	return process_request

# Ensures that all CSRF "paperwork" is in order.
# Will error and throw a 401 if:
# 0 = HEADER_MISMATCH
# 1 = HEADER_MISMATCH, TOKEN_INVALID
# 2 = HEADER_MISMATCH, TOKEN_INVALID, HEADER_MISSING
def enforce_trusted_origin(strictness = 2):
	def csfr_decorator(viewfunc):

		@wraps(viewfunc)
		@handle_errors
		def newview(*args, **kwargs):
			try:
				auth_service.check_trusted_origin(request)
				return viewfunc(*args, **kwargs)
			except daemon_error.AuthenticationServiceError as e:
				resp = None
				if e.code == daemon_error.TRUSTED_ORIGIN.HEADER_MISMATCH or (
					e.code == daemon_error.TRUSTED_ORIGIN.TOKEN_INVALID and strictness >= 1
					) or (e.code == daemon_error.TRUSTED_ORIGIN.HEADER_MISSING and strictness == 2):
					raise
				else:
					resp = viewfunc(*args, **kwargs)

				if e.code != daemon_error.TRUSTED_ORIGIN.HEADER_MISSING:
					renew_trusted_origin_cookie(request, resp)

				return resp

		return newview
	return csfr_decorator

# Decorator to protect views that require a logged-in user.
def require_privileges(privileges = {"admin"}, trusted_origin_strictness = 2):
	def authorized_personnel_only(viewfunc):

		@wraps(viewfunc)
		@handle_errors
		def newview(*args, **kwargs):
			check_trusted_origin = True
			error = None
			privs = []

			try:
				email, privs = auth_service.authenticate_bearer(request)

				# Bearer tokens bypass the need for CSRF checking, as we can assume
				# such requests are coming from headless processes.
				check_trusted_origin = False
			except daemon_error.AuthenticationServiceError:
				try:
					email, privs = auth_service.authenticate(request, load_environment())
				except daemon_error.AuthenticationServiceError as e:
					from daemon import log_failed_login
					# Write a line in the log recording the failed login.
					log_failed_login(request)

					raise e

			# Authorized to access an API view?
			if len((privileges | {"admin"}) & set(privs)) != 0:
				# Store the email address of the logged in user so it can be accessed
				# from the API methods that affect the calling user.
				request.user_email = email
				request.user_privs = privs

				if check_trusted_origin:
					return enforce_trusted_origin(strictness = trusted_origin_strictness)(viewfunc)(*args, **kwargs)
				else:
					return viewfunc(*args, **kwargs)

			if not error:
				raise daemon_error.UserPrivilegeError(daemon_error.USER_PRIVILEGES.ACCESS_DENIED)

		return newview
	return authorized_personnel_only
