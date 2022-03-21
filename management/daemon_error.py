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
		self.code_str = f"{type(why).__name__}_{why.name}"
		self.message = why.value
		self.extra = {}

	def statuscode(self):
		# Subclasses can implement something else if they want to
		return 400

# Internal server errors

class INTERNAL_SERVER_ERROR(DaemonErrorEnum):
	UNEXPECTED = "An unexpected error happened! This might be a bug."

class InternalServerError(DaemonError):
	def __init__(self, why: INTERNAL_SERVER_ERROR, traceback: str):
		super().__init__(why)
		if is_development_mode():
			self.extra = {
				"traceback": traceback
			}

	def statuscode(self):
		return 500

# Errors related to the client content

class CLIENT_CONTENT(DaemonErrorEnum):
	TYPE_NOT_SUPPORTED = "The content type uploaded is not supported by the server. Supported Content-Types are \"application/x-www-form-urlencoded\" and \"application/json\"."

class ClientContentError(DaemonError):
	def __init__(self, why: CLIENT_CONTENT):
		super().__init__(why)
		self.extra = {
			"supported_content_types": [
				"application/x-www-form-urlencoded",
				"application/json"
			]
		}

	def statuscode(self):
		return 415

# Errors related to the authentication service

class TRUSTED_ORIGIN(DaemonErrorEnum):
	TOKEN_INVALID = "The Trusted-Origin token is either missing or invalid."
	HEADER_MISSING = "The X-Trusted-Origin-Token HTTP header is missing."
	HEADER_MISMATCH = "The Trusted-Origin-Token cookie and X-Trusted-Origin-Token header do not match."

class AUTH_STATUS(DaemonErrorEnum):
	TOKEN_INVALID = "Authentication token is missing, invalid or has been revoked."

class LOGIN_STATUS(DaemonErrorEnum):
	USER_PASSWORD_INVALID = "Incorrect user or password."
	MFA_AUTH_INVALID = "The TOTP token is incorrect."
	CONFIRMATION_TOKEN_INVALID = "The 2FA login window has expired and is now invalid. Please log in again."

class AuthenticationServiceError(DaemonError):
	def statuscode(self):
		return 401

# Errors related to permissions

class USER_PRIVILEGES(DaemonErrorEnum):
	ACCESS_DENIED = "You don't have enough privileges to access this resource."

class UserPrivilegeError(DaemonError):
	def statuscode(self):
		return 403

# Functionality-specific enums

class ALIAS(DaemonErrorEnum):
	ADDRESS_INVALID = "No address provided or the address is not valid."
	NO_DESTINATIONS_OR_PERMITTED_SENDERS = "No destinations or permitted senders have been specified."
	DESTINATION_INVALID = "One or more destination addresses are not valid."
	DESTINATIONS_MUST_BE_ADMINS = "This alias can only have administrators of this system as destinations because the address is frequently used for domain control validation."
	PERMITTED_SENDER_INVALID = "One or more permitted senders are not valid."
	PERMITTED_SENDER_NOT_USER = "One or more permitted senders are not users of this system."
	NOT_FOUND = "The specified alias was not found."
	EXISTS = "The specified address is already an alias in this system."

class AliasError(DaemonError):
	def __init__(self, why: ALIAS, address: str, info = dict()):
		super().__init__(why)
		self.extra = {
			"address": address,
			**info
		}

	def statuscode(self):
		if self.code == ALIAS.EXISTS:
			return 409
		elif self.code == ALIAS.NOT_FOUND:
			return 404
		else:
			return 400
