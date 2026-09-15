# Detection engineering assurance

**Author:** Eric Cobbs

**Required dependency:** Splunk Enterprise Security 8.x

CDCC assurance is intentionally bounded to observe, recommend, and optionally notify. Enterprise Security remains authoritative for detection testing, versioning, editing, enablement, scheduling, promotion, and rollback.

## Enabled assessments

- Reliability: repeated failed or skipped scheduler executions
- Runtime regression: 24-hour p95 runtime compared with the preceding seven-day baseline
- Schedule collision: dense cron groups that merit human review
- Metadata compliance: annotations, version metadata, descriptions, and action messages
- Data contract: field-readiness exceptions by sourcetype
- Zero-yield review: repeatedly successful executions with no risk events or findings

Assessment events are written to `index=summary source=cdcc:detection_assurance`. Each run writes both healthy and open state, allowing the dashboard to select the latest state per assurance key.

## Optional notification

`CDCC Assurance - Critical Engineering Issue - Finding` is disabled by default. If an administrator enables it after validation, recent high or critical states generate suppressed ES audit-domain findings. It never changes detection configuration.

## Production checklist

1. Confirm the summary index exists, retention is appropriate, and intended users can read it.
2. Validate each assessment manually against local ES field conventions and permissions.
3. Adjust schedules to avoid local search concurrency peaks.
4. Confirm assessment ownership and review workflow.
5. Decide whether to enable the optional finding notifier; keep it disabled if dashboard review is sufficient.
