#!/usr/local/lib/mailinabox/env/bin/python
# Tools to manipulate PGP keys

import gpg, utils, datetime, shutil, tempfile

env = utils.load_environment()

# Import daemon's keyring - usually in /home/user-data/.gnupg/
gpghome = env['GNUPGHOME']
daemon_key_fpr = env['PGPKEY']
default_context = gpg.Context(armor=True, home_dir=gpghome)

# Auxiliary function to process the key in order to be read more conveniently
def key_representation(key):
    if key is None:
        return None
    key_rep = {
        "master_fpr": key.fpr,
        "revoked": key.revoked != 0,
        "ids": [],
        "subkeys": []
    }

    now = datetime.datetime.utcnow()
    key_rep["ids"] = [ id.uid for id in key.uids ]
    key_rep["subkeys"] = [{
        "master": skey.fpr == key.fpr,
        "sign": skey.can_sign == 1,
        "cert": skey.can_certify == 1,
        "encr": skey.can_encrypt == 1,
        "auth": skey.can_authenticate == 1,
        "fpr": skey.fpr,
        "expires": skey.expires if skey.expires != 0 else None,
        "expires_date": datetime.datetime.utcfromtimestamp(skey.expires).date().isoformat() if skey.expires != 0 else None,
        "expires_days": (datetime.datetime.utcfromtimestamp(skey.expires) - now).days if skey.expires != 0 else None,
        "expired": skey.expired == 1,
        "algorithm": gpg.core.pubkey_algo_name(skey.pubkey_algo),
        "bits": skey.length
    } for skey in key.subkeys ]

    return key_rep

# Tests an import as for whether we have any sort of private key material in our import
def contains_private_keys(imports):
    with tempfile.TemporaryDirectory() as tmpdir:
        with gpg.Context(home_dir=tmpdir, armor=True) as tmp:
            result = tmp.key_import(imports)
            try:
                return result.secret_read != 0
            except AttributeError:
                raise ValueError("Import is not a valid PGP key block!")

# Decorator: Copies the homedir of a context onto a temporary directory and returns a context operating over that tmpdir
def fork_context(f, context = default_context):
	def wrapped(*args, **kwargs):
		with tempfile.TemporaryDirectory() as tmpdir:
			shutil.copytree(context.home_dir, f"{tmpdir}/gnupg")
			kwargs["context"] = gpg.Context(armor=context.armor, home_dir=f"{tmpdir}/gnupg")
			return f(*args, **kwargs)

	return wrapped


def get_key(fingerprint, context = default_context):
	try:
		return context.get_key(fingerprint, secret=False)
	except KeyError:
		return None
	except gpg.errors.GPGMEError:
		return None

def get_daemon_key(context = default_context):
    if daemon_key_fpr is None or daemon_key_fpr == "":
        return None
    return context.get_key(daemon_key_fpr, secret=True)

def get_imported_keys(context = default_context):
    # All the keys in the keyring, except for the daemon's key
    return list(
        filter(
            lambda k: k.fpr != daemon_key_fpr,
            context.keylist(secret=False)
        )
    )

def import_key(key, context = default_context):
    data = str.encode(key)
    if contains_private_keys(data):
        raise ValueError("Import cannot contain private keys!")
    return context.key_import(data)

def export_key(fingerprint, context = default_context):
    if get_key(fingerprint) is None:
        return None
    return context.key_export(pattern=fingerprint) # Key does exist, export it!

def delete_key(fingerprint, context = default_context):
    key = get_key(fingerprint)
    if fingerprint == daemon_key_fpr:
        raise ValueError("You cannot delete the daemon's key!")
    elif key is None:
        return None
    context.op_delete_ext(key, gpg.constants.DELETE_ALLOW_SECRET | gpg.constants.DELETE_FORCE)
    return True

# Key usage

# Uses the daemon key to sign the provided message. If 'detached' is True, only the signature will be returned
def create_signature(data, detached=False, context = default_context):
    signed_data, _ = context.sign(data, mode=gpg.constants.sig.mode.DETACH if detached else gpg.constants.sig.mode.CLEAR)
    return signed_data

if __name__ == "__main__":
    import sys, utils
    # Check if we should renew the key

    daemon_key = get_daemon_key()

    exp = daemon_key.subkeys[0].expires
    now = datetime.datetime.utcnow()
    days_left = (datetime.datetime.utcfromtimestamp(exp) - now).days
    if days_left > 14:
        sys.exit(0)
    else:
        utils.shell("check_output", ["management/pgp_renew.sh"])
