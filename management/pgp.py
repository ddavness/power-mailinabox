# Tools to manipulate PGP keys

import gpg, utils

env = utils.load_environment()
gpghome = env['GNUPGHOME']
context = gpg.Context(armor=True, home_dir=gpghome)

def get_daemon_key():
    pass

def get_imported_keys():
    pass

def import_key(key):
    pass

def export_key(fingerprint):
    pass

def delete_key(fingerprint):
    pass
