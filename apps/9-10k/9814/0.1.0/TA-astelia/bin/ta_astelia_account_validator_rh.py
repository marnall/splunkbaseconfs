import import_declare_test  # noqa: F401
from splunktaucclib.rest_handler.admin_external import AdminExternalHandler
from splunktaucclib.rest_handler.error import RestError

from astelia_api import AsteliaApiError, AsteliaAuthError, AsteliaClient
from astelia_common import get_account, get_logger, get_proxies

MASKED_SECRET = "******"
HTTP_BAD_REQUEST = 400


class AsteliaAccountValidator(AdminExternalHandler):
    def __init__(self, *args, **kwargs) -> None:
        AdminExternalHandler.__init__(self, *args, **kwargs)

    def handleList(self, confInfo) -> None:  # noqa: N802, N803, ANN001
        AdminExternalHandler.handleList(self, confInfo)

    def handleEdit(self, confInfo) -> None:  # noqa: N802, N803, ANN001
        self._verify_account()
        AdminExternalHandler.handleEdit(self, confInfo)

    def handleCreate(self, confInfo) -> None:  # noqa: N802, N803, ANN001
        self._verify_account()
        AdminExternalHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo) -> None:  # noqa: N802, N803, ANN001
        AdminExternalHandler.handleRemove(self, confInfo)

    def _verify_account(self) -> None:
        base_url = self.payload.get("base_url") or ""
        api_key = self._resolve_api_key()
        if not api_key:
            raise RestError(HTTP_BAD_REQUEST, "Enter an Astelia API key.")
        session_key = self.getSessionKey()
        logger = get_logger("account_validation", session_key)
        try:
            proxies = get_proxies(session_key, logger)
        except Exception as exc:
            logger.warning("proxy_settings_unavailable", extra={"error": str(exc)})
            proxies = None
        try:
            AsteliaClient(base_url, api_key, proxies=proxies).ping()
        except ValueError as exc:
            raise RestError(HTTP_BAD_REQUEST, str(exc)) from exc
        except AsteliaAuthError as exc:
            raise RestError(
                HTTP_BAD_REQUEST,
                f"Astelia rejected this API key ({exc.code}). Create a key with Read permission in "
                "Settings > API Keys and check the API URL belongs to the same organization.",
            ) from exc
        except AsteliaApiError as exc:
            raise RestError(
                HTTP_BAD_REQUEST,
                f"Could not verify the key against {base_url}: {exc}. "
                "Check the URL, network access and proxy settings.",
            ) from exc

    def _resolve_api_key(self) -> str:
        api_key = self.payload.get("api_key") or ""
        if api_key != MASKED_SECRET:
            return api_key
        stored = get_account(self.getSessionKey(), self.callerArgs.id)
        return stored.get("api_key") or ""
