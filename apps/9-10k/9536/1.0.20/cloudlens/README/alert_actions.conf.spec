[cloudlens_finding]

param.severity = <string>
* Default severity when the alert result has no severity field.

param.default_status = <string>
* Initial finding status. Default: new.

param.lookback_secs = <integer>
* Timeline seconds before the alert. Default: 7200.

param.lookahead_secs = <integer>
* Timeline seconds after the alert. Default: 1800.

param.max_findings_per_alert = <integer>
* Maximum result rows converted per invocation. Default: 100.

param.max_hydrations_per_alert = <integer>
* Maximum automatic timeline searches dispatched per invocation when automatic
  generation is enabled globally in Setup. Default: 10.

param.max_timeline_events = <integer>
* Maximum CloudTrail rows stored by one timeline hydration. Default: 2000.

param.hydration_max_time_secs = <integer>
* Maximum runtime for one manual or automatic timeline search. Default: 300 seconds.

param.include_role_lineage = <boolean>
* Enables the enriched AssumeRole lineage engine for automatic timeline
  generation. Default: false. Analysts can enable it per manual fetch.

param.hydration_retry_only = <boolean>
* Internal retry mode; customer alerts must leave this disabled.

param.hydration_retry_max_attempts = <integer>
* Maximum durable timeline hydration attempts. Default: 5.

param.hydration_complete_only = <boolean>
* Internal hydration completion mode; customer alerts must leave this disabled.

param.maintenance_mode = <string>
* Internal bounded-retention mode; customer alerts must leave this empty.
