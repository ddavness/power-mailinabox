#!/usr/local/lib/mailinabox/env/bin/python
# Gmail/IMAP import/export

import os
import sys
import re
import shutil
import subprocess
import string
import random


def run_cmd(config, info):
	from decimal import Decimal, getcontext
	getcontext().prec = 3

	args = ['su', 'mail', '-g', 'mail', '-s', '/bin/bash', '-c']
	exe = f'/usr/local/lib/mailinabox/env/bin/offlineimap -c {config} '
	if info:
		exe += '--info'
	else:
		exe += '-o'

	args.append(exe)
	print('')
	output = ''

	# example: Copy message UID 118742 (8/137) Source:[Gmail]/All Mail -> In:.Import
	regex = re.compile(r'Copy message UID.*?\((\d+)/(\d+)\)')

	try:
		process = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		for line in iter(process.stdout.readline, b''):
			text = line.decode('utf8')

			# output progress %
			match = regex.search(text)
			if match:
				percent = ( Decimal(match.group(1)) / Decimal(match.group(2)) ) * 100
				print(f'\r{percent}% ', end='')
			else:
				output += text

			if process.returncode:
				break
	except Exception:
		process.kill()
		raise

	print('\rDone!\n')
	return output

def importexport_cmdline(exec, cmd, type, user, remoteuser, remotepass, remotehost, remoteport, *folderlist, **options):
	from utils import load_environment

	remoteport = int(remoteport)
	user, sep, domain = user.rpartition('@')
	if cmd not in ('import', 'export'):
		raise SyntaxError("Error: cmd can be 'import' or 'export'")
	if type not in ('Gmail', 'IMAP'):
		raise SyntaxError("Error: type can be 'Gmail' or 'IMAP'")
	if not user:
		raise SyntaxError("Error: user should be in the form 'user@host'")

	localtype = 'Maildir'
	if type == 'Gmail' and cmd == 'import':
		localtype = 'GmailMaildir'

	context = locals()
	env = load_environment()
	context.update(env)

	# Create the config from template
	mailroot = os.path.join(env['STORAGE_ROOT'], 'mail', 'mailboxes')
	filename = ''.join(random.choices(string.ascii_letters, k=12))
	config = os.path.join(mailroot, domain, user, filename)
	if cmd == 'import':
		template = os.path.join(mailroot, 'offlineimap-in.conf')
	else:
		template = os.path.join(mailroot, 'offlineimap-out.conf')

	with open(template, 'r') as fd:
		text = fd.read()
	render = text.format(**context)

	with open(config, 'w') as fd:
		fd.write(render)
	shutil.chown(config, 'mail', 'mail')

	# Run
	output = run_cmd(config, options.get('info'))
	os.remove(config)

	if not options.get('quiet'):
		print(output)


usage = f"""
Mail in a box Gmail/IMAP import/export tool
{sys.argv[0]} [options] cmd type user remoteuser remotepass remoteserver remoteport [folders]
Options:
-i		remote and local folder information
-q		quiet, don't print the output from the transfer. Progress is always printed

Parameters:
cmd		import or export
type		Gmail or IMAP
user		local mail username, usually user@domain.tld
remoteuser	remote server username, usually user@domain.tld
remotepass	remote server password
remotehost	remote server DNS name
remoteport	remote server port number, e.g. 993
[folders]	space separated list of remote (Gmail/IMAP) folders. If omitted for Gmail,
		only '[Gmail]/All Mail' will be migrated, otherwise all folders will be allowed

*** Important Note: Once an import has started you will need to make the folder visible
                    in webmail settings.
"""

if __name__ == "__main__":
	# Commandline tool
	args = []
	options = {}
	for arg in sys.argv:
		if arg == '-i':
			options['info'] = True
		elif arg == '-q':
			options['quiet'] = True
		else:
			args.append(arg)

	try:
		importexport_cmdline(*args, **options)
	except Exception as e:
		print(usage)
		print(str(e))
		pass
