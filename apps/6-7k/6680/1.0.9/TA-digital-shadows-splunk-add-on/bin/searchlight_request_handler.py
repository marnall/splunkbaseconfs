from searchlight.http import HttpRequestHandler

class SearchLightRequestHandler(HttpRequestHandler):
    def __init__(self, request_handler, base_url, account_id, access_key, secret_key, use_proxy=False, **kwargs):
        super().__init__(base_url, account_id, access_key, secret_key, **kwargs)
        self.request_handler = request_handler
        self.use_proxy = use_proxy
        self.timeout = 60

    def get(self,
            url,
            params={},
            data=None,
            headers={},
            verify=True,
            timeout=None,
            proxy_uri=None,
            use_proxy=False
        ):
        return self._send_http_request("GET", url, params, data, headers, verify, timeout, proxy_uri, self.use_proxy)

    def post(self,
            url,
            params={},
            json=None,
            headers={},
            verify=True,
            timeout=None,
            proxy_uri=None,
            use_proxy=False
        ):
        return self._send_http_request("POST", url, params, json, headers, verify, timeout, proxy_uri, self.use_proxy)

    def put(self,
            url,
            params={},
            json=None,
            headers={},
            verify=True,
            timeout=None,
            proxy_uri=None,
            use_proxy=False
        ):
        return self._send_http_request("PUT", url, params, json, headers, verify, timeout, proxy_uri, self.use_proxy)

    def _send_http_request(self, method, url,
        params={},
        data=None,
        headers={},
        verify=True,
        timeout=None,
        proxy_uri=None,
        use_proxy=False
    ):
        kwargs = {}
        if use_proxy:
            kwargs['use_proxy'] = True
        if proxy_uri:
            kwargs['proxy_uri'] = proxy_uri
        if headers:
            headers.update(**self.headers)
        else:
            headers = self.headers
        if timeout is None:
            timeout = self.timeout

        resp = self.request_handler.send_http_request(url=self.base_url + url, method=method, headers=headers,
                                                      parameters=params, payload=data, verify=verify, timeout=timeout,
                                                      **kwargs)
        return self.rate_limit_response(resp)
