"""Test-connection hook for Jamf Pro accounts.

Subclasses splunktaucclib's AdminExternalHandler and runs an OAuth probe
against the configured Jamf Pro URL on account create/edit. If the probe
fails the save is rejected with a user-friendly error message.
"""

import import_declare_test  # noqa: F401  pylint: disable=unused-import

import requests

from splunktaucclib.rest_handler.admin_external import (
    AdminExternalHandler as _BaseAdminExternalHandler,
)
from splunktaucclib.rest_handler.error import RestError


_PROBE_TIMEOUT = 10
_MASKED_PLACEHOLDER = "******"


def _probe_jamf(jss_url, auth_type, username, password):
    """Probe Jamf Pro credentials by hitting the token endpoint.

    Raises ValueError with a user-facing message if the probe fails.
    """
    if not jss_url:
        raise ValueError("Jamf Pro URL is required.")
    if not username or not password:
        raise ValueError("Username and password are required.")

    base = jss_url.rstrip("/")

    if auth_type == "api_client":
        token_url = "{}/api/v1/oauth/token".format(base)
        try:
            resp = requests.post(
                token_url,
                data={
                    "client_id": username,
                    "client_secret": password,
                    "grant_type": "client_credentials",
                },
                timeout=_PROBE_TIMEOUT,
            )
        except requests.exceptions.RequestException as exc:
            raise ValueError(
                "Could not reach {url}: {err}".format(url=token_url, err=exc)
            ) from exc
        if resp.status_code == 200:
            return
        if resp.status_code in (400, 401):
            raise ValueError(
                "Invalid Client ID or Client Secret (HTTP {})".format(resp.status_code)
            )
        raise ValueError(
            "Auth failed (HTTP {}): {}".format(resp.status_code, resp.text[:200])
        )

    # basic-auth fallback
    token_url = "{}/api/v1/auth/token".format(base)
    try:
        resp = requests.post(
            token_url,
            auth=(username, password),
            timeout=_PROBE_TIMEOUT,
        )
    except requests.exceptions.RequestException as exc:
        raise ValueError(
            "Could not reach {url}: {err}".format(url=token_url, err=exc)
        ) from exc
    if resp.status_code == 200:
        return
    if resp.status_code == 401:
        raise ValueError("Invalid username or password (HTTP 401)")
    raise ValueError(
        "Auth failed (HTTP {}): {}".format(resp.status_code, resp.text[:200])
    )


class AdminExternalHandler(_BaseAdminExternalHandler):
    """Account REST handler that validates credentials against Jamf Pro on save.

    Named ``AdminExternalHandler`` to satisfy ucc-gen's hardcoded import in the
    generated REST handler stub.
    """

    def handleCreate(self, confInfo):
        self._maybe_validate(self.payload)
        return super().handleCreate(confInfo)

    def handleEdit(self, confInfo):
        # Skip when this edit is just toggling enabled/disabled.
        if self.payload.get("disabled") is not None and len(self.payload) == 1:
            return super().handleEdit(confInfo)
        self._maybe_validate(self.payload)
        return super().handleEdit(confInfo)

    def _maybe_validate(self, payload):
        password = payload.get("password", "")
        # On edit, an unchanged password comes through as the masked placeholder.
        # Skip the probe in that case rather than failing on a fake password.
        if password == _MASKED_PLACEHOLDER:
            return
        username = payload.get("username", "") or ""
        auth_type = payload.get("auth_type") or ""
        # Legacy account compat: if no auth_type is set, infer from a client: prefix.
        if not auth_type:
            auth_type = "api_client" if username.startswith("client:") else "password"
        # Strip the legacy client: prefix if present so the OAuth probe receives a clean Client ID.
        if username.startswith("client:"):
            username = username[len("client:"):]
        try:
            _probe_jamf(
                payload.get("jss_url"),
                auth_type,
                username,
                password,
            )
        except ValueError as exc:
            raise RestError(400, str(exc)) from exc
