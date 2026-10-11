#!/usr/bin/env python3
# Copyright 2026
# SPDX-License-Identifier: Apache-2.0
#
# UniFi Network "Reference" modular input (Phase D / v3.2.0).
# Large near-static reference data (default interval 86400s = daily).
# Collects countries, DPI applications, DPI categories. Controller-wide.
#
# Shares all collection logic with unifi_ingest.py (collect_reference_events).

from __future__ import annotations

import import_declare_test  # noqa: F401 — UCC sys.path fixer, must be first

import json
import logging
import sys

from unifi_ingest import (
    DEFAULT_PAGE_SIZE,
    REFERENCE_DEFAULTS,
    REFERENCE_ENDPOINTS,
    UniFiApiError,
    _get_account,
    _parse_bool,
    _parse_collection_timeout,
    collect_reference_events,
    test_unifi_connection,
)

try:
    from splunklib.modularinput import Argument, Event, Scheme, Script
except ImportError:
    Argument = Event = Scheme = Script = None  # type: ignore

LOG = logging.getLogger(__name__)


if Script is not None:

    class UniFiReferenceScript(Script):
        """Reference-data input (grouped, native interval, default 86400s)."""

        def get_scheme(self):
            scheme = Scheme("UniFi Reference (Integration API)")
            scheme.description = (
                "Polls large near-static reference data: countries, DPI "
                "applications, DPI categories. Controller-wide. Default "
                "interval 86400s (daily)."
            )
            scheme.use_external_validation = True
            scheme.use_single_instance = False

            args = ["account", "page_size", "collection_timeout"]
            args += list(REFERENCE_ENDPOINTS.keys())
            for name in args:
                arg = Argument(name)
                arg.required_on_create = (name == "account")
                arg.required_on_edit = (name == "account")
                scheme.add_argument(arg)
            return scheme

        def validate_input(self, validation_definition):
            params = validation_definition.parameters
            session_key = validation_definition.metadata.get("session_key")
            account_name = params.get("account", "")
            try:
                account = _get_account(session_key, account_name)
            except Exception as e:
                raise ValueError(f"Cannot load account '{account_name}': {e}") from e
            host = account.get("controller_url", "")
            api_key = account.get("api_key", "")
            verify_ssl = _parse_bool(account.get("verify_ssl"), default=False)
            test_unifi_connection(host, api_key, verify_ssl=verify_ssl)

        def stream_events(self, inputs, event_writer):
            for input_name, input_item in inputs.inputs.items():
                session_key = inputs.metadata["session_key"]
                account_name = input_item.get("account", "")
                try:
                    account = _get_account(session_key, account_name)
                except Exception as e:
                    LOG.error("Cannot load account '%s' for %s: %s",
                              account_name, input_name, e)
                    raise

                host = account.get("controller_url", "")
                api_key = account.get("api_key", "")
                verify_ssl = _parse_bool(account.get("verify_ssl"), default=False)

                try:
                    page_size = int(input_item.get("page_size") or DEFAULT_PAGE_SIZE)
                except (TypeError, ValueError):
                    page_size = DEFAULT_PAGE_SIZE
                collection_timeout = _parse_collection_timeout(
                    input_item.get("collection_timeout"), default=120
                )

                toggles = {}
                for toggle in REFERENCE_ENDPOINTS:
                    toggles[toggle] = _parse_bool(
                        input_item.get(toggle),
                        default=REFERENCE_DEFAULTS.get(toggle, False),
                    )

                try:
                    for stanza_suffix, sourcetype, _otype, payload in collect_reference_events(
                        host, api_key, verify_ssl,
                        toggles, page_size, collection_timeout, log=LOG,
                    ):
                        ev = Event()
                        ev.stanza = f"{input_name}:{stanza_suffix}"
                        ev.sourceType = sourcetype
                        ev.data = json.dumps(payload, ensure_ascii=False)
                        event_writer.write_event(ev)
                except UniFiApiError as e:
                    LOG.error("UniFi reference collection failed for %s: %s",
                              input_name, e)
                    raise


if __name__ == "__main__":
    if Script is None:
        print("splunklib not available; run inside Splunk.", file=sys.stderr)
        sys.exit(1)
    sys.exit(UniFiReferenceScript().run(sys.argv))
