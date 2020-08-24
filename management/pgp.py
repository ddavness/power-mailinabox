# Tools to manipulate PGP keys

import gpg, utils, datetime

env = utils.load_environment()

# Import daemon's keyring - usually in /home/user-data/.gnupg/
gpghome = env['GNUPGHOME']
daemon_key_fpr = env['PGPKEY']
context = gpg.Context(armor=True, home_dir=gpghome)

# Global auxiliary lookup tables
trust_levels = ["Unknown", "Undefined", "Never", "Marginal", "Full", "Ultimate"]
crpyt_algos = {
    0: "Unknown",
    1: "RSA",
    2: "RSA-E",
    3: "RSA-S",
    16: "ELG-E",
    17: "DSA",
    18: "ECC",
    20: "ELG",
    301: "ECDSA",
    302: "ECDH",
    303: "EDDSA"
}

# Auxiliary function to process the key in order to be read more conveniently
def key_representation(key):
    if key is None:
        return None
    key_rep = {
        "master_fpr": key.fpr,
        "trust_level": trust_levels[key.owner_trust],
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
        "expires_date": datetime.datetime.utcfromtimestamp(skey.expires).strftime("%x") if skey.expires != 0 else None,
        "expires_days": (datetime.datetime.utcfromtimestamp(skey.expires) - now).days if skey.expires != 0 else None,
        "expired": skey.expired == 1,
        "algorithm": crpyt_algos[skey.pubkey_algo] if skey.pubkey_algo in crpyt_algos.keys() else crpyt_algos[0],
        "bits": skey.length
    } for skey in key.subkeys ]

    return key_rep

def get_daemon_key():
    if daemon_key_fpr is None or daemon_key_fpr == "":
        return None
    return key_representation(context.get_key(daemon_key_fpr, secret=True))

def get_imported_keys():
    # All the keys in the keyring, except for the daemon's key
    return list(
        map(
            key_representation,
            filter(
                lambda k: k.fpr != daemon_key_fpr,
                context.keylist(secret=False)
            )
        )
    )

def import_key(key):
    pass

def export_key(fingerprint):
    pass

def delete_key(fingerprint):
    pass
