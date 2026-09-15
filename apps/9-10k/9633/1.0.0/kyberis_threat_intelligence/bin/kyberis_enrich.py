"""Streaming custom search command: ... | kyberis field=<fields> [profile=<name>] [objective=<text>] [cache=<bool>] [cim=<bool>]

Reads indicator values from the named event field(s), deduplicates them, and
enriches them in batched Kyberis API calls (never one call per event). Each
event gains kyberis_* fields; events whose fields are empty pass through
untouched. Runs on the search head (distributed=False) so credentials and
outbound API traffic stay off the indexers.

Results are cached across searches in the kyberis_ioc_cache KV Store
collection for cache_ttl_seconds (kyberis.conf); cache=false bypasses the
cache for one search, and a TTL of 0 disables it entirely.

Verdicts of cim_min_threat level or above additionally gain CIM Threat
Intelligence (threat_*) fields for ES consumption (kyberis_splunk.cim);
cim=false suppresses them for one search.
"""

import logging
import os
import sys

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BIN_DIR, "lib"))
sys.path.insert(0, BIN_DIR)

from splunklib.searchcommands import Configuration, Option, StreamingCommand, dispatch, validators

from kyberis_splunk.cache import IocCache
from kyberis_splunk.cim import threat_fields
from kyberis_splunk import logscrub
from kyberis_splunk.enrich import (
    MAX_BATCH_ITEMS,
    Enricher,
    EnrichmentAuthError,
    EnrichmentPrivacyError,
    EnrichmentQuotaError,
)
from kyberis_splunk.settings import KyberisSettingsError, build_client


@Configuration(distributed=False)
class KyberisEnrichCommand(StreamingCommand):
    field = Option(
        require=True,
        doc="Comma-separated event field(s) holding indicator values to enrich.",
    )
    profile = Option(
        require=False,
        doc="Credential profile to use; defaults to default_profile from kyberis.conf.",
    )
    objective = Option(
        require=False,
        doc=(
            "Override for the enrichment objective reported to the Kyberis API "
            "(8-280 characters). Must never contain search text."
        ),
    )
    cache = Option(
        require=False,
        default=True,
        validate=validators.Boolean(),
        doc="Set cache=false to bypass the cross-search KV Store cache for this search.",
    )
    cim = Option(
        require=False,
        default=True,
        validate=validators.Boolean(),
        doc="Set cim=false to suppress CIM Threat Intelligence (threat_*) fields for this search.",
    )

    def stream(self, records):
        # Before anything can log: redact credential material from search.log
        # output (secrets are registered when the profile resolves). The
        # splunkd session key is a credential too — splunklib sends it on
        # every management call and could surface it in DEBUG/error output.
        logscrub.install()
        logscrub.register_secret(getattr(self.metadata.searchinfo, "session_key", None))

        field_names = [name.strip() for name in str(self.field).split(",") if name.strip()]
        if not field_names:
            self.error_exit(ValueError("field="), "The field= option must name at least one event field.")
            return

        if self.objective is not None and not 8 <= len(str(self.objective).strip()) <= 280:
            self.error_exit(
                ValueError("objective="),
                "The objective= option must be 8-280 characters long.",
            )
            return

        enricher = self._enricher()

        # Buffer events until the batch of unknown indicators is full, then
        # enrich and flush. Small batches keep the command responsive to
        # search finalization/cancellation between API calls.
        buffered = []
        pending = set()
        for record in records:
            pairs = _indicator_pairs(record, field_names)
            buffered.append((record, pairs))
            pending.update(v for v, _ in pairs if not enricher.cached(v))
            if len(pending) >= MAX_BATCH_ITEMS:
                yield from self._flush(enricher, buffered, pending)
                buffered, pending = [], set()

        yield from self._flush(enricher, buffered, pending)
        self._finish_cache()

    def _enricher(self):
        enricher = getattr(self, "_enricher_instance", None)
        if enricher is None:
            try:
                client, resolved = build_client(self.service, self.profile)
            except KyberisSettingsError as error:
                self.error_exit(error, str(error))
            logging.getLogger().setLevel(resolved.log_level)
            cache = None
            if self.cache:
                cache = IocCache(
                    self.service,
                    resolved.cache_ttl_seconds,
                    logger=self.logger,
                    base_url=resolved.config.base_url,
                )
                if not cache.active:
                    cache = None
            self._cache_instance = cache
            self._cim_min = resolved.cim_min_threat if self.cim else None
            searchinfo = self.metadata.searchinfo
            enricher = Enricher(
                client,
                resolved.auth_header,
                run_id=searchinfo.sid,
                objective=self.objective,
                cache=cache,
                # The raw SPL of the running search (and this command's own
                # argument text) must never reach a request body.
                never_send=(
                    getattr(searchinfo, "search", ""),
                    getattr(searchinfo, "args", ""),
                ),
            )
            self._enricher_instance = enricher
        return enricher

    def _finish_cache(self):
        cache = getattr(self, "_cache_instance", None)
        if cache is None:
            return
        cache.purge_expired()
        self.logger.info(
            "kyberis cache: %d hit(s), %d miss(es), %d write(s)",
            cache.hits,
            cache.misses,
            cache.writes,
        )

    def _flush(self, enricher, buffered, pending):
        try:
            enricher.enrich(pending)
        except (EnrichmentAuthError, EnrichmentPrivacyError) as error:
            self.error_exit(error, str(error))
        except EnrichmentQuotaError as error:
            self.write_warning(str(error))

        # Transport failures only annotate events; without this banner the
        # search looks successful at a glance.
        if enricher.transport_error_message and not getattr(self, "_transport_warned", False):
            self._transport_warned = True
            self.write_warning(
                enricher.transport_error_message
                + " Affected events are annotated with kyberis_status=transport_error."
            )

        for record, pairs in buffered:
            _annotate(record, pairs, enricher, self._cim_min)
            yield record


def _indicator_pairs(record, field_names):
    """Distinct, ordered (value, source field) pairs from the record's target
    fields; a value appearing in several fields keeps the first field."""
    pairs = []
    seen = set()
    for name in field_names:
        raw = record.get(name)
        for value in raw if isinstance(raw, list) else [raw]:
            value = str(value).strip() if value is not None else ""
            if value and value not in seen:
                seen.add(value)
                pairs.append((value, name))
    return pairs


def _annotate(record, pairs, enricher, cim_min):
    if not pairs:
        return
    results = []
    for value, source_field in pairs:
        fields = dict(enricher.result_for(value))
        if cim_min is not None:
            fields.update(threat_fields(source_field, value, fields, cim_min))
        results.append(fields)

    if len(pairs) == 1:
        record["kyberis_ioc"] = pairs[0][0]
        record.update(results[0])
        return

    # Multiple indicators in one event: emit multivalue fields aligned by
    # index with kyberis_ioc, padding fields a given result lacks.
    keys = []
    for result in results:
        for key in result:
            if key not in keys:
                keys.append(key)
    record["kyberis_ioc"] = [value for value, _ in pairs]
    for key in keys:
        record[key] = [_flatten(result.get(key, "")) for result in results]


def _flatten(value):
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return value


dispatch(KyberisEnrichCommand, sys.argv, sys.stdin, sys.stdout, __name__)
