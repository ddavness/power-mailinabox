# Contains all user-facing errors
# Useful for the end functions to throw, then the
# middleware can convert it to a nice HTTP representation

from enum import Enum
from utils import is_development_mode

class DaemonErrorEnum(Enum):
	pass

class DaemonError(Exception):
	def __init__(self, why: DaemonErrorEnum):
		self.code = why
		self.code_str = f"{why.__class__}_{why.name}"
		self.message = why.value

	def statuscode():
		# Subclasses can implement something else if they want to
		return 400

# Internal server errors

class INTERNAL_SERVER_ERROR(DaemonErrorEnum):
	UNEXPECTED = "An unexpected error happened! This might be a bug."

class InternalServerError(DaemonError):
	def __init__(self, why: INTERNAL_SERVER_ERROR, traceback: str):
		super.__init__(why)
		if is_development_mode():
			self.message = traceback

	def statuscode():
		return 500

# Errors related to the client content

class CLIENT_CONTENT(DaemonErrorEnum):
	TYPE_NOT_SUPPORTED = "The content type uploaded is not supported by the server. Supported Content-Types are \"application/x-www-form-urlencoded\" and \"application/json\"."

class ClientContentError(DaemonError):
	def statuscode():
		return 415

# Errors related to the authentication service

class TRUSTED_ORIGIN(DaemonErrorEnum):
	TOKEN_INVALID = "The Trusted-Origin token is either missing or invalid.",
	HEADER_MISSING = "The X-Trusted-Origin-Token HTTP header is missing.",
	HEADER_MISMATCH = "The Trusted-Origin-Token cookie and X-Trusted-Origin-Token header do not match."

class AUTH_STATUS(DaemonErrorEnum):
	TOKEN_INVALID = "Authentication token is missing, invalid or has been revoked."

class LOGIN_STATUS(DaemonErrorEnum):
	USER_PASSWORD_INVALID = "Incorrect user or password.",
	MFA_AUTH_INVALID = "The TOTP token is incorrect.",
	CONFIRMATION_TOKEN_INVALID = "The 2FA login window has expired and is now invalid. Please log in again."

class AuthenticationServiceError(DaemonError):
	def statuscode():
		return 401

	def modify_request(r):
		# Called immediately before sending the response.
		# Can be used to attach headers.
		return r

# Errors related to permissions

class USER_PRIVILEGES(DaemonErrorEnum):
	ACCESS_DENIED = "You don't have enough privileges to access this resource."

class UserPrivilegeError(DaemonError):
	def statuscode():
		return 403
