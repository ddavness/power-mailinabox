#!/bin/bash

# Daemon PGP Keyring
# ------------------
#
# Initializes the PGP keyring at /home/user-data/.gnupg
# For this, we will generate a new PGP keypair (if one isn't already present)

source setup/functions.sh # load our functions
source /etc/mailinabox.conf # load global vars
export GNUPGHOME # Dump into the environment

# Install gnupg
apt_install gnupg

if [ "$(gpg --list-secret-keys 2> /dev/null)" == "" ]; then
    echo "Generating daemon's PGP keypair..."
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
fi
