"""Alert action / ES 7 adaptive response: Kyberis enrichment.

Splunk invokes this script with --execute and a JSON payload on stdin
(session key, action configuration, path to the gzipped CSV of triggering
result rows). Indicator values are read from the configured result fields,
enriched through the shared Enricher core (batched Kyberis API calls, KV
Store cache — alert-triggered enrichments warm the same cache searches
read), and one kyberis:threat_activity event is indexed per indicator.

Indexed events carry the kyberis_* verdict fields, the CIM threat_* fields
for qualifying verdicts (kyberis_splunk.cim — the eventtype/tag in this app
puts those into the ES Threat Intelligence data model), and orig_sid /
orig_rid pointing back at the triggering search so ES incident review can
correlate the response with its notable.

stderr lands in splunkd.log (component sendmodalert); a non-zero exit marks
the action failed in the alert manager. A mid-run plan limit (402) is not a
failure: already-enriched indicators are indexed, the rest are indexed with
kyberis_status=plan_limit, and a warning is logged.
"""

import csv
import gzip
import json
import logging
import os
import sys
from urllib.parse import urlsplit

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BIN_DIR, "lib"))
sys.path.insert(0, BIN_DIR)

import splunklib.client as splunk_client

from kyberis_splunk import logscrub
from kyberis_splunk.cache import IocCache
from kyberis_splunk.cim import threat_fields
from kyberis_splunk.enrich import (
    Enricher,
    EnrichmentAuthError,
    EnrichmentPrivacyError,
    EnrichmentQuotaError,
)
from kyberis_splunk.settings import APP_NAME, KyberisSettingsError, build_client

SOURCETYPE = "kyberis:threat_activity"
SOURCE = "kyberis_enrichment"

# Static by design, like the search command's default — never built from the
# alert's search text (privacy commitment).
ACTION_OBJECTIVE = "Enrich Splunk alert results with Kyberis threat verdicts for indicator fields"

# Kept in sync with the param defaults in default/alert_actions.conf.
DEFAULT_FIELDS = "src,dest,src_ip,dest_ip,domain,url,file_hash"
DEFAULT_INDEX = "main"
DEFAULT_MAX_INDICATORS = 100

