#!/usr/bin/env python3
import import_declare_test  # noqa: F401  (UCC path shim: puts lib/ on sys.path)

import json
import sys
from urllib import error, request

from solnlib import conf_manager
from splunklib.searchcommands import Configuration, Option, StreamingCommand, dispatch, validators

API_BASE = "https://api.macadress.com"
BATCH_SIZE = 100
REQUEST_TIMEOUT = 15

APP_NAME = "TA-macadress"
SETTINGS_CONF = "ta_macadress_settings"
SETTINGS_STANZA = "settings"

OUTPUT_FIELDS = (
    "mac_valid",
    "mac_registered",
    "mac_oui",
    "mac_matched_prefix",
    "mac_organization",
    "mac_vendor_slug",
    "mac_country",
    "mac_block_type",
    "mac_locally_administered",
    "mac_administration_type",
    "mac_transmission_type",
    "mac_potentially_randomized",
    "mac_randomization_confidence",
    "mac_device_category",
    "mac_device_confidence",
    "mac_virtualization_platform",
    "mac_special_use_type",
    "mac_explanation",
    "mac_lookup_error",
)


@Configuration()
class MacAddressLookupCommand(StreamingCommand):
    """Enriches events with vendor, device, and special-use data for a MAC address field.

    ##Syntax

    macaddresslookup field=<fieldname>

    ##Example

    ... | macaddresslookup field=src_mac
    """

    field = Option(
        doc="Name of the field holding the MAC address to look up.",
        require=True,
        validate=validators.Fieldname(),
    )

    def _api_key(self):
        session_key = self.metadata.searchinfo.session_key
        api_key = None
        try:
            cfm = conf_manager.ConfManager(
                session_key,
                APP_NAME,
                realm="__REST_CREDENTIAL__#%s#configs/conf-%s" % (APP_NAME, SETTINGS_CONF),
            )
            settings = cfm.get_conf(SETTINGS_CONF).get(SETTINGS_STANZA)
            api_key = (settings or {}).get("api_key")
        except Exception:
            api_key = None

        if not api_key:
            self.error_exit(
                "No macadress.com API key configured.",
                "Open Apps > macadress.com MAC Address Lookup > Configuration and set the API key. "
                "Free keys are available at https://macadress.com/signup.",
            )
        return api_key

    def _lookup(self, macs, api_key):
        payload = json.dumps({"macs": macs}).encode("utf-8")
        req = request.Request(
            API_BASE + "/v1/mac/batch",
            data=payload,
            method="POST",
            headers={
                "Authorization": "Bearer " + api_key,
                "Content-Type": "application/json",
                "User-Agent": "TA-macadress/1.0.0 (+https://macadress.com/mcp)",
            },
        )
        try:
            with request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            self.error_exit(
                "macadress.com API returned HTTP %d." % exc.code,
                detail,
            )
        except error.URLError as exc:
            self.error_exit("Could not reach macadress.com API.", str(exc.reason))
        return body.get("results", [])

    @staticmethod
    def _get(dct, *path):
        cur = dct
        for key in path:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(key)
        return cur

    def _apply(self, record, item):
        if item is None:
            record["mac_lookup_error"] = "no response for this address"
            return

        if item.get("error"):
            record["mac_lookup_error"] = item["error"]

        record["mac_valid"] = item.get("valid")
        record["mac_registered"] = item.get("registered")
        record["mac_oui"] = item.get("oui")
        record["mac_matched_prefix"] = item.get("matched_prefix")
        record["mac_organization"] = item.get("organization")
        record["mac_country"] = item.get("country")
        record["mac_block_type"] = item.get("block_type")
        record["mac_locally_administered"] = item.get("locally_administered")
        record["mac_administration_type"] = item.get("administration_type")
        record["mac_transmission_type"] = item.get("transmission_type")
        record["mac_potentially_randomized"] = item.get("potentially_randomized")
        record["mac_randomization_confidence"] = item.get("randomization_confidence")
        record["mac_explanation"] = item.get("explanation")
        record["mac_vendor_slug"] = self._get(item, "vendor", "slug")
        record["mac_device_category"] = self._get(item, "device", "category")
        record["mac_device_confidence"] = self._get(item, "device", "confidence")
        record["mac_virtualization_platform"] = self._get(item, "virtualization", "platform")
        record["mac_special_use_type"] = self._get(item, "special_use", "type")

    def _resolve_batch(self, pending, api_key):
        macs = [mac for _, mac in pending]
        results = self._lookup(macs, api_key)
        for i, (record, _mac) in enumerate(pending):
            item = results[i] if i < len(results) else None
            self._apply(record, item)
        return [record for record, _mac in pending]

    def stream(self, records):
        api_key = self._api_key()
        pending = []

        for record in records:
            mac = record.get(self.field)
            if not mac:
                for out_field in OUTPUT_FIELDS:
                    record.setdefault(out_field, None)
                yield record
                continue

            pending.append((record, mac))
            if len(pending) >= BATCH_SIZE:
                for done_record in self._resolve_batch(pending, api_key):
                    yield done_record
                pending = []

        if pending:
            for done_record in self._resolve_batch(pending, api_key):
                yield done_record


dispatch(MacAddressLookupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
