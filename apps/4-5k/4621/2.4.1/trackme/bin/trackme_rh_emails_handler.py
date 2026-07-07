import import_declare_test

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler


class CustomRestHandlerCreateEmails(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

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

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        self._resolve_masked_secret("email_password")
        AdminExternalHandler.handleEdit(self, confInfo)
        self._decrypt_response(confInfo, "email_password")

    def handleList(self, confInfo):
        # Request decrypted credentials so edit forms are pre-populated
        self.callerArgs.data[self.ACTION_CRED] = ["1"]
        AdminExternalHandler.handleList(self, confInfo)

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)
