# encoding = utf-8
"""Shared helper for extracting Jamf Pro credentials from account objects.

Used by all three input modules to avoid duplicating the auth_type / client: prefix logic.
"""


def get_jamf_credentials(helper):
    """Extract Jamf Pro credentials from the account object or legacy fields.

    Returns a dict with keys: jss_url, jss_username, jss_password. Any of the
    three may be None if the account is misconfigured; callers must guard.
    """
    account = helper.get_arg('account')

    # Account should be a dict with credentials when resolved by UCC
    # If it's a string (account name) or empty, fall back to legacy fields
    if isinstance(account, dict) and account:
        username = account.get('username', '') or ''
        stored_auth_type = account.get('auth_type')

        if stored_auth_type:
            # auth_type is explicit on the account record — trust the username
            # as-stored. Don't second-guess (e.g., a username that happens to
            # start with the literal string "client:" on a password account is
            # left alone).
            auth_type = stored_auth_type
        else:
            # Legacy storage with no auth_type field: infer from the prefix
            # convention used by the 2.12.x AOB build, and normalize the
            # username to the form the downstream auth code expects.
            if username.startswith('client:'):
                auth_type = 'api_client'
                username = username[len('client:'):]
            else:
                auth_type = 'password'

        # api_client downstream expects the "client:" prefix; restore it.
        if auth_type == 'api_client' and not username.startswith('client:'):
            username = 'client:' + username

        return {
            'jss_url': account.get('jss_url'),
            'jss_username': username,
            'jss_password': account.get('password'),
        }

    # Legacy per-input credentials fallback
    def _compat(new_key, old_key, default=None):
        v = helper.get_arg(new_key, None)
        return v if v is not None else helper.get_arg(old_key, default)

    return {
        'jss_url': _compat('jss_url', 'jssUrl', None),
        'jss_username': _compat('jss_username', 'jssUsername', None),
        'jss_password': _compat('jss_password', 'jssPassword', None),
    }
