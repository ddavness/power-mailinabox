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

function gpg_keygen {
    # Generates a private key.
    gpg --generate-key --batch 2> /tmp/gpg_keygen_log << EOF;
    %no-protection
    Key-Type: RSA
    Key-Length: 4096
    Key-Usage: sign,encrypt,auth
    Name-Real: System Management Daemon
    Name-Email: noreply-daemon@${PRIMARY_HOSTNAME}
    Expire-Date: 180d
    %commit
EOF
}

# Generate a new key if:
# - There isn't a fingerprint on /etc/mailinabox.conf
# - The configured fingerprint doesn't actually exist

if [ "${PGPKEY-}" == "" -o "$(gpg --list-secret-keys 2> /dev/null | grep ${PGPKEY-})" = "" ]; then
    echo "No keypair found. Generating daemon's PGP keypair..."
    gpg_keygen
    if [ $? -ne 0 ]; then
        echo ""
        echo "Key generation failed!" 1>&2
        echo "============================" 1>&2
        cat /tmp/gpg_keygen_log 1>&2
        echo "============================" 1>&2

        exit 1
    fi

    FPR=$(cat /tmp/gpg_keygen_log | tr -d '\n' | sed -r 's/.*([0-9A-F]{40}).*/\1/g')
    echo "Generated key with fingerprint $FPR"

    chown -R root:root $GNUPGHOME
    # Remove the old key fingerprint from the configuration if it exists, and add the new one
    echo "$(cat /etc/mailinabox.conf | grep -v "PGPKEY")" > /etc/mailinabox.conf
    echo "PGPKEY=$FPR" >> /etc/mailinabox.conf
fi
