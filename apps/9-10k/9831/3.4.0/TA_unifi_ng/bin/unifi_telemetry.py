#!/usr/bin/env python3
# Copyright 2026
# SPDX-License-Identifier: Apache-2.0
#
# UniFi Network "Telemetry" modular input (Phase B / v3.1.0).
# Per-device performance cadence (default interval 60s).
# Collects device statistics (unifi:device:stats) and full device detail
# (unifi:device:detail). One API call per device per enabled collector.
#
# Shares all collection logic with unifi_ingest.py (collect_telemetry_events).

from __future__ import annotations

import import_declare_test  # noqa: F401 — UCC sys.path fixer, must be first

import json
import logging
import sys

from unifi_ingest import (
    DEFAULT_PAGE_SIZE,
    TELEMETRY_DEFAULTS,
    UniFiApiError,
    _get_account,
    _parse_bool,
    _parse_collection_timeout,
    _parse_site_ids,
    collect_telemetry_events,
    test_unifi_connection,
)

try:
    from splunklib.modularinput import Argument, Event, Scheme, Script
except ImportError:
    Argument = Event = Scheme = Script = None  # type: ignore

LOG = logging.getLogger(__name__)


if Script is not None:

    class UniFiTelemetryScript(Script):
        """Per-device telemetry input (grouped, native interval, default 60s)."""

        def get_scheme(self):
            scheme = Scheme("UniFi Telemetry (Integration API)")
            scheme.description = (
                "Polls per-device performance statistics and full device detail "
                "(ports, radios, uplink). One API call per device per enabled "
                "collector. Default interval 60s; raise it on large fleets."
            )
            scheme.use_external_validation = True
            scheme.use_single_instance = False

            args = [
                "account", "site_ids", "page_size", "collection_timeout",
                "collect_device_stats", "collect_device_detail",
            ]
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

                collect_stats = _parse_bool(
                    input_item.get("collect_device_stats"),
                    default=TELEMETRY_DEFAULTS["collect_device_stats"],
                )
                collect_detail = _parse_bool(
                    input_item.get("collect_device_detail"),
                    default=TELEMETRY_DEFAULTS["collect_device_detail"],
                )

                try:
                    for stanza_suffix, sourcetype, _otype, payload in collect_telemetry_events(
                        host, api_key, verify_ssl, site_ids,
                        collect_stats, collect_detail,
                        page_size, collection_timeout, log=LOG,
                    ):
                        ev = Event()
                        ev.stanza = f"{input_name}:{stanza_suffix}"
                        ev.sourceType = sourcetype
                        ev.data = json.dumps(payload, ensure_ascii=False)
                        event_writer.write_event(ev)
                except UniFiApiError as e:
                    LOG.error("UniFi telemetry collection failed for %s: %s",
                              input_name, e)
                    raise


if __name__ == "__main__":
    if Script is None:
        print("splunklib not available; run inside Splunk.", file=sys.stderr)
        sys.exit(1)
    sys.exit(UniFiTelemetryScript().run(sys.argv))
