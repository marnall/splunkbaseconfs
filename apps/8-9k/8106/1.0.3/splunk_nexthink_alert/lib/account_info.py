from splunklib.client import Service, StoragePassword, Stanza
from typing import Optional
import json
import logging


class AccountInfo:
    APP_NAME = "splunk_nexthink_alert"
    _nexthink_host = None
    _client_id = None
    _client_secret = None

    def __init__(self, service: Service, account_name: str):
        self.service = service
        self.account_name = account_name
        self.log = logging.getLogger(self.__class__.__name__)
        self.get_info()
        self.get_password()

    @classmethod
    def get_conf_name(cls) -> str:
        return f"{cls.APP_NAME}_account"

    @property
    def nexthink_host(self) -> str:
        if self._nexthink_host is None:
            self.get_info()
        if self._nexthink_host is None:
            raise ValueError("Nexthink host was not found.")
        return self._nexthink_host

    @property
    def client_secret(self) -> str:
        if self._client_secret is None:
            self.get_password()
        if self._client_secret is None:
            raise ValueError("Client Id was not found.")
        return self._client_secret

    @property
    def client_id(self) -> str:
        if self._client_id is None:
            self.get_info()
        if self._client_id is None:
            raise ValueError("Client Id was not found.")
        return self._client_id

    @property
    def conf_name(self) -> str:
        return self.__class__.get_conf_name()

    @property
    def realm(self) -> str:
        return f"__REST_CREDENTIAL__#{self.APP_NAME}#configs/conf-{self.conf_name}"

    def get_password(self):
        storage_password: Optional[StoragePassword] = None
        self.log.debug("Retrieving account credentials.")
        for storage_password in self.service.storage_passwords:
            if storage_password is None:
                continue
            if (
                storage_password.realm == self.realm
                and storage_password.username
                == f"{self.account_name}``splunk_cred_sep``1"
                and storage_password.clear_password is not None
            ):
                clear_password = json.loads(storage_password.clear_password)
                self._client_secret = clear_password.get("client_secret")
                return

        raise ValueError(f"Credential not found for account: {self.account_name}")

    def get_info(self):
        stanza: Optional[Stanza] = None
        self.log.debug("Retrieving account info.")
        for stanza in self.service.confs[self.conf_name]:
            if stanza is None:
                continue
            if stanza.name == self.account_name:
                self._client_id = stanza.content.get("client_id")
                self._nexthink_host = stanza.content.get("nexthink_hostname")
                return
        raise ValueError(f"Account not found: {self.account_name}")

    def __str__(self) -> str:
        data = {
            "account_name": self.account_name,
            "nexthink_host": self.nexthink_host,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        return json.dumps(data)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(service, {self.account_name})"