logging.basicConfig(stream=sys.stderr, level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(SOURCE)


def main(argv) -> int:
    # Before anything can log: redact credential material from splunkd.log
    # output (secrets are registered when the profile resolves).
    logscrub.install()

    if "--execute" not in argv[1:]:
        logger.error("unsupported invocation; expected --execute with a JSON payload on stdin")
        return 2
    try:
        payload = json.load(sys.stdin)
    except ValueError as error:
        logger.error("could not parse the alert payload: %s", error)
        return 2
    # The splunkd session key is a credential too — splunklib sends it on
    # every management call and could surface it in DEBUG/error output.
    logscrub.register_secret(payload.get("session_key"))

    configuration = payload.get("configuration") if isinstance(payload.get("configuration"), dict) else {}
    sid = str(payload.get("sid") or "")
    search_name = str(payload.get("search_name") or "")

    try:
        service = _connect(payload)
    except Exception as error:
        logger.error("could not connect back to splunkd: %s", error)
        return 2

    try:
        client, resolved = build_client(service, str(configuration.get("profile") or "").strip() or None)
    except KyberisSettingsError as error:
        logger.error("%s", error)
        return 3
    logging.getLogger().setLevel(resolved.log_level)

    index_name = str(configuration.get("index") or "").strip() or DEFAULT_INDEX
    try:
        index = service.indexes[index_name]
    except KeyError:
        logger.error(
            'destination index "%s" does not exist; set a valid index in the '
            "Kyberis enrichment action configuration",
            index_name,
        )
        return 3

    pairs = _indicator_pairs(payload, configuration)
    if not pairs:
        logger.info("no indicator values found in the alert results; nothing to enrich")
        return 0

    limit = _as_int(configuration.get("max_indicators"), DEFAULT_MAX_INDICATORS, 0, 100000)
    if limit and len(pairs) > limit:
        logger.warning(
            "enriching the first %d of %d unique indicators (max_indicators cap)",
            limit,
            len(pairs),
        )
        pairs = dict(list(pairs.items())[:limit])

    # The KV Store cache is built only after credential resolution:
    # service.kvstore permanently switches the service namespace owner.
    cache = IocCache(
        service, resolved.cache_ttl_seconds, logger=logger, base_url=resolved.config.base_url
    )
    if not cache.active:
        cache = None

    enricher = Enricher(
        client,
        resolved.auth_header,
        run_id=sid,
        objective=ACTION_OBJECTIVE,
        cache=cache,
        # The payload carries no raw SPL on tested versions; passed
        # defensively in case a Splunk version adds it.
        never_send=(str(payload.get("search") or ""),),
    )
    try:
        enricher.enrich(list(pairs))
    except (EnrichmentAuthError, EnrichmentPrivacyError) as error:
        logger.error("%s", error)
        return 4
    except EnrichmentQuotaError as error:
        logger.warning("%s", error)
    if enricher.transport_error_message:
        logger.warning(
            "%s Affected events are indexed with kyberis_status=transport_error.",
            enricher.transport_error_message,
        )

    submitted = 0
    for value, (field_name, rid) in pairs.items():
        fields = dict(enricher.result_for(value))
        event = {
            "indicator": value,
            "indicator_field": field_name,
            "orig_sid": sid,
            "orig_rid": rid,
            "search_name": search_name,
        }
        event.update(fields)
        event.update(threat_fields(field_name, value, fields, resolved.cim_min_threat))
        try:
            index.submit(json.dumps(event), sourcetype=SOURCETYPE, source=SOURCE)
        except Exception as error:
            logger.error(
                'indexing to "%s" failed after %d of %d events: %s',
                index_name,
                submitted,
                len(pairs),
                error,
            )
            return 5
        submitted += 1

    if cache is not None:
        cache.purge_expired()
        logger.info(
            "kyberis cache: %d hit(s), %d miss(es), %d write(s)", cache.hits, cache.misses, cache.writes
        )
    logger.info(
        'indexed %d kyberis:threat_activity event(s) to "%s" for alert "%s"',
        submitted,
        index_name,
        search_name,
    )
    return 0


def _connect(payload):
    """splunklib Service on this instance, authed with the action's session key."""
    server_uri = urlsplit(str(payload.get("server_uri") or "https://127.0.0.1:8089"))
    return splunk_client.connect(
        token=payload["session_key"],
        scheme=server_uri.scheme or "https",
        host=server_uri.hostname or "127.0.0.1",
        port=server_uri.port or 8089,
        app=APP_NAME,
        owner="nobody",
    )


def _indicator_pairs(payload, configuration) -> dict:
    """Ordered {indicator value: (source field, result row index)} across all
    triggering result rows; a value seen in several fields/rows keeps the
    first occurrence (its row index becomes the event's orig_rid)."""
    field_names = [
        name.strip()
        for name in str(configuration.get("fields") or DEFAULT_FIELDS).split(",")
        if name.strip()
    ]
    pairs = {}
    for rid, row in enumerate(_result_rows(str(payload.get("results_file") or ""))):
        for name in field_names:
            for value in _field_values(row, name):
                value = str(value).strip() if value is not None else ""
                if value and value not in pairs:
                    pairs[value] = (name, rid)
    return pairs


def _result_rows(results_file):
    if not results_file or not os.path.isfile(results_file):
        logger.warning("alert results file is missing (%s)", results_file or "not provided")
        return
    with gzip.open(results_file, "rt", newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            yield row


def _field_values(row, name) -> list:
    """Values for one field of a result-CSV row. Multivalue fields come with a
    __mv_<name> companion column encoded $value$;$value$ with $ doubled."""
    mv = row.get("__mv_" + name) or ""
    if mv.startswith("$") and mv.endswith("$"):
        return [segment.replace("$$", "$") for segment in mv[1:-1].split("$;$")]
    value = row.get(name)
    return [value] if value else []


def _as_int(value, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, number))


if __name__ == "__main__":
    sys.exit(main(sys.argv))
