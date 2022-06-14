#!/usr/local/lib/mailinabox/env/bin/python
# Gmail/IMAP import/export

import os
import sys
import re
import shutil
import subprocess


def run_cmd(cmd, config):
	from decimal import Decimal, getcontext
	getcontext().prec = 3

	args = ['su', 'mail', '-g', 'mail', '-s', '/bin/bash', '-c']
	exe = f'/usr/local/lib/mailinabox/env/bin/offlineimap -c {config} '
	if cmd in ('import', 'export'):
		exe += '-o'
	else:
		exe += '--info'
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
				print(f'\r{percent}%   ', end='')
			else:
				output += text

			if process.returncode:
				break
	except Exception:
		process.kill()
		raise

	print('\rDone!\n')
	return output

def importexport_cmdline(exec, cmd, type, user, remoteuser, remotepass, remotehost, remoteport, *folderlist):
	try:
		remoteport = int(remoteport)
		user, sep, domain = user.rpartition('@')
		if cmd not in ('import', 'export', 'info') or type not in ('Gmail', 'IMAP') or not user:
			raise SyntaxError('Error in cmd or type or user parameters')

		localtype = 'Maildir'
		if cmd in ('import', 'info') and type == 'Gmail':
			localtype = 'GmailMaildir'
			if not folderlist:
				folderlist = ('[Gmail]/All Mail',)

	except Exception as e:
		print(usage)
		raise SyntaxError(f'Error in parameters: {locals()}')

	context = locals()
	from utils import load_environment
	env = load_environment()
	context.update(env)

	# Create the config from template
	mailroot = os.path.join(env['STORAGE_ROOT'], 'mail', 'mailboxes')
	config = os.path.join(mailroot, 'offlineimaprc')
	if cmd in ('import', 'info'):
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
	output = run_cmd(cmd, config)
	print(output)


usage = """
Mail in a box Gmail/IMAP import/export tool
imapimport.py cmd type user remoteuser remotepass remoteserver remoteport [folders]
cmd		import/export/info
type		Gmail/IMAP
user		local mail username, usually user@domain.tld
remoteuser	remote server username, usually user@domain.tld
remotepass	remote server password
remotehost	remote server DNS name
remoteport	remote server port number, e.g. 993
[folders]	space separated list of source folders. If omitted for Gmail imports
		only [Gmail]/All Mail will be imported, otherwise all folders will be synced
"""

if __name__ == "__main__":
	# Commandline tool
	try:
		importexport_cmdline(*sys.argv)
	except Exception:
		print(usage)
		raise
