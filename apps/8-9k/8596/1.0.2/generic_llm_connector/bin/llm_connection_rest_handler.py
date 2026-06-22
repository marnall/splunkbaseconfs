from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from llm_config import clear_default_flag, load_conf_stanzas
from llm_validators import find_existing_default_connections


def _get_current_name(handler):
    if handler.payload and handler.payload.get("name"):
        return handler.payload.get("name")

    stanza_ids = getattr(handler.callerArgs, "id", None) or []
    if stanza_ids:
        return stanza_ids[0]
    return None


def _load_connection_entries(handler):
    return list(
        load_conf_stanzas(
            handler.getSessionKey(),
            "generic_llm_connector_connection",
        ).values()
    )


def _clean_payload(payload):
    cleaned_payload = dict(payload)
    cleaned_payload.pop("test_connection", None)
    return cleaned_payload


class LLMConnectionRestHandler(AdminExternalHandler):
    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        try:
            self.payload = _clean_payload(self.payload)
            old_defaults = find_existing_default_connections(
                self.payload,
                _load_connection_entries(self),
                current_name=_get_current_name(self),
            )
            clear_default_flag(self.getSessionKey(), old_defaults)
            AdminExternalHandler.handleEdit(self, confInfo)
        except ValueError as exc:
            raise RestError(400, str(exc))

    def handleCreate(self, confInfo):
        try:
            self.payload = _clean_payload(self.payload)
            old_defaults = find_existing_default_connections(
                self.payload,
                _load_connection_entries(self),
                current_name=None,
            )
            clear_default_flag(self.getSessionKey(), old_defaults)
            AdminExternalHandler.handleCreate(self, confInfo)
        except ValueError as exc:
            raise RestError(400, str(exc))

    def handleRemove(self, confInfo):
        AdminExternalHandler.handleRemove(self, confInfo)
