"""
Description:
    Splunk related functionality.

Authors:
    Peter Uys, Cylance Inc.
"""


import re

import splunk.entity as entity


g_app_name = 'cylance_protect'
g_token_length = 32
g_cylance_tag = 'cYlAnCe0tEnAnT'

def is_valid_url(url):
    pattern = re.compile(r'^https://.+cylance.com/Reports/ThreatDataReportV[0-9]+$', re.IGNORECASE)
    result = pattern.match(url.strip())
    if not result:
        return False
    else:
        return (result.group() == url.strip())


def is_valid_token(token):
    try:
        int(token, 16) # base 16
    except:
        return False
    if len(token) == g_token_length:
        return True
    else:
        return False


# access the credentials in /servicesNS/nobody/<YourApp>/storage/passwords
def get_passwords(session_key):

    try:
        # list all credentials
        entities = entity.getEntities(
            ['storage', 'passwords'], namespace=g_app_name, owner='nobody', sessionKey=session_key)
    except Exception as e:
        raise Exception("Could not get %s credentials from splunk. Error: %s" % (g_app_name, str(e)))

    # return credentials
    tenants = []
    if entities:
        for i, ent in list(entities.items()):
            entry_name = ent['username']
            if not entry_name.startswith(g_cylance_tag):
                continue
            tenant_name = entry_name[len(g_cylance_tag):]
            url_token = ent['clear_password']
            url = url_token.strip()[:-(g_token_length+1)]
            token = url_token.strip()[-g_token_length:]

            if not is_valid_url(url):
                return []
            if not is_valid_token(token):
                return []
            tenants.append({
                'TenantName' : tenant_name,
                'ThreatDataReportURL' : url,
                'ThreatDataReportToken' : token })

    return tenants


def get_tenants(session_key):

    return get_passwords(session_key)
