"""Streaming search command for Whisper IOC enrichment.

``| whisperlookup field=<field> [type=auto|domain|ip]
  [include_threat_intel=true] [include_cname=true]
  [include_nameserver=true] [include_feeds=true]
  [add_prefix=whisper_] [use_cache=true]``

Enriches each event by querying the Whisper Knowledge Graph API for
infrastructure context (ASN, prefix, geolocation, co-hosting density),
threat intelligence, CNAME chain, and nameserver data.

Cache lookup order: precomputed collection -> enrichment cache -> live API.

Enrichment logic is in whisper_enrichment.py.
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from splunklib.searchcommands import (  # noqa: E402
    Configuration,
    Option,
    StreamingCommand,
    dispatch,
    validators,
)
from whisper_enrichment_cache import enrich_event_cached  # noqa: E402
from whisper_logging import get_logger, setup_logging  # noqa: E402

logger = get_logger("lookup_command")
setup_logging("lookup_command")


@Configuration()
class WhisperLookupCommand(StreamingCommand):
    """Streaming search command that enriches events via the Whisper Knowledge Graph API.

    Usage::

        | whisperlookup field=<field> [type=auto|domain|ip]
          [include_threat_intel=true] [include_cname=true]
          [include_nameserver=true] [include_feeds=true]
          [add_prefix=whisper_] [use_cache=true]
    """

    field = Option(name="field", require=True, validate=validators.Fieldname())
    type = Option(name="type", require=False, default="auto")
    include_threat_intel = Option(
        name="include_threat_intel", require=False, default=True, validate=validators.Boolean()
    )
    include_cname = Option(name="include_cname", require=False, default=True, validate=validators.Boolean())
    include_nameserver = Option(name="include_nameserver", require=False, default=True, validate=validators.Boolean())
    include_feeds = Option(name="include_feeds", require=False, default=True, validate=validators.Boolean())
    add_prefix = Option(name="add_prefix", require=False, default="whisper_")
    use_cache = Option(name="use_cache", require=False, default=True, validate=validators.Boolean())

    def stream(self, records):
        """Enrich each event with Whisper Knowledge Graph data.

        Args:
            records: Iterator of Splunk event dictionaries.

        Yields:
            Enriched event dictionaries.
        """
        from whisper_command_helpers import get_api_client_from_service

        try:
            client = get_api_client_from_service(self.service)
        except RuntimeError as exc:
            logger.error("action=whisperlookup status=error reason=client_init_failed", exc_info=True)
            self.error_exit(exc, str(exc))
            return

        cache = None
        precomputed = None
        if self.use_cache:
            try:
                from whisper_cache import EnrichmentCache

                cache_collection = self.service.kvstore["whisper_enrichment_cache"]
                cache = EnrichmentCache(cache_collection)
            except Exception:
                logger.debug("Cache unavailable, proceeding without cache")

            try:
                precomputed = self.service.kvstore["whisper_precomputed_enrichment"]
            except Exception:
                logger.debug("Precomputed collection unavailable")

        try:
            for record in records:
                enrich_start = time.monotonic()
                try:
                    record = enrich_event_cached(
                        client,
                        record,
                        field=self.field,
                        indicator_type=self.type,
                        include_threat_intel=self.include_threat_intel,
                        include_cname=self.include_cname,
                        include_nameserver=self.include_nameserver,
                        include_feeds=self.include_feeds,
                        add_prefix=self.add_prefix,
                        cache=cache,
                        precomputed_collection=precomputed,
                    )
                except Exception as exc:
                    logger.warning("action=enrich_event, status=error, error=%s", exc)
                # Add per-event enrichment timing
                enrich_elapsed_ms = int((time.monotonic() - enrich_start) * 1000)
                record["whisper_enrichment_time_ms"] = enrich_elapsed_ms
                yield record
        finally:
            if client:
                client.close()


if __name__ == "__main__":
    dispatch(WhisperLookupCommand, sys.argv, sys.stdin, sys.stdout, __name__)
