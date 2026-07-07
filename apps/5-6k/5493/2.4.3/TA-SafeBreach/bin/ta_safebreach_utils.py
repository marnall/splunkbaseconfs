"""This is utils file for safebreach."""

import ta_safebreach_declare  # noqa: F401
import requests


def get_proxy_setting(proxy_dict):
    """Genrate proxy uri."""
    if not proxy_dict:
        proxy_settings = None
    else:
        proxy_type = proxy_dict.get("proxy_type", "")
        proxy_username = proxy_dict.get("proxy_username", "")
        proxy_password = proxy_dict.get("proxy_password", "")
        proxy_url = proxy_dict.get("proxy_url", "")
        proxy_port = proxy_dict.get("proxy_port", "")
        """Get Proxy Settings."""
        if proxy_username and proxy_password:
            proxy_username = requests.compat.quote_plus(proxy_username)
            proxy_password = requests.compat.quote_plus(proxy_password)
            proxy_uri = "%s://%s:%s@%s:%s" % (
                proxy_type,
                proxy_username,
                proxy_password,
                proxy_url,
                proxy_port,
            )
        else:
            proxy_uri = "%s://%s:%s" % (proxy_type, proxy_url, proxy_port)
        proxy_settings = {"http": proxy_uri, "https": proxy_uri}

    return proxy_settings
