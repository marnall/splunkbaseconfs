"""
Account tab REST handler: a Cisodium account is saved only if Cisodium says
the URL and API key work.

Saving calls `GET /api/v2/siem/whoami` with the key (through the add-on's proxy
settings) and refuses the account with Cisodium's own reason when the call
fails — a wrong URL, a revoked key or a key without the SIEM scope shows up on
the Configuration page, not hours later in the input's log.

On edit, an unchanged API key arrives as the UI's mask; the stored key is read
back (decrypted) to run the same check.

Refusals are raised as admin.ArgValidationException: splunkd answers those
with a 400 carrying just the message, which the Configuration page shows as
is. Any other exception type comes back as "500 Unexpected error … from python
handler" around the same text.
"""

import import_declare_test  # noqa: F401  (UCC: puts ../lib on sys.path)
from solnlib import conf_manager
from splunk import admin
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler

from cisodium_client import (
    CisodiumClient,
    CisodiumError,
    looks_like_api_key,
    normalize_base_url,
    proxies_from_settings,
)

ADDON_NAME = "TA_cisodium"
SETTINGS_CONF = "ta_cisodium_settings"
_MASKS = ("******", "********")


def _proxy_settings(session_key):
    try:
        cfm = conf_manager.ConfManager(
            session_key,
            ADDON_NAME,
            realm="__REST_CREDENTIAL__#%s#configs/conf-%s" % (ADDON_NAME, SETTINGS_CONF),
        )
        return cfm.get_conf(SETTINGS_CONF).get("proxy")
    except Exception:
        return None


def refuse(message):
    return admin.ArgValidationException(message)


def check_account(url, api_key, session_key):
    """Raise a 400 unless Cisodium accepts this URL and key."""
    try:
        base_url = normalize_base_url(url)
    except ValueError as exc:
        raise refuse(str(exc))
    if not looks_like_api_key(api_key):
        raise refuse(
            "The API key must be a Cisodium platform key: cso_ followed by 64 hex characters."
        )
    client = CisodiumClient(
        base_url,
        api_key,
        proxies=proxies_from_settings(_proxy_settings(session_key)),
        timeout=30,
        max_retries=1,
        max_backoff=5,
    )
    try:
        answer = client.whoami()
    except CisodiumError as exc:
        raise refuse(str(exc))
    if not isinstance(answer.get("feeds"), list):
        raise refuse(
            "%s answered, but not like a Cisodium SIEM feed API; check the URL." % base_url
        )
    return answer


class CisodiumAccountHandler(AdminExternalHandler):
    def __init__(self, *args, **kwargs):
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def _stored_api_key(self):
        for entity in self.handler.get(self.callerArgs.id, decrypt=True):
            return (entity.content or {}).get("api_key")
        return None

    def handleCreate(self, confInfo):
        check_account(
            self.payload.get("url"),
            self.payload.get("api_key"),
            self.getSessionKey(),
        )
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        # Enabling/disabling an account posts only `disabled`; nothing to check.
        if self.payload.get("disabled") is None:
            api_key = self.payload.get("api_key")
            if not api_key or api_key in _MASKS:
                api_key = self._stored_api_key()
            url = self.payload.get("url")
            if not url:
                for entity in self.handler.get(self.callerArgs.id):
                    url = (entity.content or {}).get("url")
            check_account(url, api_key, self.getSessionKey())
        AdminExternalHandler.handleEdit(self, confInfo)
