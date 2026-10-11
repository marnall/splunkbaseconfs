#!/usr/bin/env python3
# Copyright 2026
# SPDX-License-Identifier: Apache-2.0
#
# UniFi Network "Inventory" modular input (Phase A / v3.x).
# Grouped, configuration/inventory cadence (default interval 180s).
# Collects sites + the per-site and global list endpoints selected via the
# collect_* toggles. Credentials come from the encrypted account (UCC pattern).
#
# Shares all collection logic with unifi_ingest.py (collect_inventory_events).

from __future__ import annotations

import import_declare_test  # noqa: F401 — UCC sys.path fixer, must be first

import json
import logging
import sys

from unifi_ingest import (
    DEFAULT_PAGE_SIZE,
    INVENTORY_DEFAULTS,
    INVENTORY_ENDPOINTS,
    UniFiApiError,
    _get_account,
    _parse_bool,
    _parse_collection_timeout,
    _parse_site_ids,
    collect_inventory_events,
    test_unifi_connection,
)

try:
    from splunklib.modularinput import Argument, Event, Scheme, Script
except ImportError:
    Argument = Event = Scheme = Script = None  # type: ignore

LOG = logging.getLogger(__name__)


if Script is not None:

    class UniFiInventoryScript(Script):
        """Inventory/config collection input (grouped, native interval)."""

        def get_scheme(self):
            scheme = Scheme("UniFi Inventory (Integration API)")
            scheme.description = (
                "Polls UniFi Network configuration and inventory lists "
                "(devices, clients, networks, firewall, wifi, wan, vpn, "
                "switching, dns, traffic lists, radius, vouchers, device tags, "
                "pending devices, info). Default interval 180s."
            )
            scheme.use_external_validation = True
            scheme.use_single_instance = False

            args = ["account", "site_ids", "page_size", "collection_timeout"]
            args += list(INVENTORY_ENDPOINTS.keys())
            args += ["collect_network_detail"]  # Phase C enrichment toggle
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

                site_ids = _parse_site_ids(input_item.get("site_ids"))
                try:
                    page_size = int(input_item.get("page_size") or DEFAULT_PAGE_SIZE)
                except (TypeError, ValueError):
                    page_size = DEFAULT_PAGE_SIZE
                collection_timeout = _parse_collection_timeout(
                    input_item.get("collection_timeout"), default=120
                )

                # Resolve toggles: stanza value if present, else plan default.
                toggles = {}
                for toggle in list(INVENTORY_ENDPOINTS) + ["collect_network_detail"]:
                    toggles[toggle] = _parse_bool(
                        input_item.get(toggle),
                        default=INVENTORY_DEFAULTS.get(toggle, False),
                    )

                try:
                    for stanza_suffix, sourcetype, _otype, payload in collect_inventory_events(
                        host, api_key, verify_ssl, site_ids,
                        toggles, page_size, collection_timeout, log=LOG,
                    ):
                        ev = Event()
                        ev.stanza = f"{input_name}:{stanza_suffix}"
                        ev.sourceType = sourcetype
                        ev.data = json.dumps(payload, ensure_ascii=False)
                        event_writer.write_event(ev)
                except UniFiApiError as e:
                    LOG.error("UniFi inventory collection failed for %s: %s",
                              input_name, e)
                    raise


if __name__ == "__main__":
    if Script is None:
        print("splunklib not available; run inside Splunk.", file=sys.stderr)
        sys.exit(1)
    sys.exit(UniFiInventoryScript().run(sys.argv))
