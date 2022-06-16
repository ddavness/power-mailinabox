#!/bin/bash

source /etc/mailinabox.conf # get global vars
source setup/functions.sh # load our functions

echo "Installing IMAP/Gmail importer..."

# DEPENDENCIES
# Install offlineimap to the venv
venv=/usr/local/lib/mailinabox/env
hide_output $venv/bin/pip install --upgrade distro imaplib2 rfc6555
hide_output $venv/bin/pip install --upgrade git+https://github.com/offlineIMAP/offlineimap3.git@v8.0.0

# CONFIGURATION
maildir=$STORAGE_ROOT/mail/mailboxes

# offlineimap helper script
scriptname=set-received-mtime
hide_output cp tools/$scriptname $maildir
chown mail:mail $maildir/$scriptname

# config templates
hide_output cp conf/offlineimap* $maildir
chown mail:mail $maildir/offlineimap*
