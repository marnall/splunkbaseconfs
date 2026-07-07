import datetime
import json


class Token(object):
    AUTH_BACKEND = "https://login.gem.security/oauth/token"
    AUDIENCE = "https://backend.gem.security"
    TOKEN_NAME = "gem-security-token-cache"
    TOKEN_EXPIRE_TIME_DRIFT = datetime.timedelta(seconds=600)

    def __init__(self, helper, client_id, client_secret):
        self._helper = helper
        self._client_id = client_id
        self._client_secret = client_secret
        self._cache_key = "{}-{}".format(self.TOKEN_NAME, self._client_id)
        self._found_cache = False

    @classmethod
    def _build(cls, data):
        token_type = data["token_type"]
        access_token = data["access_token"]
        return " ".join((token_type, access_token))

    def _request_token(self):
        self._helper.log_debug("Requesting new token")
        resp = self._helper.send_http_request(
            self.AUTH_BACKEND,
            "POST",
            payload={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
                "audience": self.AUDIENCE,
            },
        )

        resp.raise_for_status()
        data = resp.json()

        token = self._build(data)
        self._save_cache(token, data)
        return token

    def _save_cache(self, token, data):
        expires_in = data["expires_in"]

        expire = datetime.datetime.now() + datetime.timedelta(seconds=expires_in)
        storage_password_object = {"token": token, "expire": expire.isoformat()}

        if self._found_cache:
            self.clear_cache()

        try:
            self._helper.service.storage_passwords.create(json.dumps(storage_password_object), self._cache_key)
            self._found_cache = True
        except Exception as e:
            self._helper.log_error(repr(e))

    def clear_cache(self):
        """
        Best effort to clean cache
        """
        self._helper.log_debug("Remove cache {}".format(self._cache_key))

        try:
            self._helper.service.storage_passwords.delete(self._cache_key)
            self._found_cache = False
        except Exception as e:
            self._helper.log_error("Failed removing cache {}".format(self._cache_key))
            self._helper.log_error(repr(e))

        return None

    def _get_cache(self):
        try:
            response = self._helper.service.storage_passwords[self._cache_key]
            self._found_cache = True
            password_parsed = json.loads(response.clear_password)
            expire = datetime.datetime.fromisoformat(password_parsed["expire"])

            if (expire - self.TOKEN_EXPIRE_TIME_DRIFT) > datetime.datetime.now():
                return password_parsed["token"]
        except Exception as e:
            self._helper.log_error("Failed getting cache {}".format(self._cache_key))
            self._helper.log_error(repr(e))

        return None

    def get(self):
        token = self._get_cache()
        if not token:
            token = self._request_token()
        return token
