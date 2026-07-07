import requests
import json
import re
from urllib.parse import urljoin, urlparse, parse_qs


class MFATokenError(Exception):
    """Custom exception to indicate that Multi-Factor Authentication is required."""

    def __init__(self, message="MFA is enabled"):
        """Intializes the MFATokenError instance."""
        super().__init__(message)


class AzureSSOToken:
    """Azure SSO Token class."""

    def __init__(
        self,
        host,
        sso_user,
        sso_pass,
        logger,
        proxies,
        verify_cert,
    ):
        """Initializes an instance of the class."""
        self.host = host
        self.sso_user = sso_user
        self.sso_pass = sso_pass
        self.logger = logger
        self.proxies = proxies
        self.verify_cert = verify_cert

        self.client = requests.Session()
        self.client.verify = verify_cert
        self.client.proxies.update(proxies)

        self.logger.log_info("Intiating to get Azure SSO Token.")

    def http_request(
        self,
        url,
        method="GET",
        params=None,
        data=None,
        headers=None,
        timeout=None,
        auth=None,
        cookies=None,
        json=None,
    ):
        """Sends an HTTP request to the specified URL using the specified method."""
        try:
            response = self.client.request(
                method,
                url,
                params=params,
                data=data,
                headers=headers,
                timeout=timeout,
                auth=auth,
                cookies=cookies,
                json=json,
            )
            return response
        except Exception as e:
            self.logger.log_error(f"Monitoring HTTP request for SSO: An error occurred - {e}")
            raise

    def get_sso_auth_token(self):
        """Retrieves the SSO authentication token."""
        auth_data = self.get_authorization_data()
        ms_resp2 = self.perform_sso_login(auth_data)

        if ms_resp2.status_code == 401:
            return self.handle_401_response(ms_resp2)

        return None

    def get_authorization_data(self):
        """Sends a POST request to the SAML authorization endpoint to retrieve the authorization data."""
        resp = self.http_request(
            method="POST",
            url=f"https://{self.host}/api/v3/authorize-saml",
            json={"AccountId": ""},
        )

        resp.raise_for_status()
        data = resp.json()

        ms_resp = self.http_request(method="GET", url=data["data"])

        ms_resp.raise_for_status()

        config_data = self.extract_config_data(ms_resp.text)
        ms_request_id = ms_resp.headers.get("X-Ms-Request-Id")
        return config_data, ms_request_id

    def extract_config_data(self, response_text):
        """Extracts configuration data from a given response text."""
        config_re = re.compile(r"\$Config=({.*?});")

        matches = config_re.search(response_text)

        if not matches:
            raise ValueError("No matches for regex")

        return json.loads(matches.group(1))

    def perform_sso_login(self, auth_data):
        """Performs a single sign-on (SSO) login using the given authentication data."""
        config_data, ms_request_id = auth_data
        canary = config_data["canary"]
        flowtoken = self.get_flow_token(config_data)

        url_login = config_data["urlLogin"]
        u = urlparse(url_login)
        query = parse_qs(u.query)
        ctx = query.get("ctx", [""])[0]

        form_data = {
            "login": self.sso_user,
            "loginfmt": self.sso_user,
            "passwd": self.sso_pass,
            "canary": canary,
            "ctx": ctx,
            "LoginOptions": 3,
            "hpgrequestid": ms_request_id,
            "flowToken": flowtoken,
            "CookieDisclosure": 0,
        }

        ms_resp2 = self.http_request(
            method="POST",
            url=urljoin("https://login.microsoftonline.com", config_data["urlPost"]),
            data=form_data,
        )

        return ms_resp2

    def get_flow_token(self, config_data):
        """Retrieves the flow token for the given configuration data."""
        url_login = config_data["urlLogin"]
        u = urlparse(url_login)
        query = parse_qs(u.query)
        ctx = query.get("ctx", [""])[0]

        get_cred_response = self.http_request(
            method="POST",
            url="https://login.microsoftonline.com/common/GetCredentialType",
            json={
                "FlowToken": config_data["sFT"],
                "OriginalRequest": ctx,
                "Username": self.sso_user,
            },
        )

        get_cred_response.raise_for_status()
        return get_cred_response.json()["FlowToken"]

    def handle_401_response(self, ms_resp2):
        """Handle the 401 response from the server."""
        request_value = re.search(r'<input.*name="request"\svalue="(.*?)"', ms_resp2.text)
        flowtoken_value = re.search(r'<input.*name="flowToken"\svalue="(.*?)"', ms_resp2.text)

        request_value = request_value.group(1)
        flowtoken_value = flowtoken_value.group(1)

        form_data = {
            "ctx": request_value,
            "flowtoken": flowtoken_value,
        }
        headers = {
            "Origin": "https://device.login.microsoftonline.com",
            "Referer": "https://device.login.microsoftonline.com/",
        }

        x = self.http_request(
            method="POST",
            url="https://login.microsoftonline.com/common/DeviceAuthTls/reprocess",
            data=form_data,
            headers=headers,
        )

        x.raise_for_status()
        res = self.extract_config_data(x.text)

        form_data5 = {
            "ctx": res["sCtx"],
            "hpgrequestid": x.headers.get("X-Ms-Request-Id", ""),
            "flowToken": res["sFT"],
            "canary": res["canary"],
        }

        headers = {
            "Origin": "https://login.microsoftonline.com",
            "Referer": "https://login.microsoftonline.com/common/DeviceAuthTls/reprocess",
        }

        ms_resp3 = self.http_request(
            method="POST",
            url="https://login.microsoftonline.com/kmsi",
            data=form_data5,
            headers=headers,
        )

        ms_resp3.raise_for_status()
        return self.handle_saml_response(ms_resp3.text)

    def handle_saml_response(self, response_text):
        """Handle the saml response from the server."""
        form_re = re.compile(r'action="(.*?)".*?name="SAMLResponse" value="(.*?)"')
        matches3 = form_re.search(response_text)

        if not matches3:
            config_data = self.extract_config_data(response_text)
            if config_data["arrUserProofs"]:
                self.logger.log_debug("MFA is enabled.")
                raise MFATokenError("Multi-factor authentication (MFA) is enabled, please disable to proceed.")

            raise ValueError("No matches for regex")

        saml_response = {
            "SAMLResponse": matches3.group(2),
            "RelayState": "0",
        }
        auth_resp = self.http_request(method="POST", url=matches3.group(1), data=saml_response)
        auth_resp.raise_for_status()
        auth = auth_resp.json()

        if not auth.get("data"):
            raise ValueError("Auth data is missing")

        self.logger.log_info("Received SSO auth token successfully")

        return {"auth_token": str(auth["data"])}
