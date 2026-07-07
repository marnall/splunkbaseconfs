#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.2.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# Standard library imports
import logging
import os
import sys
import time
from logging.handlers import RotatingFileHandler

# splunkhome
splunkhome = os.environ["SPLUNK_HOME"]

# rotating-file logger — same setup as the historical implementation so
# the operator log path doesn't move under existing log-monitoring rules.
filehandler = RotatingFileHandler(
    "%s/var/log/splunk/trackme_api_autodocs.log" % splunkhome,
    mode="a",
    maxBytes=10000000,
    backupCount=1,
)
formatter = logging.Formatter(
    "%(asctime)s %(levelname)s %(filename)s %(funcName)s %(lineno)d %(message)s"
)
logging.Formatter.converter = time.gmtime
filehandler.setFormatter(formatter)
log = logging.getLogger()  # root logger
for hdlr in log.handlers[:]:
    if isinstance(hdlr, logging.FileHandler):
        log.removeHandler(hdlr)
log.addHandler(filehandler)
log.setLevel(logging.INFO)

# Path setup so trackme_libs is importable.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
import import_declare_test  # noqa: F401 — Splunk import shim

# Splunk libs
from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)

# TrackMe libs
from trackme_libs import trackme_reqinfo
from trackme_libs_autodocs_catalog_builder import build_catalog_as_list_cached


@Configuration(distributed=False)
class TrackMeApiAutoDocs(GeneratingCommand):
    """SPL custom command — emit the TrackMe API catalog as search rows.

    Historically, this class owned everything: the handler imports, the
    handler→resource_group dictionary, the introspection of each
    handler's methods, and the HTTPS-loopback that calls each method
    with ``describe=true``.

    All of that has moved to ``trackme_libs_autodocs_catalog_builder``
    so the same logic is reusable from a REST endpoint (the Concierge
    Advisor's ``discover_endpoints`` MCP tool needs JSON, not SPL rows).
    The class now is a thin wrapper that calls
    ``build_catalog_as_list_cached`` and yields each entry as an SPL
    row in the historical shape — operators and dashboards reading the
    SPL output keep working unchanged.

    Cache behaviour (PR adding this — May 2026):

      Previously this class called ``build_catalog`` (the uncached
      generator) which paid the full ~19s build on EVERY invocation.
      The REST API Reference UI fires this command on every page open
      (one call for ``target="groups"``, one per resource-group
      drill-in for ``target="endpoints"``), so the page felt
      consistently slow.

      Switching to ``build_catalog_as_list_cached`` shares the
      filesystem cache (PR #1329) with the Concierge describe payload
      and the ``/configuration/api_catalog`` REST endpoint. Cache key
      is ``(target, app_version)`` — one cache file per ``target``,
      auto-invalidates on app upgrade. First call after an upgrade
      pays the rebuild; every subsequent call reads from disk in
      sub-second time.

      In practice, PR #1461's schema-migration warmup (in
      ``trackmetrackerhealth.py``) runs in tracker-owner context
      (typically a ``trackme_admin`` role) and pre-populates the
      cache during the first per-tenant migration cycle after each
      app upgrade. By the time a human user opens the REST API
      Reference page, the cache is already warm with the maximal
      RBAC view. The first user (whoever fires first) does NOT pay
      the rebuild themselves.

      RBAC trade-off (already documented in the catalog builder
      module): the cache reflects the FIRST builder's RBAC view.
      Splunkd enforces per-handler capabilities at routing time, so
      a non-admin user who somehow fired the build before any
      warmup would cache a restricted view. Mitigations: (a) the
      warmup typically wins the race; (b) the ``force_rebuild=true``
      SPL option below lets an admin invalidate and rebuild on
      demand. The catalog is documentation only — visibility never
      bypasses authorization at call time, the user's actual REST
      calls still go through their own RBAC.

    Usage:

        | trackmeapiautodocs target="endpoints"
        | trackmeapiautodocs target="groups"
        | trackmeapiautodocs target="endpoints" force_rebuild=true
    """

    target = Option(
        doc="""
        **Syntax:** **target=****
        **Description:** The type of objects to be returned, valid options are: groups | endpoints""",
        require=False,
        default="endpoints",
        validate=validators.Match("mode", r"^(?:groups|endpoints)$"),
    )

    force_rebuild = Option(
        doc="""
        **Syntax:** **force_rebuild=**<bool>
        **Description:** When ``true``, bypass the per-version
        filesystem cache and rebuild the catalog by exercising every
        handler describe block. Use after registering a new endpoint
        mid-version (without bumping the app version) so the cache
        reflects the addition without waiting for the next deploy.
        Default: ``false`` (cache hit when present, build + cache
        when cold).""",
        require=False,
        default=False,
        validate=validators.Boolean(),
    )

    def generate(self, **kwargs):
        # Lift logging level from per-tenant config (matches the
        # historical entry point — operators set the level via the
        # standard trackme settings UI).
        reqinfo = trackme_reqinfo(
            self._metadata.searchinfo.session_key,
            self._metadata.searchinfo.splunkd_uri,
        )
        log.setLevel(reqinfo["logging_level"])

        start = time.time()
        emitted = 0

        # ``build_catalog_as_list_cached`` materialises the full
        # catalog before returning (filesystem cache write requires
        # the complete list). For the SPL surface this is fine —
        # 423 entries × ~1-2KB each ≈ 1MB, well within memory budget.
        # The historical generator pattern (``build_catalog`` yielding
        # per-row) didn't help streaming anyway because the SPL
        # framework buffers the chunk before flushing to splunkd.
        catalog = build_catalog_as_list_cached(
            splunkd_uri=self._metadata.searchinfo.splunkd_uri,
            session_key=self._metadata.searchinfo.session_key,
            target=self.target,
            force_rebuild=bool(self.force_rebuild),
        )
        for entry in catalog:
            # Yield in the historical SPL row shape: top-level keys for
            # filtering / display, full payload mirrored under ``_raw``
            # for completeness. Errors flow through the same path —
            # ``entry`` carries an ``"error"`` key that operators can
            # filter on.
            row = {"_time": time.time(), "_raw": entry, **entry}
            emitted += 1
            yield row

        run_time = round(time.time() - start, 3)
        logging.info(
            f"trackmeapiautodocs execution terminated, "
            f"target={self.target!r} force_rebuild={bool(self.force_rebuild)} "
            f"emitted={emitted} run_time={run_time}s"
        )


dispatch(TrackMeApiAutoDocs, sys.argv, sys.stdin, sys.stdout, __name__)
