def build_proxy_dict(proxy_settings):
    if proxy_settings:
        proxy_type = proxy_settings['proxy_type']
        if proxy_settings.get('proxy_username') and proxy_settings.get('proxy_password'):
            proxy = {
                'http': '{proxy_type}://{user}:{password}@{host}:{port}'.format(
                    proxy_type=proxy_type,
                    user=proxy_settings['proxy_username'],
                    password=proxy_settings['proxy_password'],
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                'https': '{proxy_type}://{user}:{password}@{host}:{port}'.format(
                    proxy_type=proxy_type,
                    user=proxy_settings['proxy_username'],
                    password=proxy_settings['proxy_password'],
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                    }
        else:
            proxy = {
                'http': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                'https': '{proxy_type}://{host}:{port}'.format(
                    proxy_type=proxy_type,
                    host=proxy_settings['proxy_url'],
                    port=proxy_settings['proxy_port'],
                ),
                    }
    else:
        proxy = {}

    return proxy