"""Shared modular-input logic for veza_events and veza_audit_logs.

Splunk discovers modular inputs by script name, so each input must have its
own executable script in bin/ — but the bodies are otherwise identical. The
subclasses below set KIND, PATH, SCHEME_NAME, SCHEME_DESCRIPTION, and
DEFAULT_SOURCETYPE; everything else lives here.
"""

import json
import os
import sys
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.modularinput import (  # noqa: E402
    Argument,
    Event,
    Scheme,
    Script,
)

import veza_client  # noqa: E402


_ARGS = [
    ("tenant_url", "Veza Tenant URL",
     "Base URL of the Veza tenant, e.g. https://yourtenant.cookieai.com.", True),
    ("client_id", "OAuth2 Client ID",
     "Veza OAuth2 client_id (create under Settings → OAuth2 Clients).", True),
    ("client_secret", "OAuth2 Client Secret",
     "Veza OAuth2 client_secret matching the Client ID. Stored encrypted in "
     "Splunk's credential store on first run.", True),
    ("scope", "OAuth2 Scope",
     "Optional OAuth2 scope to request (e.g. 'viewer'). Leave blank to use "
     "the OAuth client's default configured scopes.", False),
    ("page_size", "Page Size",
     "Maximum items per page (default 1000).", False),
    ("verify_tls", "Verify TLS",
     "Verify the tenant's TLS certificate (default true; set 0 only for "
     "self-signed dev tenants).", False),
]


class VezaInputBase(Script):
    KIND = None
    PATH = None
    SCHEME_NAME = None
    SCHEME_DESCRIPTION = None
    DEFAULT_SOURCETYPE = None

    def get_scheme(self):
        scheme = Scheme(self.SCHEME_NAME)
        scheme.description = self.SCHEME_DESCRIPTION
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        for name, title, description, required in _ARGS:
            a = Argument(name)
            a.title = title
            a.description = description
            a.required_on_create = required
            scheme.add_argument(a)
        return scheme

    def validate_input(self, validation_definition):
        # Only validate *format* of present fields. Required-on-create is
        # enforced by the Scheme (`required_on_create=True`), so we don't
        # need (or want) presence checks here — partial updates from
        # _rewrite_input_secret carry only the changed field and would
        # otherwise fail validation.
        params = validation_definition.parameters
        url = (params.get("tenant_url") or "").strip()
        if url and not url.startswith("https://"):
            raise ValueError("tenant_url must be an https:// URL")
        page_size = params.get("page_size")
        if page_size and not str(page_size).isdigit():
            raise ValueError("page_size must be a positive integer")

    def stream_events(self, inputs, ew):
        # splunklib 2.x: inputs.metadata holds checkpoint_dir / session_key;
        # each inputs.inputs[name] is a plain dict of stanza params.
        checkpoint_dir = inputs.metadata["checkpoint_dir"]
        for input_name, item in inputs.inputs.items():
            try:
                self._run_one(input_name, item, checkpoint_dir, ew)
            except veza_client.VezaCheckpointExpired as exc:
                # Operator-actionable: cursor aged past the server retention
                # window. See the README "Operations" section for recovery.
                ew.log(
                    ew.ERROR,
                    "veza-ta checkpoint-expired input={0}: {1} -- "
                    "delete the cursor file and restart the input to resume".format(
                        input_name, exc
                    ),
                )
            except (veza_client.VezaAuthError, veza_client.VezaOAuthError) as exc:
                ew.log(ew.ERROR, "veza-ta auth-error input={0}: {1}".format(input_name, exc))
            except Exception as exc:  # noqa: BLE001
                ew.log(ew.ERROR, "veza-ta unexpected-error input={0}: {1}".format(input_name, exc))

    def _run_one(self, input_name, item, checkpoint_dir, ew):
        tenant_url = item["tenant_url"].rstrip("/")
        page_size = int(item.get("page_size") or veza_client.DEFAULT_PAGE_SIZE)
        verify_tls = str(item.get("verify_tls", "1")).lower() not in ("0", "false")

        client_secret = veza_client.resolve_client_secret(
            self.service, input_name, item["client_secret"]
        )
        scope = (item.get("scope") or "").strip() or None

        token_manager = veza_client.OAuthTokenManager(
            tenant_url=tenant_url,
            client_id=item["client_id"],
            client_secret=client_secret,
            scope=scope,
            verify_tls=verify_tls,
        )
        transport = veza_client.VezaTransport(
            tenant_url, token_manager, verify_tls=verify_tls
        )
        checkpoint = veza_client.Checkpoint(checkpoint_dir, self.KIND, input_name)

        host = urlparse(tenant_url).hostname or tenant_url
        source = tenant_url + self.PATH
        sourcetype = item.get("sourcetype") or self.DEFAULT_SOURCETYPE
        index = item.get("index") or "main"

        def sink(payload):
            evt = Event()
            evt.stanza = input_name
            evt.host = host
            evt.source = source
            evt.sourcetype = sourcetype
            evt.index = index
            evt.data = json.dumps(payload, separators=(",", ":"))
            ew.write_event(evt)

        count = veza_client.drain(transport, self.PATH, checkpoint, page_size, sink)
        ew.log(ew.INFO, "veza-ta drained input={0} count={1}".format(input_name, count))
