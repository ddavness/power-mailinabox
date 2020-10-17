#!/usr/local/lib/mailinabox/env/bin/python
# WDK (Web Key Directory) Manager: Facilitates discovery of keys by third-parties
# Current relevant documents: https://tools.ietf.org/id/draft-koch-openpgp-webkey-service-10.html

import pgp, utils
from cryptography.hazmat.primitives import hashes

env = utils.load_environment()

wkdpath = f"{env['GNUPGHOME']}/.wkdlist"

def sha1(message):
    h = hashes.Hash(hashes.SHA1())
    h.update(message)
    return h.finalize()

def zbase32(digest):
    # Crudely check if all quintets are complete
    if len(digest) % 5 != 0:
        raise ValueError("Digest cannot have incomplete chunks of 40 bits!")
    base = "ybndrfg8ejkmcpqxot1uwisza345h769"
    encoded = ""
    for i in range(0, len(digest), 5):
        chunk = int.from_bytes(digest[i:i+5], byteorder="big")
        for j in range(35, -5, -5):
            encoded += base[(chunk >> j) & 31]
    return encoded

def set_wkd_published(fingerprint, publish):
    if pgp.get_key(fingerprint) is None:
        return None
    with open(wkdpath, "a+") as wkdfile:
        wkdfile.seek(0)
        wkdlist = list(map(lambda s: s[0:-1], list(wkdfile)))
        print(wkdlist)
        # if we want to publish an already published key or we want to unpublish a non-published key, exit early
        if (publish and fingerprint in wkdlist) or (not publish and fingerprint not in wkdlist):
            return False
        elif publish: # we can guarantee it's not in the list and as such we can add it
            wkdlist.append(fingerprint)
        else:         # we can guarantee it's in the list and as such we can remove it
            wkdlist.remove(fingerprint)

        # Write to file
        print(wkdlist)
        wkdfile.truncate(0)
        wkdfile.writelines(map(lambda s: s+"\n", wkdlist))
        # Todo: Rebuild WDK
        return True
