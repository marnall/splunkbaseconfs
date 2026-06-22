import import_declare_test

import logging

from splunktaucclib.rest_handler import admin_external, util
from splunktaucclib.rest_handler.admin_external import (
    AdminExternalHandler,
    build_conf_info,
)
from splunktaucclib.rest_handler.endpoint import RestModel, SingleModel, field
from splunktaucclib.rest_handler.entity import RestEntity
from splunktaucclib.rest_handler.error import RestError

from llm_connection_test_service import test_connection


util.remove_http_proxy_env_vars()

fields = [
    field.RestField("provider", required=False, encrypted=False, default=None),
    field.RestField("model", required=False, encrypted=False, default=None),
    field.RestField("max_tokens", required=False, encrypted=False, default=None),
]

model = RestModel(fields, name=None)

endpoint = SingleModel(
    "llm_connection_test",
    model,
    config_name="llm_connection_test",
    need_reload=False,
)


class LLMConnectionTestHandler(AdminExternalHandler):
    @build_conf_info
    def handleCreate(self, confInfo):
        try:
            result = test_connection(
                session_key=self.getSessionKey(),
                payload=self.payload,
            )
        except ValueError as exc:
            raise RestError(400, str(exc))

        return [
            RestEntity(
                self.callerArgs.id or "test_connection",
                result,
                self.endpoint.model(self.callerArgs.id),
                self.endpoint.user,
                self.endpoint.app,
            )
        ]


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=LLMConnectionTestHandler,
    )
