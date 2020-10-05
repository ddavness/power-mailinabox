#!/usr/local/lib/mailinabox/env/bin/python
# WDK (Web Key Directory) Manager: Facilitates discovery of keys by third-parties
# Current relevant documents: https://tools.ietf.org/id/draft-koch-openpgp-webkey-service-10.html

import pgp, utils

env = utils.load_environment()

wkdpath = f"{env['GNUPGHOME']}/.wkdlist"

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
