def get_proxies(helper):
    proxies = None
    proxy_settings = helper.get_proxy()
    if proxy_settings:
        proxy_uri = proxy_settings['proxy_url'] + ':' + proxy_settings['proxy_port']
        if proxy_settings['proxy_username'] and proxy_settings['proxy_password']:
            helper.log_info("Proxy uses authentication")
            proxy_uri = proxy_settings['proxy_username'] + ':' + proxy_settings['proxy_password'] + '@' + proxy_uri
        proxy_uri = proxy_settings['proxy_type'] + '://' + proxy_uri

        # Replace username and password in logs
        proxy_uri_log_message = proxy_uri
        if proxy_settings['proxy_username'] and proxy_settings['proxy_password']:
            proxy_uri_log_message = proxy_uri_log_message.replace(proxy_settings['proxy_username'], '******').replace(
                proxy_settings['proxy_password'], '******')
        helper.log_info("Using proxy: %s" % proxy_uri_log_message)

        proxies = {
            'http': proxy_uri,
            'https': proxy_uri
        }

    return proxies