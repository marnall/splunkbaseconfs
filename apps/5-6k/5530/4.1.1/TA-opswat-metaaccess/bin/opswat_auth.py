def get_auth_token(helper, client_key, client_secret, host, auth_endpoint, use_proxy):
    endpoint = 'https://{}/{}'.format(host, auth_endpoint)
    payload = 'client_id={}&client_secret={}&grant_type=client_credentials&verify=true'.format(client_key, client_secret)

    helper.log_info('Invoking authentication request to {}'.format(endpoint))

    if 'oauth2/token' in endpoint:
        r = helper.send_http_request(
            endpoint,
            'POST',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            payload=payload,
            cookies=None,
            timeout=None,
            use_proxy=use_proxy
        )
    else:
        r = helper.send_http_request(
            endpoint,
            'POST',
            headers={
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            payload=payload,
            cookies=None,
            timeout=None,
            use_proxy=use_proxy
        )

    r_json = r.json()

    if r.ok:
        token = 'Bearer {}'.format(r_json['access_token'])
        helper.log_info('Successful authentication request, received new token.')
        return token

    else:
        helper.log_error('Failed authentication request: {0}. Message={1}'.format(r.status_code, r.text))
        return None
