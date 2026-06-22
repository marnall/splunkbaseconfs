#!/usr/bin/env python3
"""
framework_mapper.py — Layer 2: Framework Enrichment Engine
Compliance Posture for Splunk | GIC Engineering Consultants

Accepts normalized parser output from parse_arf.py and enriches each event
with framework-specific display labels, scoring metadata, and control taxonomy.

Driven entirely by JSON config files in lookups/frameworks/.
Adding a new framework (PCI-DSS, HIPAA, NIST CSF) requires:
  1. Adding a new config file: lookups/frameworks/<framework_id>.json
  2. No code changes to this module.

Usage (from upload_handler.py):
    from framework_mapper import FrameworkMapper
    mapper = FrameworkMapper(framework_id='cis_benchmarks')
    enriched_events = mapper.enrich(events)
"""

import json
import os


# ── Default config search paths ──────────────────────────────────────────────
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_SEARCH_PATHS = [
    # Splunk app standard location
    os.path.join(_SCRIPT_DIR, '..', 'lookups', 'frameworks'),
    # Dev/test: lookups/frameworks relative to script
    os.path.join(_SCRIPT_DIR, 'lookups', 'frameworks'),
    # Fallback: same directory as script
    os.path.join(_SCRIPT_DIR, 'frameworks'),
]


class FrameworkMapper:
    """
    Framework enrichment engine. Loads a framework config file and applies
    it to a list of normalized parser events.

    Args:
        framework_id (str):   Framework identifier matching a config filename.
                              e.g. 'cis_benchmarks' loads cis_benchmarks.json
        config_path (str):    Optional explicit path to the config file.
                              If not provided, searched in CONFIG_SEARCH_PATHS.
    """

    def __init__(self, framework_id='cis_benchmarks', config_path=None):
        self.framework_id = framework_id
        self.config = self._load_config(framework_id, config_path)

    def _load_config(self, framework_id, config_path=None):
        """Load and validate the framework configuration file."""
        filename = f"{framework_id}.json"

        # Explicit path provided
        if config_path:
            if not os.path.isfile(config_path):
                raise FileNotFoundError(
                    f"Framework config not found at explicit path: {config_path}"
                )
            return self._read_config(config_path)

        # Search standard paths
        for search_dir in CONFIG_SEARCH_PATHS:
            candidate = os.path.join(search_dir, filename)
            if os.path.isfile(candidate):
                return self._read_config(candidate)

        raise FileNotFoundError(
            f"Framework config '{filename}' not found. "
            f"Searched: {', '.join(CONFIG_SEARCH_PATHS)}"
        )

    @staticmethod
    def _read_config(path):
        """Read and parse a JSON config file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in framework config '{path}': {e}")

    def enrich(self, events):
        """
        Enrich a list of normalized parser events with framework-specific fields.

        Args:
            events (list[dict]): Output from parse_arf.parse_arf_file()

        Returns:
            list[dict]: Enriched events ready for Splunk ingestion.
        """
        enriched = []
        for event in events:
            enriched.append(self._enrich_event(event))
        return enriched

    def _enrich_event(self, event):
        """Apply framework enrichment to a single event dict."""
        e = dict(event)  # copy — do not mutate input

        # ── Framework identification ─────────────────────────────────────────
        e['framework']    = self.config.get('framework_id', self.framework_id)
        e['framework_name'] = self.config.get('framework_name', '')

        # ── Result display label ─────────────────────────────────────────────
        result_labels = self.config.get('result_labels', {})
        e['result_display'] = result_labels.get(
            e.get('result', ''),
            e.get('result', '')   # fall back to raw value if not in map
        )

        # ── Result classification booleans ───────────────────────────────────
        scored_pass_values  = set(self.config.get('scored_pass_values', ['pass']))
        scored_fail_values  = set(self.config.get('scored_fail_values', ['fail', 'error']))
        excluded_values     = set(self.config.get('excluded_from_scoring', ['notapplicable', 'informational']))

        result_val = e.get('result', '')
        e['is_pass']     = result_val in scored_pass_values
        e['is_fail']     = result_val in scored_fail_values
        e['is_excluded'] = result_val in excluded_values

        # Zero-weight rules are always excluded from scoring denominator
        if e.get('rule_weight', 1.0) == 0.0:
            e['is_excluded'] = True
            e['is_pass']     = False
            e['is_fail']     = False

        # ── Section label ────────────────────────────────────────────────────
        sections = self.config.get('sections', {})
        rule_section = e.get('rule_section', '')
        e['section_label'] = sections.get(rule_section, f"Section {rule_section}")

        # ── Scoring model ────────────────────────────────────────────────────
        scoring = self.config.get('scoring', {})
        e['scoring_model']    = scoring.get('model', 'percentage')
        e['score_field']      = scoring.get('score_field', 'compliance_score')
        e['score_label']      = scoring.get('score_label', 'Compliance Score')
        e['score_good_above'] = scoring.get('good_above', 80.0)
        e['score_warn_above'] = scoring.get('warn_above', 60.0)

        # ── sourcetype (for Splunk field extraction reference) ───────────────
        e['sourcetype'] = self.config.get('sourcetype', 'ciscat:arf')

        return e


# ── Standalone runner ────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    from parse_arf import parse_arf_file

    if len(sys.argv) < 2:
        print("Usage: python3 framework_mapper.py <arf_xml_file> [framework_id]")
        sys.exit(1)

    file_path    = sys.argv[1]
    framework_id = sys.argv[2] if len(sys.argv) > 2 else 'cis_benchmarks'

    try:
        events = parse_arf_file(
            file_path,
            upload_time='2026-02-19T08:00:00',
            upload_batch_id='test_batch_001'
        )
        mapper  = FrameworkMapper(framework_id=framework_id)
        enriched = mapper.enrich(events)

        print(f"\nEnriched {len(enriched)} events with framework: {framework_id}")
        print(f"\nSample enriched fields (first event):")
        sample = enriched[0]
        for key in ['framework', 'framework_name', 'result', 'result_display',
                    'is_pass', 'is_fail', 'is_excluded', 'section_label',
                    'scoring_model', 'score_label', 'compliance_score',
                    'sourcetype']:
            print(f"  {key:<20} {sample.get(key)}")

        # Result breakdown
        from collections import Counter
        pass_count  = sum(1 for e in enriched if e['is_pass'])
        fail_count  = sum(1 for e in enriched if e['is_fail'])
        excl_count  = sum(1 for e in enriched if e['is_excluded'])
        print(f"\nResult classification:")
        print(f"  Pass:     {pass_count}")
        print(f"  Fail:     {fail_count}")
        print(f"  Excluded: {excl_count}")
        print(f"\nSUCCESS")

    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
