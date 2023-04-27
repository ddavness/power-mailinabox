#!/usr/local/lib/mailinabox/env/bin/python3
# Creates an nginx configuration file so we serve HTTP/HTTPS on all
# domains for which a mail account has been set up.
########################################################################

import os.path
import re
import rtyaml

from mailconfig import get_mail_domains
from dns_update import get_custom_dns_config, get_dns_zones
from ssl_certificates import get_ssl_certificates, get_domain_ssl_files, check_certificate
from utils import shell, safe_domain_name, sort_domains, get_php_version


def get_web_domains(env,
					include_www_redirects=True,
					include_auto=True,
					exclude_dns_elsewhere=True):
	# What domains should we serve HTTP(S) for?
	domains = set()

	# Serve web for all mail domains so that we might at least
	# provide auto-discover of email settings, and also a static website
	# if the user wants to make one.
	domains |= get_mail_domains(env)

	if include_www_redirects and include_auto:
		# Add 'www.' subdomains that we want to provide default redirects
		# to the main domain for. We'll add 'www.' to any DNS zones, i.e.
		# the topmost of each domain we serve.
		domains |= set('www.' + zone for zone, zonefile in get_dns_zones(env))

	if include_auto:
		# Add Autoconfiguration domains for domains that there are user accounts at:
		# 'autoconfig.' for Mozilla Thunderbird auto setup.
		# 'autodiscover.' for ActiveSync autodiscovery (Z-Push).
		domains |= set(
			'autoconfig.' + maildomain
			for maildomain in get_mail_domains(env, users_only=True))
		domains |= set(
			'autodiscover.' + maildomain
			for maildomain in get_mail_domains(env, users_only=True))

		# 'mta-sts.' for MTA-STS support for all domains that have email addresses.
		domains |= set('mta-sts.' + maildomain
					for maildomain in get_mail_domains(env))

	# 'openpgpkey.' for WKD support
	domains |= set('openpgpkey.' + maildomain
				for maildomain in get_mail_domains(env))

	if exclude_dns_elsewhere:
		# ...Unless the domain has an A/AAAA record that maps it to a different
		# IP address than this box. Remove those domains from our list.
		domains -= get_domains_with_a_records(env)

	# Ensure the PRIMARY_HOSTNAME is in the list so we can serve webmail
	# as well as Z-Push for Exchange ActiveSync. This can't be removed
	# by a custom A/AAAA record and is never a 'www.' redirect.
	domains.add(env['PRIMARY_HOSTNAME'])

	# Sort the list so the nginx conf gets written in a stable order.
	domains = sort_domains(domains, env)

	return domains


def get_domains_with_a_records(env):
	domains = set()
	dns = get_custom_dns_config(env)
	for domain, rtype, value, ttl in dns:
		if rtype == "CNAME" or (rtype in ("A", "AAAA")
								and value not in ("local", env['PUBLIC_IP'])):
			domains.add(domain)
	return domains


def get_web_domains_with_root_overrides(env):
	# Load custom settings so we can tell what domains have a redirect or proxy set up on '/',
	# which means static hosting is not happening.
	root_overrides = {}
	nginx_conf_custom_fn = os.path.join(env["STORAGE_ROOT"], "www/custom.yaml")
	if os.path.exists(nginx_conf_custom_fn):
		with open(nginx_conf_custom_fn, 'r') as f:
			custom_settings = rtyaml.load(f)
		for domain, settings in custom_settings.items():
			for type, value in [('redirect', settings.get('redirects',
														{}).get('/')),
								('proxy', settings.get('proxies',
													{}).get('/'))]:
				if value:
					root_overrides[domain] = (type, value)
	return root_overrides


DOMAIN_EXTERNAL = -1
DOMAIN_PRIMARY = 1
DOMAIN_WWW = 2
DOMAIN_REDIRECT = 4
DOMAIN_WKD = 8


