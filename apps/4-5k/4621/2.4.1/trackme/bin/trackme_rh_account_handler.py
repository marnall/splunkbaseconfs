import import_declare_test
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
import json
import requests


class CustomRestHandlerCreateRemoteAccount(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def checkConnectivity(self):
        # set call
        header = {
            "Authorization": "Splunk %s" % self.getSessionKey(),
            "Content-Type": "application/json",
        }

        url = (
            "%s/services/trackme/v2/configuration/test_remote_connectivity"
            % self.handler._splunkd_uri
        )
        data = {
            "target_endpoints": self.payload.get("splunk_url"),
            "bearer_token": self.payload.get("bearer_token"),
            "app_namespace": self.payload.get("app_namespace"),
        }

        # check connectivity, raise an exception if the connectivity check fails
        try:
            response = requests.post(
                url,
                headers=header,
                data=json.dumps(data, indent=1),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                msg = f'remote connectivity check has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                raise Exception(msg)
        except Exception as e:
            raise Exception(str(e))

    def updateMetadata(self, action):
        # set call
        header = {
            "Authorization": "Splunk %s" % self.getSessionKey(),
            "Content-Type": "application/json",
        }

        url = (
            "%s/services/trackme/v2/configuration/admin/remote_account_update_token_metadata"
            % self.handler._splunkd_uri
        )
        data = {
            "account": self.payload.get("name"),
            "action": action,
            "raw_payload": self.payload,
        }

        # check connectivity, raise an exception if the connectivity check fails
        try:
            response = requests.post(
                url,
                headers=header,
                data=json.dumps(data, indent=1),
                verify=False,
                timeout=600,
            )
            if response.status_code not in (200, 201, 204):
                msg = f'metadata update has failed, response.status_code="{response.status_code}", response.text="{response.text}"'
                raise Exception(msg)
        except Exception as e:
            raise Exception(str(e))

    def _resolve_masked_secret(self, field_name):
        """If the payload field is the UCC mask, replace it with the real value."""
        if self.payload.get(field_name) == self.handler.PASSWORD:
            try:
                entities = list(
                    self.handler.get(self.callerArgs.id, decrypt=True)
                )
                if entities:
                    real_value = entities[0].content.get(field_name)
                    if real_value and real_value != self.handler.PASSWORD:
                        self.payload[field_name] = real_value
            except Exception:
                pass

    def _decrypt_response(self, confInfo, field_name):
        """Replace masked secret in the response so the frontend caches the real value."""
        try:
            entities = list(
                self.handler.get(self.callerArgs.id, decrypt=True)
            )
            if entities:
                real_value = entities[0].content.get(field_name)
                if real_value and real_value != self.handler.PASSWORD:
                    confInfo[self.callerArgs.id][field_name] = real_value
        except Exception:
            pass

    def handleList(self, confInfo):
        # Request decrypted credentials so edit forms are pre-populated
        self.callerArgs.data[self.ACTION_CRED] = ["1"]
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        self._resolve_masked_secret("bearer_token")
        self.checkConnectivity()
        # self.updateMetadata("update")
        AdminExternalHandler.handleEdit(self, confInfo)
        # Override masked secret in the response so the frontend caches the real value
        self._decrypt_response(confInfo, "bearer_token")

    def handleCreate(self, confInfo):
        self.checkConnectivity()
        # self.updateMetadata("update")
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        # self.updateMetadata("delete")
        AdminExternalHandler.handleRemove(self, confInfo)
