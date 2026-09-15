import os
import json
import requests
import splunk.admin as admin
from splunk_secret_helper import set_secret

APP = "arubacentral-api-app_v1"
SETTINGS_PATH = os.path.join(
    os.environ.get("SPLUNK_HOME", "/opt/splunk"),
    "etc", "apps", APP, "local", "arubacentral_settings.json"
)

class ArubaSetupHandler(admin.MConfigHandler):
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["hpe_base_url", "token_url", "client_id", "client_secret","aruba_base_url"]:
                self.supportedArgs.addOptArg(arg)

    def handleEdit(self, confInfo):
        session_key = self.getSessionKey()
        hpe_base_url = self.callerArgs["hpe_base_url"][0]
        token_url = self.callerArgs["token_url"][0]
        client_id = self.callerArgs["client_id"][0]
        client_secret = self.callerArgs["client_secret"][0]
        aruba_base_url = self.callerArgs["aruba_base_url"][0]

        test = requests.post(
            f"{hpe_base_url}{token_url}",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret
            },
            verify=True,
            timeout=30
        )
        test.raise_for_status()
        token_payload = test.json()

        set_secret(session_key, "client_id", client_id)
        set_secret(session_key, "client_secret", client_secret)
        set_secret(session_key, "access_token", token_payload["access_token"])

        settings = {
            "hpe_base_url": hpe_base_url,
            "token_url": token_url,
            "verify_tls": True,
            "aruba_base_url": aruba_base_url
        }

        os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
        with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)

def main():
    admin.init(ArubaSetupHandler, admin.CONTEXT_APP_ONLY)

if __name__ == "__main__":
    main()