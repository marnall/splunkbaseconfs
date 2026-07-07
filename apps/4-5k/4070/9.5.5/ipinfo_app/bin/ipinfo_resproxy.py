from __future__ import annotations

import os
import sys
import traceback
from typing import Dict, Generator, List, Optional, OrderedDict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _ipinfo_bootstrap  # noqa: F401  -- pin vendored splunklib before any other import to defeat Splunk Enterprise Security sys.path collisions

from ipinfo.logging import get_logger
from ipinfo.utils import calculate_prefix, increment_mmdb_usage, prefix_dict_keys
from ipinfo.validators import ListOrBoolean
from ipinfo_constants import RESPROXY_LOOKBACK_DAYS
from ipinfo_MMDB import open_mmdb, parse_mmdb_result, read_mmdb
from ipinfo_RestAPI import get_ipinfo_rest_result
from ipinfo_utils import (
    get_config,
)
from splunklib.searchcommands import (
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
    validators,
)


logger = get_logger("ipinfo_resproxy")
replication = get_config("replicate_lookup") == "Yes"

TEMPLATE_RECORD = {
    "ip": "",
    "last_seen": "",
    "percent_days_seen": "",
    "service": "",
}


@Configuration(distributed=replication)
class IPinfoResproxyCommand(StreamingCommand):
    prefix = Option(require=False, default=False, validate=ListOrBoolean())
    restapi = Option(require=False, default=False, validate=validators.Boolean())
    lookback = Option(require=False, default="30", validate=validators.Set(*RESPROXY_LOOKBACK_DAYS))

    def stream(self, records: Generator[OrderedDict[str, str], None, None]):
        fields: List[str] = self.fieldnames or []
        prefix = self.prefix
        restapi = self.restapi
        lookback = self.lookback

        method = get_config("method")
        if restapi:
            method = "RESTAPI"

        prefix = calculate_prefix(prefix, fields)

        try:
            if method == "MMDB":
                yield from self._stream_mmdb(records, fields, prefix, lookback)
            elif method == "RESTAPI":
                yield from self._stream_restapi(records, fields, prefix)
        except Exception as e:
            logger.error(e)
            logger.error("\nTraceback:\n" + "".join(traceback.format_exc()))

    def _fill_record_with_empty_values(
        self,
        record: OrderedDict[str, str],
        fields: List[str],
        prefix: Optional[Dict[str, str]],
    ):
        for field in fields:
            empty_fields = TEMPLATE_RECORD.copy()
            if prefix:
                empty_fields = prefix_dict_keys(empty_fields, prefix[field])
            record.update(empty_fields)

    def _stream_mmdb(
        self,
        records: Generator[OrderedDict[str, str], None, None],
        fields: List[str],
        prefix: Optional[Dict[str, str]],
        lookback: str,
    ) -> Generator[OrderedDict[str, str], None, None]:
        lookupfile = f"resproxy_{lookback}d"
        reader = open_mmdb(self, lookupfile)
        total_ips = 0
        count = 0
        ip_addresses = []
        for record in records:
            new_ip_found = False
            for field in fields:
                if field not in record:
                    continue
                ip_value = record.get(field, "").strip()
                if ip_value == "":
                    continue
                new_ip_found = True
                ip_addresses.append(ip_value)
                count += 1

            if not new_ip_found:
                self._fill_record_with_empty_values(record, fields, prefix)
                yield record
                continue

            total_ips += len(ip_addresses)
            results = read_mmdb(self, "resproxy", reader, ip_addresses)
            details = {}
            parse_mmdb_result(details, results)
            # We got the IPs details, we can reset the list for the next iteration
            ip_addresses = []

            if not details:
                self.write_warning("Some Error Occured. Check Logs dashboard for troubleshooting.")
                self._fill_record_with_empty_values(record, fields, prefix)
                yield record
                continue

            for field in fields:
                if field not in record:
                    continue
                detail = details.get(record.get(field))
                if detail is not None:
                    if prefix:
                        detail = prefix_dict_keys(detail, prefix[field])
                    record.update(detail)

            yield record

        # We keep track of MMDBs usage, this increments the usage of the residential proxy MMDB
        increment_mmdb_usage(self.service, lookupfile, total_ips)

    def _stream_restapi(
        self,
        records: Generator[OrderedDict[str, str], None, None],
        fields: List[str],
        prefix: Optional[Dict[str, str]],
    ) -> Generator[OrderedDict[str, str], None, None]:
        count = 0
        ip_addresses = []
        record_foo: Dict[str, OrderedDict[str, str]] = {}
        for record in records:
            new_ip_found = False
            for field in fields:
                if field not in record:
                    continue
                ip_value = record.get(field, "").strip()
                if ip_value == "":
                    continue
                new_ip_found = True
                ip_addresses.append(ip_value)
                count += 1

            if new_ip_found:
                record_foo[str(count)] = record
            else:
                self._fill_record_with_empty_values(record, fields, prefix)
                yield record
            if count >= 1000:
                count = 0
                yield from get_ipinfo_rest_result(
                    self,
                    ip_addresses,
                    record_foo,
                    fields,
                    False,
                    False,
                    False,
                    False,
                    False,
                    False,
                    True,
                    prefix,
                )
                ip_addresses = []
                record_foo = {}
        if count < 1000:
            yield from get_ipinfo_rest_result(
                self,
                ip_addresses,
                record_foo,
                fields,
                False,
                False,
                False,
                False,
                False,
                False,
                True,
                prefix,
            )


dispatch(IPinfoResproxyCommand, sys.argv, sys.stdin, sys.stdout, __name__)
