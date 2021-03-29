#!/usr/local/lib/mailinabox/env/bin/python

# Reads in STDIN. If the stream is not empty, mail it to the system administrator.

import sys

import html
import smtplib

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from pgp import create_signature

# In Python 3.6:
#from email.message import Message

from utils import load_environment

# Load system environment info.
env = load_environment()

# Process command line args.
subject = sys.argv[1]

# Read in STDIN.
content = sys.stdin.read().strip()

# If there's nothing coming in, just exit.
if content == "":
	sys.exit(0)

# create MIME message
msg = MIMEMultipart('alternative')

# In Python 3.6:
#msg = Message()

noreply = "noreply-daemon@" + env['PRIMARY_HOSTNAME']
admin_addr = "administrator@" + env['PRIMARY_HOSTNAME']

msg['From'] = "\"%s\" <%s>" % ("System Management Daemon", "noreply-daemon@" + env['PRIMARY_HOSTNAME'])
msg['To'] = "administrator@" + env['PRIMARY_HOSTNAME']
msg['Subject'] = "[%s] %s" % (env['PRIMARY_HOSTNAME'], subject)

content_html = "<html><body><pre>{}</pre></body></html>".format(html.escape(content))

msg.attach(MIMEText(create_signature(content.encode()).decode(), 'plain'))
msg.attach(MIMEText(content_html, 'html'))

# In Python 3.6:
#msg.set_content(content)
#msg.add_alternative(content_html, "html")

# send
smtpclient = smtplib.SMTP('127.0.0.1', 25)
smtpclient.ehlo()
smtpclient.sendmail(
        noreply, # MAIL FROM
        admin_addr, # RCPT TO
        msg.as_string())
smtpclient.quit()