def get_web_domain_flags(env):
	flags = dict()
	zones = get_dns_zones(env)
	email_domains = get_mail_domains(env)
	user_domains = get_mail_domains(env, users_only=True)
	external = get_domains_with_a_records(env)
	redirects = get_web_domains_with_root_overrides(env)

	for d in email_domains:
		flags[d] = flags.get(d, 0)
		flags[f"mta-sts.{d}"] = flags.get(d, 0)
		flags[f"openpgpkey.{d}"] = flags.get(d, 0) | DOMAIN_WKD

	for d in user_domains:
		flags[f"autoconfig.{d}"] = flags.get(d, 0)
		flags[f"autodiscover.{d}"] = flags.get(d, 0)

	for d, _ in zones:
		flags[f"www.{d}"] = flags.get(d, 0) | DOMAIN_WWW

	for d in redirects:
		flags[d] = flags.get(d, 0) | DOMAIN_REDIRECT

	flags[env["PRIMARY_HOSTNAME"]] |= DOMAIN_PRIMARY

	# Last check for websites hosted elsewhere
	for d in flags.keys():
		if d in external:
			# -1 = All bits set to 1, assuming twos-complement
			flags[d] = DOMAIN_EXTERNAL
	return flags


def do_web_update(env):
	# Pre-load what SSL certificates we will use for each domain.
	ssl_certificates = get_ssl_certificates(env)

	# Helper for reading config files and templates
	def read_conf(conf_fn):
		with open(os.path.join(os.path.dirname(__file__), "../conf", conf_fn), "r") as f:
			return f.read()

	# Build an nginx configuration file.
	nginx_conf = read_conf("nginx-top.conf")

	nginx_conf = re.sub("{{phpver}}", get_php_version(), nginx_conf)

	# Add upstream additions
	nginx_upstream_include = os.path.join(env["STORAGE_ROOT"], "www", ".upstream.conf")
	if not os.path.exists(nginx_upstream_include):
		with open(nginx_upstream_include, "a+") as f:
			f.writelines([
				f"# Add your nginx-wide configurations here.\n",
				"# The following names are already defined:\n\n",
				"# # php-default: The php socket used for apps managed by the box. (Roundcube, Z-Push, Nextcloud, etc.) - DO NOT USE!\n",
				"# # php-fpm: A php socket not managed by the box. Feel free to use it for your PHP applications\n"
			])

	nginx_conf += "\ninclude %s;\n" % (nginx_upstream_include)

	# Load the templates.
	template0 = read_conf("nginx.conf")
	template1 = read_conf("nginx-alldomains.conf")
	template2 = read_conf("nginx-primaryonly.conf")
	template3 = "\trewrite ^(.*) https://$REDIRECT_DOMAIN$1 permanent;\n"
	template4 = read_conf("nginx-openpgpkey.conf")

	# Add the PRIMARY_HOST configuration first so it becomes nginx's default server.
	nginx_conf += make_domain_config(env['PRIMARY_HOSTNAME'],
									[template0, template1, template2],
									ssl_certificates, env)

	# Add configuration all other web domains.
	pairs = list(get_web_domain_flags(env).items())

	# Sort the domains in some way to keep ordering consistency. Keep domains and subdomains together.
	pairs.sort(reverse=False, key=lambda x: x[0][::-1])
	for domain, flags in pairs:
		if flags & DOMAIN_PRIMARY == DOMAIN_PRIMARY or flags == DOMAIN_EXTERNAL:
			# PRIMARY_HOSTNAME is handled above.
			continue
		if flags & DOMAIN_WWW == 0:
			# This is a regular domain.
			if flags & DOMAIN_WKD == DOMAIN_WKD:
				nginx_conf += make_domain_config(
					domain, [template0, template1, template4],
					ssl_certificates, env)
			elif flags & DOMAIN_REDIRECT == 0:
				nginx_conf += make_domain_config(domain,
												[template0, template1],
												ssl_certificates, env)
			else:
				nginx_conf += make_domain_config(domain, [template0],
												ssl_certificates, env)
		else:
			# Add default 'www.' redirect.
			nginx_conf += make_domain_config(domain, [template0, template3],
											ssl_certificates, env)

	# Did the file change? If not, don't bother writing & restarting nginx.
	nginx_conf_fn = "/etc/nginx/conf.d/local.conf"
	if os.path.exists(nginx_conf_fn):
		with open(nginx_conf_fn) as f:
			if f.read() == nginx_conf:
				return ""

	# Save the file.
	with open(nginx_conf_fn, "w") as f:
		f.write(nginx_conf)

	# Kick nginx. Since this might be called from the web admin
	# don't do a 'restart'. That would kill the connection before
	# the API returns its response. A 'reload' should be good
	# enough and doesn't break any open connections.
	shell('check_call', ["/usr/sbin/service", "nginx", "reload"])

	return "web updated\n"


