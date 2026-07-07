import csv
import os
import re
import sys

lookup_table = dict()
domain_aliases = dict()


def get_app_home():
    """
    ad_username.py executes in the bin directory which is the app bin directory
    on standalone deployments and in the temporary workspace created on replication
    in a search peer setup (distributed search). Use this directory to identify
    the active app workspace.
    """
    return os.path.join(os.path.dirname(__file__), '..')


def load_lookup_file():
    """
    load_lookup_file will load the active_directory.csv file into memory
    """
    adFile = os.path.join(get_app_home(), 'local', 'active_directory.csv')

    try:
        with open(adFile, 'r') as f:
            c = csv.reader(f)
            for row in c:
                if len(row) > 0:
                    r = {'user_domain': row[0].lower(), 'user_subject': row[1].lower()}
                    for cs_username in row[2:]:
                        lookup_table[cs_username.lower()] = r
    except Exception:
        ''' Best Effort '''
        pass


def load_aliases_file():
    """
    load_aliases_file will load the domain_aliases.csv file into memory
    """
    daFile = os.path.join(get_app_home(), 'local', 'domain_aliases.csv')

    try:
        with open(daFile, 'r') as f:
            c = csv.reader(f)
            for row in c:
                if len(row) > 0:
                    domain_aliases[row[0].lower()] = row[1].lower()
    except Exception:
        ''' Best Effort '''
        pass


class DomainAliasesFileHandler():
    '''
    Class wrapper to load in views.py
    '''

    def load(self):
        load_aliases_file()
        return domain_aliases


def convert_user(cs_username):
    """
    convert_user takes a username in whatever form and translates it into a domain and
    user dictionary for later use.
    """
    # DOMAIN\user@domain
    wsd = re.match(r"^([^\\]+)\\([^@]+)@(.*)", cs_username)
    if not (wsd is None):
        return {'user_subject': wsd.group(2), 'user_domain': wsd.group(1)}

    # DOMAIN/user@domain
    wsd = re.match(r"^([^/]+)/([^@]+)@(.*)", cs_username)
    if not (wsd is None):
        return {'user_subject': wsd.group(2), 'user_domain': wsd.group(1)}

    # Standard DOMAIN\user
    sd = re.match(r"^([^\\]+)\\(.*)", cs_username)
    if not (sd is None):
        return {'user_subject': sd.group(2), 'user_domain': sd.group(1)}

    # Standard DOMAIN/user
    sd = re.match(r"^([^/]+)/(.*)", cs_username)
    if not (sd is None):
        return {'user_subject': sd.group(2), 'user_domain': sd.group(1)}

    # More advanced user@domain
    ud = re.match(r"^([^@]+)@(.*)", cs_username)
    if not (ud is None):
        return {'user_subject': ud.group(1), 'user_domain': ud.group(2)}

    # The normal form
    return {'user_subject': cs_username, 'user_domain': 'UNKNOWN'}


if __name__ == '__main__':
    """
    Main Routine - loop through the input doing the translation
    """
    load_lookup_file()

    reader = csv.DictReader(sys.stdin)
    writer = csv.DictWriter(sys.stdout, fieldnames=reader.fieldnames)
    writer.writeheader()

    for row in reader:
        cs_username = row['cs_username']
        if cs_username.lower() in lookup_table:
            d = lookup_table[cs_username.lower()]
        else:
            d = convert_user(cs_username.lower())

        row['user_subject'] = "%s@%s" % (d['user_subject'].lower(), d['user_domain'].lower())
        writer.writerow(row)
