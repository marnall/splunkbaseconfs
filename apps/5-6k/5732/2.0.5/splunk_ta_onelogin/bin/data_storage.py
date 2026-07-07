#!/usr/bin/env python
import os

import splunklib.client as client

SPLUNK_ENDPOINT = 'localhost'
SPLUNK_PORT = 8089


class DataStorage:
    APP = __file__.split(os.sep)[-3]

    def __init__(self, session_key):
        self.service = client.connect(
            host=SPLUNK_ENDPOINT, port=SPLUNK_PORT, token=session_key)

    def get_client_secret(self, client_id):
        return self._get_secret(client_id) or ''

# PRIVATE METHODS =============================================================

    def _get_password(self, storage_key, realm=None):
        return next(
            (password for password in self.service.storage_passwords
             if (password.username == storage_key and
                 password.realm == realm)),
            None
        )

    def _get_secret(self, storage_key):
        secret = (self._get_password(storage_key, self.APP) or
                  self._get_password(storage_key))
        return secret.clear_password if secret else None