def make_domain_config(domain, templates, ssl_certificates, env):
	# GET SOME VARIABLES

	# Where will its root directory be for static files?
	root = get_web_root(domain, env)

	# What private key and SSL certificate will we use for this domain?
	tls_cert = get_domain_ssl_files(domain, ssl_certificates, env)

	# ADDITIONAL DIRECTIVES.

	nginx_conf_extra = ""

	# Because the certificate may change, we should recognize this so we
	# can trigger an nginx update.
	def hashfile(filepath):
		import hashlib
		sha1 = hashlib.sha1()
		with open(filepath, 'rb') as f:
			sha1.update(f.read())
		return sha1.hexdigest()

	nginx_conf_extra += "\t# ssl files sha1: %s / %s\n" % (hashfile(
		tls_cert["private-key"]), hashfile(tls_cert["certificate"]))

	# Add in any user customizations in YAML format.
	hsts = "yes"
	nginx_conf_custom_fn = os.path.join(env["STORAGE_ROOT"], "www/custom.yaml")
	if os.path.exists(nginx_conf_custom_fn):
		with open(nginx_conf_custom_fn, 'r') as f:
			yaml = rtyaml.load(f)
		if domain in yaml:
			yaml = yaml[domain]

			# any proxy or redirect here?
			for path, url in yaml.get("proxies", {}).items():
				# Parse some flags in the fragment of the URL.
				pass_http_host_header = False
				proxy_redirect_off = False
				frame_options_header_sameorigin = False
				m = re.search("#(.*)$", url)
				if m:
					for flag in m.group(1).split(","):
						if flag == "pass-http-host":
							pass_http_host_header = True
						elif flag == "no-proxy-redirect":
							proxy_redirect_off = True
						elif flag == "frame-options-sameorigin":
							frame_options_header_sameorigin = True
					url = re.sub("#(.*)$", "", url)

				nginx_conf_extra += "\tlocation %s {" % path
				nginx_conf_extra += "\n\t\tproxy_pass %s;" % url
				if proxy_redirect_off:
					nginx_conf_extra += "\n\t\tproxy_redirect off;"
				if pass_http_host_header:
					nginx_conf_extra += "\n\t\tproxy_set_header Host $http_host;"
				if frame_options_header_sameorigin:
					nginx_conf_extra += "\n\t\tproxy_set_header X-Frame-Options SAMEORIGIN;"
				nginx_conf_extra += "\n\t\tproxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;"
				nginx_conf_extra += "\n\t\tproxy_set_header X-Forwarded-Host $http_host;"
				nginx_conf_extra += "\n\t\tproxy_set_header X-Forwarded-Proto $scheme;"
				nginx_conf_extra += "\n\t\tproxy_set_header X-Real-IP $remote_addr;"
				nginx_conf_extra += "\n\t}\n"
			for path, alias in yaml.get("aliases", {}).items():
				nginx_conf_extra += "\tlocation %s {" % path
				nginx_conf_extra += "\n\t\talias %s;" % alias
				nginx_conf_extra += "\n\t}\n"
			for path, url in yaml.get("redirects", {}).items():
				nginx_conf_extra += "\trewrite %s %s permanent;\n" % (path,
																	url)

			# override the HSTS directive type
			hsts = yaml.get("hsts", hsts)

	# Add the HSTS header.
	if hsts == "yes":
		nginx_conf_extra += "\tadd_header Strict-Transport-Security \"max-age=31536000\" always;\n"
	elif hsts == "preload":
		nginx_conf_extra += "\tadd_header Strict-Transport-Security \"max-age=31536000; includeSubDomains; preload\" always;\n"

	# Add in any user customizations in the includes/ folder.
	nginx_conf_custom_include = os.path.join(
		env["STORAGE_ROOT"], "www",
		safe_domain_name(domain) + ".conf")
	if not os.path.exists(nginx_conf_custom_include):
		with open(nginx_conf_custom_include, "a+") as f:
			f.writelines([
				f"# Custom configurations for {domain} go here\n",
				"# To use php: use the \"php-fpm\" alias\n\n",
				"index index.html index.htm;\n"
			])

	nginx_conf_extra += "\tinclude %s;\n" % (nginx_conf_custom_include)

	# PUT IT ALL TOGETHER

	# Combine the pieces. Iteratively place each template into the "# ADDITIONAL DIRECTIVES HERE" placeholder
	# of the previous template.
	nginx_conf = "# ADDITIONAL DIRECTIVES HERE\n"
	for t in templates + [nginx_conf_extra]:
		nginx_conf = re.sub("[ \t]*# ADDITIONAL DIRECTIVES HERE *\n", t,
							nginx_conf)

	# Replace substitution strings in the template & return.
	nginx_conf = nginx_conf.replace("$STORAGE_ROOT", env['STORAGE_ROOT'])
	nginx_conf = nginx_conf.replace("$HOSTNAME", domain)
	nginx_conf = nginx_conf.replace("$HTTPS_PORT", env['HTTPS_PORT'])
	nginx_conf = nginx_conf.replace("$ROOT", root)
	nginx_conf = nginx_conf.replace("$SSL_KEY", tls_cert["private-key"])
	nginx_conf = nginx_conf.replace("$SSL_CERTIFICATE", tls_cert["certificate"])
	nginx_conf = nginx_conf.replace(
		"$REDIRECT_DOMAIN",
		re.sub(r"^www\.", "",
			domain))  # for default www redirects to parent domain

	return nginx_conf


