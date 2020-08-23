# Tools to manipulate PGP keys

import gpg, utils

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

    for id in key.uids:
        key_rep["ids"].append(id.uid)

    for skey in key.subkeys:
        key_rep["subkeys"].append({
            "master": skey.fpr == key.fpr,
            "sign": skey.can_sign == 1,
            "cert": skey.can_certify == 1,
            "encr": skey.can_encrypt == 1,
            "auth": skey.can_authenticate == 1,
            "fpr": skey.fpr,
            "expires": skey.expires if skey.expires != 0 else None,
            "expired": skey.expired == 1,
            "algorithm": crpyt_algos[skey.pubkey_algo] if skey.pubkey_algo in crpyt_algos.keys() else crpyt_algos[0],
            "bits": skey.length
        })

    return key_rep

def get_daemon_key():
    if daemon_key_fpr is None or daemon_key_fpr == "":
        return None
    return key_representation(context.get_key(daemon_key_fpr, secret=True))

def get_imported_keys():
    pass

def import_key(key):
    pass

def export_key(fingerprint):
    pass

def delete_key(fingerprint):
    pass
