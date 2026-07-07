import import_declare_test
import ssl

from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from solnlib import log
from account_validation import validate_account_credentials

logger = log.Logs().get_logger("appdynamics_account_validation")


def _validate_credentials(controller_url, client_name, client_secret, session_key):
    import logging
    version_string = ""
    try:
        import requests as _r
        import urllib3 as _u
        version_string = f"requests: {_r.__version__}; urllib3: {_u.__version__}"
    except Exception:
        pass
    if logger.isEnabledFor(logging.DEBUG):
        from ucc_utils import Util
        verify_ssl = Util.get_verify_ssl(session_key)
        logger.debug(
            "SSL Debug: openssl version: '%s' verify paths: '%s' %s TA verify ssl setting: '%s' controller: '%s'",
            ssl.OPENSSL_VERSION, ssl.get_default_verify_paths(), version_string, verify_ssl, controller_url,
        )
    validate_account_credentials(controller_url, client_name, client_secret, session_key, logger=logger)


class CustomRestHandler(AdminExternalHandler):

    def handleEdit(self, confInfo):
        _validate_credentials(
            self.payload.get("appd_controller_url"),
            self.payload.get("appd_client_name"),
            self.payload.get("appd_client_secret"),
            self.getSessionKey()
        )
        super().handleEdit(confInfo)

    def handleCreate(self, confInfo):
        _validate_credentials(
            self.payload.get("appd_controller_url"),
            self.payload.get("appd_client_name"),
            self.payload.get("appd_client_secret"),
            self.getSessionKey()
        )
        super().handleCreate(confInfo)
