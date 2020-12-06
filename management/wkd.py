#!/usr/local/lib/mailinabox/env/bin/python
# WDK (Web Key Directory) Manager: Facilitates discovery of keys by third-parties
# Current relevant documents: https://tools.ietf.org/id/draft-koch-openpgp-webkey-service-11.html

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


@pgp.fork_context
# Strips and exports a key so that only the provided UID index(es) remain.
# This is to comply with the following requirement, set forth in section 5 of the draft:
#
# The mail provider MUST make sure to publish a key in a way
# that only the mail address belonging to the requested user
# is part of the User ID packets included in the returned key.
# Other User ID packets and their associated binding signatures
# MUST be removed before publication.
def strip_and_export(fpr, except_uid_indexes, context):
	context.armor = False # We need to disable armor output for this key
	k = pgp.get_key(fpr, context)
	if k is None:
		return None
	for i in except_uid_indexes:
		if i > len(k.uids):
			raise ValueError(f"UID index {i} out of bounds")

	switch = [(f"uid {i+1}" if i + 1 not in except_uid_indexes else "") for i in range(len(k.uids))] + ["deluid", "save"]
	stage = [-1] # Horrible hack: Because it's a reference (aka pointer), we can pass these around
	def interaction(request, prompt):
		print(f"{request}/{prompt}")
		if request in ["GOT_IT", "KEY_CONSIDERED", ""]:
			return 0
		elif request == "GET_BOOL":
			# No way to confirm interactively, so we just say yes
			return "y" # Yeah, I'd also rather just return True but that doesn't work
		elif request == "GET_LINE" and prompt == "keyedit.prompt":
			stage[0] += 1
			return switch[stage[0]]
		else:
			raise Exception("No idea of what to do!")

	context.interact(k, interaction)
	return pgp.export_key(fpr, context)

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
