# PhishIQPlus Enterprise Handover Checklist

Use this checklist before handing the package to a customer SOC or production operations team.

---

## 1) Deployment Scope

- [ ] Confirm deployment target: Heavy Forwarder only, or HF + Search Head package.
- [ ] Confirm Splunk version compatibility (Splunk 8.x+ with Python 3).
- [ ] Confirm app path and name (`$SPLUNK_HOME/etc/apps/phishiq_ta`).

## 2) Connectivity and Credentials

- [ ] Verify outbound HTTPS connectivity from HF to PhishIQPlus API base URL.
- [ ] Configure API key in modular input UI and save successfully.
- [ ] Confirm API key is stored in credential store (not plaintext configs).
- [ ] Run Setup/Test Connection and validate no 401/403 errors.

## 3) Data Input Configuration

- [ ] Confirm primary mode (`batch` or `dynamic`) per customer use case.
- [ ] For `dynamic`, set:
  - [ ] `source_search`
  - [ ] `source_url_field`
  - [ ] `source_search_limit`
  - [ ] `source_search_overlap_seconds`
  - [ ] `source_search_batch_size`
  - [ ] `source_search_max_urls`
- [ ] Confirm target `index` and `sourcetype` for enriched events.

## 4) Reliability and Performance Controls

- [ ] Confirm retry/circuit-breaker defaults are accepted by customer.
- [ ] Validate run-lock behavior (no overlapping stanza execution).
- [ ] Validate checkpoint behavior over 2-3 consecutive runs.
- [ ] Validate dynamic throttle (`dynamic_sleep_ms_between_batches`) if API quota is strict.

## 5) Parsing and Search Experience

- [ ] Confirm `props.conf` and `transforms.conf` are deployed on search tier.
- [ ] Validate field extraction for:
  - [ ] `phishiq_prediction`
  - [ ] `phishiq_risk_level`
  - [ ] `phishiq_source_event_hash`

## 6) SOC Operational Views

- [ ] Validate dashboard: **PhishIQPlus - Health**
- [ ] Validate dashboard: **PhishIQPlus - Correlation**
- [ ] Validate dashboard: **PhishIQPlus - Manual Test**
- [ ] Validate macros:
  - [ ] `phishiqplus_correlation_filter(index,sourcetype)`
  - [ ] `phishiqplus_correlation_fields`

## 7) Alerting Baseline

- [ ] Enable and review scheduled searches in `savedsearches.conf`.
- [ ] Validate alert behavior for:
  - [ ] High failure rate
  - [ ] Rate limiting / circuit breaker
- [ ] Integrate alert actions with customer workflow (email, webhook, SOAR, ticketing).

## 8) Rollback and Support

- [ ] Keep previous app version for rollback.
- [ ] Document rollback procedure (`disable input` -> `replace app` -> `restart`).
- [ ] Record owner contacts for API service and Splunk operations.
- [ ] Attach this package's `ARCHITECTURE.md`, `TESTING.md`, and this checklist to handover.
