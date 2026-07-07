"""NetApp util module."""


import requests


def get_proxy_setting(proxy):
    """Provide proxy in format."""
    if not proxy:
        return {"http": None, "https": None}

    proxy_username = proxy["proxy_username"]
    proxy_password = proxy["proxy_password"]
    proxy_url = proxy["proxy_url"]
    proxy_port = proxy["proxy_port"]
    proxy_type = proxy["proxy_type"]

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
    return {"http": proxy_uri, "https": proxy_uri}
