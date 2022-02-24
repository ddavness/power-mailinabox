# Provides API request and response decorators and utilities

from ast import arg
from operator import mod
import auth
import json
import os

from flask import Flask, request, render_template, abort, Response, send_from_directory, make_response
from functools import wraps

auth_service = auth.AuthService()

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

	return ["text/plain", "application/json", "text/plain", "application/json", "text/plain"][priority]

def route_decorator(app):
	def create_decorator(*args, **kwargs):
		def decorator(viewf):
			@app.route(*args, **kwargs)
			def process_request():
				# Check the Accept headers. These only apply to error messages as we can provide
				# a default representation. Errors will always be sent as text/plain UNLESS the
				# client explicitly prefers application/json. Anything else will be ignored.
				error_mime = decide_error_mime_type(request.headers.get("Accept", "text/plain"))

				# Determine content form to create a canonical form (when it's a POST/PUT)
				# We accept URL-encoded and JSON payloads. Anything else is a 415

				if request.method in ("POST", "PUT", "PATCH"):
					ct = request.headers.get("Content-Type", "application/x-www-form-urlencoded")
					if ct == "application/x-www-form-urlencoded":
						request.payload = request.form
					elif ct == "application/json":
						request.payload = request.get_json()
					else:
						# Response is returned as plain text. 415 Media Not Supported means that
						# we don't speak whatever stuff they've uploaded to us
						return Response(415)

				return Response()

				responsedata = viewf()
				if responsedata is None:
					return

			return process_request
		return decorator
	return create_decorator

def json_response(data, status=200):
	return Response(
		json.dumps(data, indent=2, sort_keys=True) + '\n',
		status=status,
		mimetype="application/json"
	)

# Ensures that all CSRF "paperwork" is in order.
# Will error and throw a 401 if:
# 0 = HEADER_MISMATCH
# 1 = HEADER_MISMATCH, TOKEN_INVALID
# 2 = HEADER_MISMATCH, TOKEN_INVALID, HEADER_MISSING
def enforce_trusted_origin(strictness = 2):

	def csfr_decorator(viewfunc):

		@wraps(viewfunc)
		def newview(*args, **kwargs):
			try:
				auth_service.check_trusted_origin(request)
				return viewfunc(*args, **kwargs)
			except ValueError as e:
				resp = None
				if (
					e.args[0] == auth.CSFRStatusEnum.HEADER_MISMATCH
					or (e.args[0] == auth.CSFRStatusEnum.INVALID and strictness >= 1)
					or (e.args[0] == auth.CSFRStatusEnum.HEADER_MISSING and strictness == 2)
				):
					resp = json_response({
						"code": e.args[0].value,
					}, 401)
				else:
					resp = viewfunc(*args, **kwargs)

				if e.args[0] != auth.CSFRStatusEnum.HEADER_MISSING:
					resp.set_cookie(
						"_Host-Trusted-Origin-Token",
						auth_service.issue_trusted_origin_token(request.cookies.get("_Host-Trusted-Origin-Token", None)),
						max_age = 60 * 60 * 60,
						path="/admin",
						secure=True,
						httponly=False,
						samesite="Lax"
					)

				return resp

		return newview

	return csfr_decorator

# Decorator to protect views that require a user with 'admin' privileges.
def require_privileges(privileges = {"admin"}, trusted_origin_strictness = 2):

	def authorized_personnel_only(viewfunc):

		@wraps(viewfunc)
		def newview(*args, **kwargs):
			check_trusted_origin = True
			error = None
			privs = []

			try:
				email, privs = auth_service.authenticate_bearer(request)

				# Bearer tokens bypass the need for CSRF checking, as we can assume
				# such requests are coming from headless processes.
				check_trusted_origin = False
			except ValueError:
				try:
					email, privs = auth_service.authenticate(request, env)
				except ValueError as e:
					# Write a line in the log recording the failed login.
					log_failed_login(request)

					# Authentication failed.
					error = str(e)

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
				error = "You do not have enough permissions to access this resource."

			# Not authorized. Return a 401 (send auth) and a prompt to authorize by default.
			status = 401
			headers = {
				"WWW-Authenticate": "Do Not Attempt Browser Authentication"
			}

			if request.headers.get("Accept") in (None, "", "*/*"):
				# Return plain text output.
				return Response(error + "\n",
								status=status,
								mimetype='text/plain',
								headers=headers)
			else:
				# Return JSON output.
				return Response(
					json.dumps({
						"status": "error",
						"reason": error,
					}) + "\n",
					status=status,
					mimetype="application/json",
					headers=headers)

		return newview

	return authorized_personnel_only

def generate_response(data):
	if data == {}:
		return make_response("", 204)
	else:
		return make_response(data, 200)