def get_web_root(domain, env, test_exists=True):
	# Try STORAGE_ROOT/web/domain_name if it exists, but fall back to STORAGE_ROOT/web/default.
	for test_domain in (domain, 'default'):
		root = os.path.join(env["STORAGE_ROOT"], "www",
							safe_domain_name(test_domain))
		if os.path.exists(root) or not test_exists:
			break
	return root


def is_default_web_root(domain, env):
	root = os.path.join(env["STORAGE_ROOT"], "www", safe_domain_name(domain))
	return not os.path.exists(root)


def get_web_domains_info(env):
	www_redirects = set(get_web_domains(env)) - \
			set(get_web_domains(env, include_www_redirects=False))
	has_root_proxy_or_redirect = set(get_web_domains_with_root_overrides(env))
	ssl_certificates = get_ssl_certificates(env)

	# for the SSL config panel, get cert status
	def check_cert(domain):
		try:
			tls_cert = get_domain_ssl_files(domain,
											ssl_certificates,
											env,
											allow_missing_cert=True)
		except OSError:  # PRIMARY_HOSTNAME cert is missing
			tls_cert = None
		if tls_cert is None:
			return ("danger", "No certificate installed.")
		cert_status, cert_status_details = check_certificate(
			domain, tls_cert["certificate"], tls_cert["private-key"])
		if cert_status == "OK":
			return ("success", "Signed & valid. " + cert_status_details)
		elif cert_status == "SELF-SIGNED":
			return ("warning",
					"Self-signed. Get a signed certificate to stop warnings.")
		else:
			return ("danger", "Certificate has a problem: " + cert_status)

	return [{
		"domain":
		domain,
		"root":
		get_web_root(domain, env),
		"custom_root":
		get_web_root(domain, env, test_exists=False),
		"ssl_certificate":
		check_cert(domain),
		"static_enabled":
		domain not in (www_redirects | has_root_proxy_or_redirect),
	} for domain in get_web_domains(env)]

if __name__ == '__main__':
	from web_update import do_web_update
	from utils import load_environment
	env = load_environment()
	print(do_web_update(env))
