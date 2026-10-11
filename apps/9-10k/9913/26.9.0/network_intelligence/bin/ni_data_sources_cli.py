"""CLI for inspecting and mutating Network Intelligence data source configuration.

Run via the Splunk-bundled interpreter, e.g.:
  $SPLUNK_HOME/bin/splunk cmd python3 ni_data_sources_cli.py --list
  $SPLUNK_HOME/bin/splunk cmd python3 ni_data_sources_cli.py \
      --source meraki --indexes meraki --interval 300 --enable
  $SPLUNK_HOME/bin/splunk cmd python3 ni_data_sources_cli.py --reconcile

Requires a session token with rights to write network_intelligence conf and
read Splunk's indexes endpoint: pass --session-key, or set SPLUNK_SESSION_KEY.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

import import_declare_test  # noqa: E402,F401
from config.models import KNOWN_SOURCE_SYSTEMS, DataSource  # noqa: E402
from config.orchestrator import DataSourceNotFoundError  # noqa: E402
from config.service import UNSET, DataSourceService  # noqa: E402
from config.transaction import TransactionRollbackError  # noqa: E402
from splunk.clilib.bundle_paths import make_splunkhome_path  # noqa: E402


def _session_key(args: argparse.Namespace) -> str:
    key = args.session_key or os.environ.get("SPLUNK_SESSION_KEY")
    if not key:
        raise SystemExit("A session token is required: pass --session-key or set SPLUNK_SESSION_KEY.")
    return key


def _source_dict(source: DataSource) -> dict:
    return {
        "source_system": source.source_system,
        "indexes": list(source.indexes),
        "collection_interval_s": source.collection_interval_s,
        "enabled": source.enabled,
    }


def _cmd_list(service: DataSourceService, session_key: str) -> None:
    listing = service.list_sources(session_key)
    print(json.dumps({"default_collection_interval_s": listing.default_collection_interval_s}, indent=2))
    for source_system in KNOWN_SOURCE_SYSTEMS:
        print(json.dumps(_source_dict(listing.data_sources[source_system]), indent=2))


def _cmd_update(service: DataSourceService, session_key: str, args: argparse.Namespace) -> None:
    indexes = args.indexes.split(",") if args.indexes is not None else UNSET
    interval = args.interval if args.interval is not None else UNSET
    enabled = UNSET
    if args.enable:
        enabled = True
    elif args.disable:
        enabled = False
    result = service.update_source(
        args.source,
        session_key,
        indexes=indexes,
        collection_interval_s=interval,
        enabled=enabled,
    )
    print("changed" if result.changed else "unchanged")
    print(json.dumps(_source_dict(result.source), indent=2))


def _cmd_reconcile(service: DataSourceService, session_key: str) -> None:
    """Unconditionally re-derive ni_indexes and dependent state from current conf.

    Leaves every source's own indexes/interval/disabled untouched — the recovery
    path after local/data_sources.conf (or a dependent conf) was hand-edited.
    Delegates to DataSourceService.reconcile(), the same entry point the REST
    settings/collection route uses after changing the global default.
    """
    service.reconcile(session_key)
    print("reconciled")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--session-key", help="Splunk session token; defaults to SPLUNK_SESSION_KEY.")
    parser.add_argument("--list", action="store_true", help="List all data sources.")
    parser.add_argument("--reconcile", action="store_true", help="Re-derive dependent state from current conf.")
    parser.add_argument("--source", choices=KNOWN_SOURCE_SYSTEMS, help="Data source to update.")
    parser.add_argument("--indexes", help="Comma-separated index list.")
    parser.add_argument(
        "--interval", type=int, help="Collection interval in seconds (one of 60/300/900/1800/3600)."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--enable", action="store_true")
    group.add_argument("--disable", action="store_true")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    app_dir = make_splunkhome_path(["etc", "apps", "network_intelligence"])
    service = DataSourceService(app_dir)
    session_key = _session_key(args)

    try:
        if args.list:
            _cmd_list(service, session_key)
        elif args.reconcile:
            _cmd_reconcile(service, session_key)
        elif args.source:
            _cmd_update(service, session_key, args)
        else:
            _build_parser().print_help()
            return 1
    except (DataSourceNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    except TransactionRollbackError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
