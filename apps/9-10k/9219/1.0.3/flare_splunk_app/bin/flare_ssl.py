import ssl

from requests.adapters import HTTPAdapter
from typing import Any


def build_unverified_ssl_context() -> ssl.SSLContext:
    """Build an SSLContext with verification disabled that loads no CA store."""
    # ssl.create_default_context() would itself call load_default_certs(), so the
    # context is constructed directly.
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    # check_hostname must be cleared before verify_mode, otherwise stdlib raises.
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    return context


class UnverifiedHTTPAdapter(HTTPAdapter):
    """HTTPAdapter that injects an explicit unverified SSLContext."""

    def init_poolmanager(self, *args: Any, **kwargs: Any) -> Any:
        kwargs["ssl_context"] = build_unverified_ssl_context()
        return super().init_poolmanager(  # type: ignore[no-untyped-call, unused-ignore]
            *args, **kwargs
        )

    def proxy_manager_for(self, *args: Any, **kwargs: Any) -> Any:
        kwargs["ssl_context"] = build_unverified_ssl_context()
        return super().proxy_manager_for(  # type: ignore[no-untyped-call, unused-ignore]
            *args, **kwargs
        )
