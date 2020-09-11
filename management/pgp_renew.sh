#!/bin/bash
# Renews the daemon's PGP key, if needed.

source /etc/mailinabox.conf # load global vars
export GNUPGHOME # Dump into the environment so that gpg uses it as homedir

gpg --batch --command-fd=0 --edit-key "${PGPKEY-}" << EOF;
key 0
expire
180d
save
EOF