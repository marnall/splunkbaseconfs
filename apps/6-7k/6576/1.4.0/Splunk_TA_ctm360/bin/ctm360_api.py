from typing import Optional


class ctm360_api:
    def __init__(self, helper, api_key: str):
        """ctm360_api class initialization"""
        self.api_key = api_key
        self.helper = helper
        if not self.api_key:
            self.helper.log_error("API key is missing")
            return
        self.headers = {"Content-Type": "application/json", "api-key": self.api_key}

    # Default timeout: (connect=30s, read=120s) — generous enough for large
    # payloads (e.g. 5 000 malware-log records) while still failing fast on
    # truly unreachable hosts.
    DEFAULT_TIMEOUT = (30, 120)

    def api_call(self, url: str, parameters: Optional[dict] = None,
                 timeout=None):
        """
        Call CTM360 API
        Args:
            url: Request URL
            parameters: Request parameters, if any
            timeout: (connect, read) tuple in seconds; defaults to
                     DEFAULT_TIMEOUT (30, 120)
        Returns:
            response: Response in json
        """
        proxy_settings = self.helper.get_proxy()
        proxy_enabled = bool(proxy_settings)
        self.helper.log_debug(f"Proxy enabled: {proxy_enabled}")
        method = "GET"
        kwargs = {"headers": self.headers,
                  "timeout": timeout or self.DEFAULT_TIMEOUT}
        if parameters:
            kwargs["parameters"] = parameters
        if proxy_enabled:
            kwargs["use_proxy"] = proxy_enabled
        response = self.helper.send_http_request(url, method, **kwargs)
        return response.json()

    def get_offset(self, url: str):
        """
        Args:
            url: Request URL
        """
        try:
            offset_data = self.api_call(url)
            offset_time = offset_data["offset"]
            self.helper.log_debug(f"{url} : {offset_time}")
            return offset_time
        except Exception as e:
            raise Exception(e)
