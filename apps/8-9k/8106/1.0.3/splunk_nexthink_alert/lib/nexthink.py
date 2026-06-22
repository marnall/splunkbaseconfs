import requests
import json
import time
import logging


class Nexthink:
    def __init__(self, host: str):
        self._session = requests.Session()
        self._host = host
        self.log = logging.getLogger(self.__class__.__name__)
        if host.startswith("https://"):
            self._host = self._host.replace("https://", "")
        self._base_url = f"https://{self._host}/api/v1"

    def authorize(self, client_id: str, client_secret: str) -> dict:
        ret = self._session.post(
            f"{self._base_url}/token", auth=(client_id, client_secret)
        )
        ret.raise_for_status()
        data = ret.json()
        self._session.headers = {
            "Authorization": f"{data.get('token_type', 'Bearer')} {data.get('access_token', '')}"
        }
        self.log.debug("Authorizing...")
        # Set the expiry time 5 seconds before
        self._expire: float = float(data.get("expires_in", "0")) + time.time() - 5
        self._token_type: str = data.get("token_type", "Bearer")
        self._access_token: str = data.get("access_token", "")
        return data

    def __str__(self) -> str:
        return json.dumps(
            {
                "host": self._host,
                "token_type": self._token_type,
                "access_token": self._access_token,
                "expiry": self._expire,
            }
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}:{self.__str__()}"

    def get_remote_actions(self) -> dict:
        resp = self._session.get(f"{self._base_url}/act/remote-action")
        resp.raise_for_status()
        return resp.json()

    def execute_remote_action(
        self,
        remote_action_id: str,
        device_uids: list[str],
        params: dict = None,
        reason: str = "",
        external_reference: str = "",
        expires_in_minutes: int = 60,
        external_source: str = "Splunk",
    ) -> dict:
        payload = json.dumps(
            {
                "remoteActionId": remote_action_id,
                "params": {} if params is None else params,
                "devices": device_uids,
                "expiresInMinutes": expires_in_minutes,
                "triggerInfo": {
                    "externalSource": external_source,
                    "reason": reason,
                    "externalReference": external_reference,
                },
            }
        )
        self.log.debug(f"payload: {payload}")
        resp = self._session.post(f"{self._base_url}/act/execute", data=payload)
        resp.raise_for_status()
        return resp.json()
