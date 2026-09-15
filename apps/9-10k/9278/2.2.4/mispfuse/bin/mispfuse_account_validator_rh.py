"""Validate a MISP account before UCC stores it."""

import import_declare_test  # noqa: F401

import logging

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from mispfuse_lib.config import ConfigError, get_account, get_proxies
from mispfuse_lib.connection import (
    ConnectionTestError,
    resolve_account_values,
    test_misp_connection,
)

_LOGGER = logging.getLogger("mispfuse.account_validation")


class MispAccountValidator(AdminExternalHandler):
    """Reject account creates/edits whose MISP connection test fails."""

    def _existing_account(self, session_key, account_name):
        if not account_name:
            return None
        try:
            return get_account(session_key, account_name)
        except ConfigError:
            return None

    def _validate_connection(self, editing=False):
        session_key = self.getSessionKey()
        account_name = self.callerArgs.id or self.payload.get("name")
        existing = (
            self._existing_account(session_key, account_name) if editing else None
        )

        try:
            account = resolve_account_values(self.payload, existing=existing)
            proxies = get_proxies(session_key)
            result = test_misp_connection(
                account["misp_url"],
                account["misp_key"],
                verify_ssl=account["verify_ssl"],
                proxies=proxies,
            )
        except ConnectionTestError as exc:
            _LOGGER.warning(
                "MISP connection validation failed for account=%r: %s",
                account_name,
                exc,
            )
            raise RestError(400, str(exc)) from exc
        except Exception as exc:
            _LOGGER.error(
                "Unexpected MISP account validation failure for account=%r "
                "exception_type=%s",
                account_name,
                type(exc).__name__,
            )
            raise RestError(
                500,
                "An internal error occurred while testing the MISP connection. "
                "No configuration was saved.",
            ) from exc

        _LOGGER.info(
            "MISP connection validation succeeded account=%r host=%s "
            "misp_version=%s attribute_types=%s",
            account_name,
            result["url"],
            result["version"],
            result["type_count"],
        )

    def handleList(self, confInfo):
        return AdminExternalHandler.handleList(self, confInfo)

    def handleCreate(self, confInfo):
        self._validate_connection(editing=False)
        return AdminExternalHandler.handleCreate(self, confInfo)

    def handleEdit(self, confInfo):
        self._validate_connection(editing=True)
        return AdminExternalHandler.handleEdit(self, confInfo)

    def handleRemove(self, confInfo):
        return AdminExternalHandler.handleRemove(self, confInfo)
