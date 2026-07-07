from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Callable

from splunk import admin
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path

sys.path.insert(0, make_splunkhome_path(["etc", "apps", "alphasoc_for_splunk", "bin"]))

from a4slib.config import ALPHASOC_CONF, ConfigError
from a4slib.config import api as api_config
from a4slib.config import findings as findings_config

if TYPE_CHECKING:
    from collections.abc import Mapping

EAI_PREFIX = "eai:"

_SETTERS: dict[tuple[str, str], Callable[[admin.MConfigHandler, str], str]] = {
    (api_config.STANZA, api_config.URL_KEY): api_config.set_url,
    (findings_config.STANZA, findings_config.INDEX_KEY): findings_config.set_index,
}


def caller_arg(caller_args: admin.ArgsInfo, key: str) -> str:
    value = caller_args.data.get(key, "")
    if isinstance(value, list):
        value = value[0] if value else ""
    return value.strip() if isinstance(value, str) else ""


class AlphaSOCConfigHandler(admin.MConfigHandler):
    def setup(self) -> None:
        if self.requestedAction not in (admin.ACTION_LIST, admin.ACTION_EDIT):
            return

        conf = self.readConf(ALPHASOC_CONF)
        for stanza_data in conf.values():
            for key in stanza_data:
                if not key.startswith(EAI_PREFIX):
                    self.supportedArgs.addOptArg(key)

    def handleList(self, conf_info: dict[str, dict[str, str]]) -> None:  # noqa: N802
        conf = self.readConf(ALPHASOC_CONF)
        for stanza_name, stanza_data in conf.items():
            for key, value in stanza_data.items():
                if not key.startswith(EAI_PREFIX):
                    conf_info[stanza_name][key] = str(value).strip()

    def handleEdit(self, conf_info: dict[str, dict[str, str]]) -> None:  # noqa: N802
        stanza_name = self.callerArgs.id
        conf = self.readConf(ALPHASOC_CONF)

        if stanza_name not in conf:
            message = f"Unknown stanza {stanza_name!r}."
            raise admin.ArgValidationException(message)

        current = _user_fields(conf[stanza_name])

        updates: dict[str, str] = {}
        for key in current:
            value = caller_arg(self.callerArgs, key)
            if value:
                updates[key] = value

        if not updates:
            message = "At least one setting must be provided."
            raise admin.ArgValidationException(message)

        for key, value in updates.items():
            setter = _SETTERS.get((stanza_name, key))
            if setter is None:
                message = f"Field {key!r} is not editable on '[{stanza_name}]'."
                raise admin.ArgValidationException(message)
            try:
                conf_info[stanza_name][key] = setter(self, value)
            except ConfigError as exc:
                raise admin.ArgValidationException(str(exc)) from exc


def _user_fields(stanza_data: Mapping[str, object]) -> dict[str, str]:
    return {k: str(v).strip() for k, v in stanza_data.items() if not k.startswith(EAI_PREFIX)}


admin.init(AlphaSOCConfigHandler, "app")
