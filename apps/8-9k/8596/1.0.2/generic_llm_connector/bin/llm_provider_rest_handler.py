from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from llm_config import load_conf_stanzas
from llm_validators import ensure_provider_not_in_use


def _get_stanza_name(handler):
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


class LLMProviderRestHandler(AdminExternalHandler):
    def handleList(self, confInfo):
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo):
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo):
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        try:
            provider_name = _get_stanza_name(self)
            ensure_provider_not_in_use(provider_name, _load_connection_entries(self))
            AdminExternalHandler.handleRemove(self, confInfo)
        except ValueError as exc:
            raise RestError(400, str(exc))
