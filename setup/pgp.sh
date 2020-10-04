#!/bin/bash

# Daemon PGP Keyring
# ------------------
#
# Initializes the PGP keyring at /home/user-data/.gnupg
# For this, we will generate a new PGP keypair (if one isn't already present)

source setup/functions.sh # load our functions
source /etc/mailinabox.conf # load global vars
export GNUPGHOME # Dump into the environment so that gpg uses it as homedir

# Install gnupg
apt_install gnupg

if [ "$(gpg --list-secret-keys 2> /dev/null)" = "" -o "${PGPKEY-}" = "" ]; then
    echo "No keypair found. Generating daemon's PGP keypair..."
    gpg --generate-key --batch << EOF;
    %no-protection
    Key-Type: RSA
    Key-Length: 4096
    Key-Usage: sign,encrypt,auth
    Name-Real: Power Mail-in-a-Box Management Daemon
    Name-Email: administrator@${PRIMARY_HOSTNAME}
    Expire-Date: 180d
    %commit
EOF
    chown -R root:root $GNUPGHOME
    # Remove the old key fingerprint if it exists, and add the new one
    echo "$(cat /etc/mailinabox.conf | grep -v "PGPKEY")" > /etc/mailinabox.conf
    echo "PGPKEY=$(gpg --list-secret-keys --with-colons | grep fpr | head -n 1 | sed 's/fpr//g' | sed 's/://g')" >> /etc/mailinabox.conf
fi
