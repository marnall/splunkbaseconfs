import requests


class RestError(Exception):
    """
    Error from REST API client.
    """


class InvalidResponse(RestError):
    def __init__(self, response: requests.Response):
        super().__init__()
        self.response = response

    def __str__(self) -> str:
        return f'Invalid response with status {self.response.status_code}: {self.response.text}'


class RestClient:
    def __init__(self, base_url, **kwargs):
        self.base_url = base_url
        self._session = requests.session()

        for key, value in kwargs.items():
            setattr(self._session, key, value)

    def close(self):
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _request(self, method, path, resp_type='json', **kwargs):
        """
        Executing HTTP request against some RESTful API.

        Arguments:
            method (str): the HTTP method to send to the API.
            path (str): the endpoint of the request.

        Raises:
            RestError: The request has failed or the response is invalid

        Returns:
            Union[str, dict, list]: the response from the RESTful API.
        """

        try:
            resp = self._session.request(method, f'{self.base_url}/{path}', **kwargs)
        except requests.RequestException as err:
            raise RestError(f'Failed to execute request: {err}') from err

        if not resp.ok and resp_type != 'all':
            raise InvalidResponse(resp)

        if resp_type == 'json':
            return resp.json()
        if resp_type == 'text':
            return resp.text
        if resp_type == 'all':
            return resp

        raise RestError(f'Invalid response type: {resp_type}')

    def get(self, *args, **kwargs):
        return self._request('GET', *args, **kwargs)

    def post(self, *args, **kwargs):
        return self._request('POST', *args, **kwargs)

    def put(self, *args, **kwargs):
        return self._request('PUT', *args, **kwargs)

    def patch(self, *args, **kwargs):
        return self._request('PATCH', *args, **kwargs)

    def delete(self, *args, **kwargs):
        return self._request('DELETE', *args, **kwargs)
