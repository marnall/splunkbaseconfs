"""Knowledge-layer seed catalogue (v1.0.0).

Two seed lists:
  STATIC_RULE_SEEDS    → seeded into itmip_knowledge_static_rules
  CURATED_ENTRY_SEEDS  → seeded into itmip_ai_knowledge_entries

Both follow the same lifecycle as skills / templates:
  - Re-seed-eligible rows: creator='system' AND version==1.
  - Admin-edited rows (version > 1 or creator != 'system') are immune.
  - Brand-new seeds inserted as new rows on first seed pass.

The seed pass is driven by `seed_static_rules()` /
`seed_curated_entries()` in itmip_knowledge_core.py — called lazily on
the first REST call to any knowledge endpoint.

Plan §15.3 (the 15 static rules) and §H2 (5+ curated entries — one of
each kind to prove the curated path).

All rules ship at DFLT/DFLT scope (global) and status='operational'.
"""

# ──────────────────────────────────────────────────────────────────────
# Static-library trigger rules — 15 OOTB rules per plan §15.3
# ──────────────────────────────────────────────────────────────────────

STATIC_RULE_SEEDS = [
    {
        "name": "windows-eventlog-suggest-asset-identity-enrichment",
        "title": "Windows event log -> Asset & Identity enrichment reminder",
        "summary": "When querying Windows event logs, suggest enriching with the Asset & Identity framework.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"index\s*=\s*wineventlog",
                r"sourcetype\s*=\s*WinEventLog",
                r"sourcetype\s*=\s*XmlWinEventLog",
            ],
        },
        "injected_guidance": (
            "Windows event log queries usually benefit from enriching `dest` and `user` "
            "with the Asset & Identity framework before correlation. Pattern:\n"
            "  ... | lookup asset_lookup_by_str src OUTPUTNEW priority as asset_priority, category as asset_category\n"
            "      | lookup identity_lookup_expanded user OUTPUTNEW priority as identity_priority\n"
            "This lets downstream notables and dashboards apply asset/identity-based risk scoring."
        ),
        "rule_priority": 70,
        "intent_kinds": ["soc-investigation", "spl-authoring", "detection-engineering"],
        "data_sources": ["Windows Security", "Windows", "Authentication"],
        "tags": ["windows", "enrichment", "asset-identity"],
    },
    {
        "name": "sysmon-xmlwineventlog-spath-extraction",
        "title": "XmlWinEventLog / Sysmon -> fields live in raw XML, extract with spath (not rex)",
        "summary": (
            "For XML-wrapped Windows Event Log / Sysmon sourcetypes the detection fields "
            "(EventID, Image, CommandLine, ParentImage, User, DestinationIp, DestinationPort) "
            "live inside the raw XML, not as index-time fields; extract them with spath up front "
            "instead of probing, and prefer spath over rex to avoid the angle-bracket escaping trap."
        ),
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"sourcetype\s*=\s*[\"']?XmlWinEventLog",
                r"Microsoft-Windows-Sysmon",
                r"sourcetype\s*=\s*[\"']?WinEventLog",
            ],
        },
        "injected_guidance": (
            "XML-wrapped Windows Event Log / Sysmon events (sourcetypes like "
            "XmlWinEventLog:Microsoft-Windows-Sysmon/Operational) carry their detection fields "
            "INSIDE the raw XML, NOT as index-time fields -- a bare `... | stats count by CommandLine` "
            "returns nothing, so do not discover this by trial-and-error. Extract with one spath up front:\n"
            "  index=<idx> sourcetype=XmlWinEventLog:Microsoft-Windows-Sysmon/Operational | spath input=_raw\n"
            "`Event.System.EventID` gives the event id. The per-detection fields live in the EventData "
            "block as an array of <Data Name='...'>value</Data> pairs -- reference them via the "
            "`Event.EventData.Data{@Name=\"CommandLine\"}` style paths (Image, CommandLine, ParentImage, "
            "User, DestinationIp, DestinationPort). Useful event-id semantics: EventID 1 = Process Create "
            "(Image / CommandLine / ParentImage / User -- the right source for process-discovery techniques "
            "like T1057 / T1082 / T1518 / T1033); EventID 3 = Network Connect (DestinationIp / DestinationPort "
            "-- the right source for network-service-discovery like T1046).\n"
            "PREFER spath OVER rex for XML: a rex named capture `(?<f>...)` stays literal in an ad-hoc "
            "splunk_run_search but MUST be written `(?&lt;f&gt;...)` inside a dashboard <query> block; "
            "mismatching that is a common failure (the regex won't compile). spath has no angle brackets "
            "and behaves identically in a raw search and inside a dashboard <query>."
        ),
        "rule_priority": 75,
        "intent_kinds": ["spl-authoring", "soc-investigation", "detection-engineering", "dashboard-authoring"],
        "data_sources": ["Sysmon", "Windows", "XmlWinEventLog", "Endpoint"],
        "tags": ["sysmon", "windows", "xml", "spath", "field-extraction"],
    },
    {
        "name": "aws-cloudtrail-suggest-region-filter",
        "title": "AWS CloudTrail -> region filter reminder",
        "summary": "SPL against AWS CloudTrail without an awsRegion filter scans every region and inflates cost.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"index\s*=\s*aws_cloudtrail",
                r"sourcetype\s*=\s*aws:cloudtrail",
            ],
        },
        "injected_guidance": (
            "CloudTrail queries that cover all regions are usually a sign of missing context. "
            "Add `awsRegion=<region>` (or a list `awsRegion IN (eu-west-1, eu-central-1, ...)`) to "
            "the search clause unless the user specifically wants global scope. This is both a "
            "cost-control measure (per-region indexes scan less data) and a noise-control one "
            "(many regions never have legitimate activity in a given account)."
        ),
        "rule_priority": 60,
        "intent_kinds": ["spl-authoring", "soc-investigation", "detection-engineering"],
        "data_sources": ["AWS CloudTrail", "AWS"],
        "tags": ["aws", "cloudtrail", "cost-control"],
    },
    {
        "name": "sourcetype-wildcard-suggest-narrowing",
        "title": "sourcetype=* -> suggest narrowing",
        "summary": "`sourcetype=*` (or omitted sourcetype) is almost always a mistake; warn and suggest narrowing.",
        "trigger_pattern": {
            "match_in": ["spl_drafted"],
            "patterns": [
                r"sourcetype\s*=\s*\*",
                r"^\s*search\s+index\s*=[^|]*$",
            ],
        },
        "injected_guidance": (
            "Searches without an explicit sourcetype scan everything in the index and "
            "force Splunk to evaluate every extracted field across every sourcetype. "
            "Pick a sourcetype (or a short OR-list of sourcetypes) before running the "
            "search. If the user genuinely doesn't know which sourcetype carries the "
            "data, call `splunk_list_indexes` + the discovery searches first."
        ),
        "rule_priority": 65,
        "intent_kinds": ["spl-authoring"],
        "tags": ["spl", "performance"],
    },
    {
        "name": "lookup-no-output-suggest-default",
        "title": "`lookup` without OUTPUT/OUTPUTNEW -> warn",
        "summary": "A `lookup` clause without OUTPUT/OUTPUTNEW silently adds every lookup column.",
        "trigger_pattern": {
            "match_in": ["spl_drafted"],
            "patterns": [
                r"\|\s*lookup\s+[\w_-]+\s+[\w_-]+\s*(?:$|\|)",
            ],
        },
        "injected_guidance": (
            "Without `OUTPUT` or `OUTPUTNEW`, every column of the lookup is added to "
            "every event — which is wasteful and can collide with existing fields. "
            "Either specify the columns you actually need "
            "(`OUTPUT col1, col2 as alias`) or use `OUTPUTNEW` so only missing fields "
            "are added (safer when re-running over already-enriched events)."
        ),
        "rule_priority": 55,
        "intent_kinds": ["spl-authoring"],
        "tags": ["spl", "lookup"],
    },
    {
        "name": "index-asterisk-warn-cost",
        "title": "`index=*` without time filter -> warn about scan cost",
        "summary": "`index=*` plus open time range scans everything ingested ever.",
        "trigger_pattern": {
            "match_in": ["spl_drafted"],
            "patterns": [
                r"index\s*=\s*\*",
            ],
        },
        "injected_guidance": (
            "`index=*` reads every index the user can see. If you also lack a tight "
            "`earliest`/`latest`, this can scan terabytes. Replace with the specific "
            "index name(s) and add a time window. If the user genuinely needs to "
            "search across many indexes (e.g. for an IOC sweep), use an explicit "
            "OR-list (`index=(idx1 OR idx2 OR idx3)`) plus `earliest=-7d@d` minimum."
        ),
        "rule_priority": 75,
        "intent_kinds": ["spl-authoring", "soc-investigation"],
        "tags": ["spl", "performance", "cost-control"],
    },
    {
        "name": "correlation-search-suggest-rba",
        "title": "Correlation search -> consider RBA pattern over notable-direct",
        "summary": "When designing a new correlation search, consider Risk-Based Alerting over a direct notable.",
        "trigger_pattern": {
            "match_in": ["query"],
            "patterns": [
                r"correlation search",
                r"build (a |an )?detection",
                r"create (a |an )?correlation",
            ],
        },
        "injected_guidance": (
            "For new ES correlation searches, consider the Risk-Based Alerting (RBA) "
            "pattern over writing directly to `index=notable`. RBA writes a risk_score "
            "increment to `index=risk` keyed on the affected entity, and a single "
            "risk-incident-rule correlation search fires the notable when accumulated "
            "risk crosses a threshold. Pros: aggregates many low-confidence signals "
            "into one high-confidence notable, reduces alert fatigue, and the risk "
            "timeline becomes the analyst's investigation surface."
        ),
        "rule_priority": 60,
        "intent_kinds": ["detection-engineering"],
        "data_sources": ["Enterprise Security"],
        "tags": ["es", "correlation-search", "rba"],
    },
    {
        "name": "kvstore-vs-csv-lookup-tradeoff",
        "title": "Threat-intel lookup -> KVStore vs CSV trade-off",
        "summary": "Threat-intel feeds usually need KVStore lookups, not flat CSVs.",
        "trigger_pattern": {
            "match_in": ["query"],
            "patterns": [
                r"threat intel",
                r"threat-intel",
                r"ioc lookup",
                r"indicator of compromise",
            ],
        },
        "injected_guidance": (
            "For threat-intel data: prefer a KVStore lookup over a CSV lookup. "
            "KVStore handles concurrent updates (one feed-loader script writing while "
            "search heads read), supports indexed reads via `_key`, and survives a SH "
            "restart. CSV lookups are fine for static reference data (CIDR-to-name maps, "
            "service-account allowlists) but break under contention and don't index. "
            "ES uses KVStore for its `threat_intel_by_*` collections for this reason."
        ),
        "rule_priority": 50,
        "intent_kinds": ["spl-authoring", "detection-engineering"],
        "tags": ["lookup", "threat-intel"],
    },
    {
        "name": "wineventlog-codes-without-cim",
        "title": "Specific Windows event codes -> suggest CIM normalisation",
        "summary": "Querying 4624/4625 directly works but loses CIM portability.",
        "trigger_pattern": {
            "match_in": ["spl_drafted"],
            "patterns": [
                r"EventCode\s*=\s*462[4-9]",
                r"EventCode\s*IN\s*\(",
            ],
        },
        "injected_guidance": (
            "Querying raw Windows event codes (4624, 4625, 4634, 4648, ...) works but "
            "produces SPL that only matches Windows. Consider the CIM Authentication "
            "data model: `| tstats count from datamodel=Authentication where "
            "Authentication.action=success` covers 4624 plus Linux PAM, SSH, AWS IAM, "
            "Azure AD, and any other auth source the user later onboards. CIM "
            "normalisation is the difference between a Windows-specific detection and "
            "one that grows with the environment."
        ),
        "rule_priority": 55,
        "intent_kinds": ["spl-authoring", "detection-engineering"],
        "data_sources": ["Windows", "Windows Security"],
        "data_models": ["Authentication"],
        "tags": ["windows", "cim"],
    },
    {
        "name": "dns-suggest-stream-or-cim",
        "title": "DNS query -> use Stream or CIM Network_Resolution",
        "summary": "DNS queries belong in the Network_Resolution data model.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"\bdns\b",
                r"sourcetype\s*=\s*stream:dns",
                r"sourcetype\s*=\s*dns",
            ],
        },
        "injected_guidance": (
            "DNS data should flow through Splunk Stream (sourcetype=stream:dns) or a "
            "vendor TA that maps to the CIM Network_Resolution data model. Querying "
            "raw DNS log files directly works but loses correlation with the other "
            "Network_Resolution sources (DHCP, AD DNS, resolver appliances). Prefer "
            "`| tstats count from datamodel=Network_Resolution by Network_Resolution.query`."
        ),
        "rule_priority": 50,
        "intent_kinds": ["spl-authoring"],
        "data_sources": ["DNS"],
        "data_models": ["Network_Resolution"],
        "tags": ["dns", "cim"],
    },
    {
        "name": "firewall-cim-network-traffic-suggest",
        "title": "Firewall logs -> CIM Network_Traffic",
        "summary": "Firewall logs should normalise through the Network_Traffic data model.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"\bfirewall\b",
                r"sourcetype\s*=\s*pan:traffic",
                r"sourcetype\s*=\s*cisco:asa",
                r"sourcetype\s*=\s*fortigate",
            ],
        },
        "injected_guidance": (
            "Firewall traffic data fits the CIM Network_Traffic data model. Most "
            "vendor TAs (Palo Alto, Cisco ASA/FTD, Fortinet, Check Point) map their "
            "sourcetypes for you. Querying `| tstats count from "
            "datamodel=Network_Traffic by Network_Traffic.src, Network_Traffic.dest` "
            "is faster than raw search and works across vendors."
        ),
        "rule_priority": 50,
        "intent_kinds": ["spl-authoring", "detection-engineering"],
        "data_sources": ["Firewall", "Network Traffic"],
        "data_models": ["Network_Traffic"],
        "tags": ["firewall", "cim"],
    },
    {
        "name": "email-cim-email-suggest",
        "title": "Email logs -> CIM Email data model",
        "summary": "Email/SMTP logs (Exchange, Mimecast, Proofpoint) belong in the Email data model.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"\bemail\b",
                r"\bsmtp\b",
                r"sourcetype\s*=\s*ms:exchange",
                r"sourcetype\s*=\s*mimecast",
                r"sourcetype\s*=\s*proofpoint",
            ],
        },
        "injected_guidance": (
            "Email-related searches benefit from the CIM Email data model: it carries "
            "src_user, recipient, subject, action, message_id, attachment_hashes — the "
            "fields phishing detections actually need. The Microsoft Exchange, "
            "Mimecast, and Proofpoint TAs all map to this model."
        ),
        "rule_priority": 50,
        "intent_kinds": ["spl-authoring", "detection-engineering"],
        "data_sources": ["Email"],
        "data_models": ["Email"],
        "tags": ["email", "cim", "phishing"],
    },
    {
        "name": "endpoint-cim-endpoint-suggest",
        "title": "Process/file event queries -> CIM Endpoint",
        "summary": "Process/file-event data (Sysmon, EDR) belongs in the Endpoint data model.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"sysmon",
                r"\bprocess\b",
                r"\bedr\b",
                r"crowdstrike",
                r"sourcetype\s*=\s*XmlWinEventLog:Microsoft-Windows-Sysmon/Operational",
            ],
        },
        "injected_guidance": (
            "Process and file-event data fits the CIM Endpoint data model "
            "(Endpoint.Processes, Endpoint.Filesystem, Endpoint.Registry, "
            "Endpoint.Services). Sysmon, CrowdStrike, SentinelOne, Defender for "
            "Endpoint all map to this model via their TAs. Prefer the data model over "
            "raw event-code searches — the model normalises across vendors."
        ),
        "rule_priority": 55,
        "intent_kinds": ["spl-authoring", "detection-engineering"],
        "data_sources": ["Endpoint", "Sysmon"],
        "data_models": ["Endpoint"],
        "tags": ["endpoint", "cim", "edr"],
    },
    {
        "name": "cloud-cim-cloud-suggest",
        "title": "Cloud audit logs -> CIM Change / Authentication / Network_Resolution",
        "summary": "Cloud audit logs span several CIM data models.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"cloudtrail",
                r"azure activity",
                r"gcp audit",
                r"sourcetype\s*=\s*aws:cloudtrail",
                r"sourcetype\s*=\s*azure:activity",
            ],
        },
        "injected_guidance": (
            "Cloud audit logs split across several CIM data models depending on what "
            "the event describes: Change (IAM updates, resource creates/deletes), "
            "Authentication (console + STS auth events), Network_Resolution (Route 53 "
            "/ Azure DNS query logs). Pick the model that matches what you're hunting; "
            "querying raw `aws:cloudtrail` works but loses cross-cloud portability."
        ),
        "rule_priority": 50,
        "intent_kinds": ["spl-authoring", "soc-investigation"],
        "data_sources": ["AWS CloudTrail", "Azure Activity", "GCP Audit"],
        "data_models": ["Change", "Authentication"],
        "tags": ["cloud", "cim", "aws", "azure", "gcp"],
    },
    {
        "name": "rest-api-search-mode-restriction",
        "title": "REST /search/jobs -> set earliest/latest explicitly",
        "summary": "When dispatching SPL via /services/search/jobs, always set dispatch.earliest_time + latest_time.",
        "trigger_pattern": {
            "match_in": ["query", "spl_drafted"],
            "patterns": [
                r"/services/search/jobs",
                r"search/jobs",
                r"rest api.*search",
            ],
        },
        "injected_guidance": (
            "When dispatching SPL via the Splunk REST API (`/services/search/jobs`), "
            "always include `dispatch.earliest_time` and `dispatch.latest_time` in the "
            "POST body. The default if you omit them is the user's current saved "
            "time-range preference, which is different across users and can scan "
            "unintended amounts of data. Be explicit: `dispatch.earliest_time=-15m@m`, "
            "`dispatch.latest_time=now`."
        ),
        "rule_priority": 45,
        "intent_kinds": ["spl-authoring"],
        "tags": ["rest-api", "search-jobs"],
    },
    {
        "name": "tstats-prefer-over-stats-for-datamodels",
        "title": "Data model query -> prefer `tstats` over `stats`",
        "summary": "When querying an accelerated data model, `tstats` reads tsidx and is orders of magnitude faster than `stats`.",
        "trigger_pattern": {
            "match_in": ["spl_drafted"],
            "patterns": [
                r"\|\s*stats\s+.*\s+from\s+datamodel",
                r"datamodel\s+[\w_]+\s+[\w_]+\s+\|.*\bstats\b",
            ],
        },
        "injected_guidance": (
            "When the query is against a data model (especially an accelerated one), "
            "use `| tstats summariesonly=true count from datamodel=<m> by <fields>` "
            "instead of `| datamodel <m> | stats ...`. `tstats` reads the tsidx "
            "summary directly and is typically 10-100x faster than the stats-over-"
            "datamodel form, because the latter expands each event."
        ),
        "rule_priority": 65,
        "intent_kinds": ["spl-authoring"],
        "tags": ["spl", "tstats", "performance"],
    },
]


# ──────────────────────────────────────────────────────────────────────
# Curated entries — 5+ entries, one per `kind` to prove the path.
# ──────────────────────────────────────────────────────────────────────

CURATED_ENTRY_SEEDS = [
    {
        "name": "msp-soc-noisy-detection-tuning-process",
        "title": "Tuning a noisy detection — MSP playbook",
        "kind": "tuning-note",
        "summary": "Three-step tuning process for a correlation search firing >20 notables/day in a normal environment.",
        "response_guidance": (
            "A correlation search firing >20 notables/day in a non-incident environment "
            "is noise. Tune in this order:\n\n"
            "1. **Identify the noisy axis.** Run `index=notable rule_name=<X> | stats "
            "count by user, src, dest, sourcetype | sort -count | head 20`. The top "
            "row almost always shows the axis to exclude.\n\n"
            "2. **Confirm legitimacy.** For service accounts (svc-*, *-bot, *-cron), "
            "scanners (Qualys, Tenable, Rapid7), and known automation hosts, "
            "exclusion is safe.\n\n"
            "3. **Apply via the detection's `where` clause, not the input filter.** "
            "Where-clause exclusions are visible to the analyst when they read the "
            "search; input-filter exclusions are invisible. Document the exclusion "
            "in `description`."
        ),
        "tags": ["soc", "tuning", "msp"],
    },
    {
        "name": "lesson-2024-q4-credential-stuffing-vs-brute-force",
        "title": "Credential stuffing vs brute force — distinguishing them",
        "kind": "lesson-learned",
        "summary": "Q4 2024 incident: credential-stuffing campaign was initially mis-triaged as brute force.",
        "response_guidance": (
            "A T1110 (brute force) detection fires for **many failed logins from one "
            "source to many usernames**. T1110.004 (credential stuffing) fires for "
            "**many login attempts where each user is tried once** — the attacker is "
            "trying leaked credentials, not guessing passwords.\n\n"
            "Distinguishing query:\n"
            "  `index=auth action=failure earliest=-1h `\n"
            "  `| stats dc(user) as unique_users, count by src `\n"
            "  `| where unique_users > 10 AND count/unique_users < 3`\n\n"
            "Output >5 means likely credential stuffing (high unique_users, low "
            "attempts/user). Output <2 with high count is classic brute force.\n\n"
            "Response: credential stuffing requires checking external breach databases "
            "(HaveIBeenPwned API, Recorded Future) for the matched usernames; brute "
            "force only requires source IP block + account-lockout policy review."
        ),
        "tags": ["incident-response", "auth", "credential-stuffing"],
        "mitre_techniques": ["T1110", "T1110.004"],
        "data_sources": ["Authentication"],
    },
    {
        "name": "cim-auth-data-onboarding-checklist",
        "title": "CIM Authentication onboarding checklist",
        "kind": "data-model-note",
        "summary": "Field mappings + props.conf checklist for new auth sources joining the Authentication data model.",
        "response_guidance": (
            "When onboarding a new authentication source to CIM:\n\n"
            "Required fields (case-sensitive in CIM, regardless of source):\n"
            "  - `action` = success | failure | (not modelled)\n"
            "  - `user` = the principal attempting auth\n"
            "  - `src` = source IP/host\n"
            "  - `dest` = destination IP/host or system\n"
            "  - `app` = the application or service being auth'd to\n\n"
            "Common gotchas:\n"
            "  - Mapping `username` to `user` (CIM expects `user`)\n"
            "  - Forgetting `EVAL-action` props.conf entry to normalise a "
            "vendor-specific status to success/failure\n"
            "  - Not adding `TAG=authentication` to the eventtype so the data model "
            "sees the events\n\n"
            "Validate with `| datamodel Authentication Authentication search | head 10 "
            "| table user, src, dest, action` — every row should populate cleanly."
        ),
        "tags": ["cim", "data-onboarding", "authentication"],
        "data_sources": ["Authentication"],
        "data_models": ["Authentication"],
    },
    {
        "name": "playbook-contain-compromised-aws-iam-key",
        "title": "Containment: compromised AWS IAM access key",
        "kind": "playbook-step",
        "summary": "Step-by-step containment when an AWS access key has been confirmed leaked or in attacker hands.",
        "response_guidance": (
            "Order matters — each step bounds the blast radius before the next:\n\n"
            "1. **Disable the access key** (not delete — preserves audit trail):\n"
            "   `aws iam update-access-key --access-key-id <ID> --status Inactive`\n\n"
            "2. **Pull every CloudTrail event for the key in the last 14 days.** This "
            "is the actor's full activity history. Look specifically for "
            "AssumeRole / CreateAccessKey / PutUserPolicy — those are persistence "
            "moves.\n\n"
            "3. **Revoke any sessions the key may have started.** If the key was used "
            "with sts:AssumeRole, revoke the role's sessions via "
            "`aws iam put-role-policy` with a Deny on the affected role.\n\n"
            "4. **Search for downstream credentials.** If the user had EC2 access, "
            "any instance metadata credentials may have been pulled. If they had "
            "Lambda access, check for inserted env vars.\n\n"
            "5. **Only after 1-4: notify and rotate.** Notify the credential owner, "
            "then issue new credentials. Reversing this order tips off the attacker."
        ),
        "tags": ["aws", "incident-response", "containment"],
        "data_sources": ["AWS CloudTrail"],
        "references": [
            {"label": "AWS docs — Disable access key",
             "url": "https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html"},
        ],
    },
    {
        "name": "reference-asset-priority-tiers-acme",
        "title": "Asset priority tiers — reference",
        "kind": "reference-article",
        "summary": "Reference: what an asset's priority field (critical/high/medium/low) means in a tuned ES install.",
        "response_guidance": (
            "Asset priority is the single most important field for risk-weighted "
            "alerting. A tuned ES install assigns:\n\n"
            "  - **critical** — Domain controllers, payment-processing hosts, source-"
            "control servers, CA servers, any host whose compromise = breach in itself.\n"
            "  - **high** — Production-tier web/app/db servers, jump hosts, "
            "Kubernetes control-plane nodes.\n"
            "  - **medium** — Internal-only services, non-production-tier prod, "
            "monitoring/observability hosts.\n"
            "  - **low** — Workstations, dev environments, lab subnets.\n\n"
            "An alert fires once per (rule_name, src) tuple per day at low priority; "
            "10x sooner at medium; immediately at high; and pages the on-call at "
            "critical. If a notable's asset priority is null, treat it as medium "
            "until the asset is properly categorised."
        ),
        "tags": ["asset-identity", "reference", "priority"],
    },
    {
        "name": "trackme-feed-health-dashboard-panel-recipe",
        "title": "TrackMe feed-health dashboard panel — exact SPL (use verbatim)",
        "kind": "reference-article",
        "summary": (
            "Canonical, copy-paste SPL for a TrackMe data-feed-health panel on a "
            "Simple XML dashboard in the calling app. Avoids the inputlookup / "
            "stats-wildcard / spath pitfalls."
        ),
        "response_guidance": (
            "To add a TrackMe data-feed-health panel to a dashboard for one or more "
            "indexes:\n\n"
            "1. Call `trackme_health_for_indexes(indexes=[...])` FIRST. Per index it "
            "returns `tracked` (bool), `status_counts` {green/orange/red}, `tenants`, "
            "`summary_index`, and ready-made `panel_spl_*` strings. Only add the panel "
            "when `tracked:true`; NEVER claim an index is unmonitored unless the tool "
            "returned `tracked:false` (TrackMe tracks `_internal` and other internal "
            "indexes fine).\n\n"
            "2. Use these EXACT SPL — substitute <summary_index> = the tool's "
            "`summary_index` (default `trackme_summary`) and <index> = the index name. "
            "Do NOT re-derive them. Do NOT use `| inputlookup trackme_*` (app-private to "
            "the `trackme` app — errors in the calling app). Do NOT add `*` wildcards to "
            "a `stats` rename — use `count AS total_feeds`, NOT `count(*) AS total_feeds` "
            "(that errors: 'number of wildcards do not match').\n\n"
            "- Health summary (single panel — counts + readable string): "
            "`index=<summary_index> object=<index>* object_state=* | stats "
            "latest(object_state) AS state by object | stats "
            "count(eval(state=\"green\")) AS green_feeds, count(eval(state=\"orange\")) "
            "AS orange_feeds, count(eval(state=\"red\")) AS red_feeds, count AS "
            "total_feeds | eval summary=green_feeds.\" green / \".orange_feeds.\" orange "
            "/ \".red_feeds.\" red (out of \".total_feeds.\" tracked feeds)\" | table "
            "summary, green_feeds, orange_feeds, red_feeds, total_feeds`\n"
            "- Trend: `index=<summary_index> object=<index>* object_state=* | timechart "
            "span=5m count by object_state`\n"
            "- Red-feeds detail table: `index=<summary_index> object=<index>* "
            "object_state=* | stats latest(object_state) AS state latest(anomaly_reason) "
            "AS anomaly_reason latest(priority) AS priority by object | where "
            "state=\"red\" | rename object AS entity | table entity priority "
            "anomaly_reason`\n\n"
            "Summary-index fields: `object` (=`<index>:<sourcetype>`), `object_state` "
            "(green/orange/red), `tenant_id`, `priority`, `anomaly_reason`. The "
            "`object_state=*` filter drops empty-state housekeeping events. This is a "
            "plain index search — cross-app safe, no KVStore / lookup / `| trackme` / "
            "spath needed."
        ),
        "vendor": "TrackMe",
        "product": "TrackMe",
        "tags": ["trackme", "dashboard", "feed-health", "data-availability"],
        "assigned_tools": ["trackme_health_for_indexes"],
    },
    {
        "name": "reuse-sse-escu-detections-federated",
        "title": "Reuse SSE / ESCU detections — don't write detection SPL from scratch",
        "kind": "playbook-step",
        "summary": (
            "Splunk Security Essentials (SSE) + ES Content Updates (ESCU) ship "
            "2000+ production detection searches. For any 'build a detection' / "
            "'what detections exist for <X>' / coverage-audit / threat-hunt "
            "request, START from a canonical detection via the SSE tools and adapt "
            "only the environment-specific parts (index/sourcetype/datamodel)."
        ),
        "response_guidance": (
            "Reuse canonical SSE/ESCU detections instead of authoring detection "
            "SPL from scratch. WORKFLOW (fetching this entry unlocks the SSE "
            "tools):\n\n"
            "1. `sse_check_prerequisites` — confirm SSE + DA-ESS-ContentUpdate "
            "(ESCU) are installed and visible. Gate everything on `ready=true`.\n\n"
            "2. `sse_list_content` — browse/filter the catalogue (card metadata "
            "only — fast, no SPL) by `usecase` / `category` / MITRE "
            "`tactic`+`technique` / `data_source`. Pick cards with "
            "`hasSearch=Yes`; note the card `id`.\n\n"
            "3. `sse_get_detection(id)` — returns the REAL detection SPL plus "
            "`macros`, `lookups`, `how_to_implement`, `known_false_positives`, "
            "MITRE mapping, `references`, and `runnable` + `dependency_note`.\n\n"
            "4. ADAPT to THIS environment — the canonical SPL is ~90% there; keep "
            "the detection LOGIC, swap only env-specific tokens:\n"
            "   - Replace the example `index=` / `sourcetype=` with the customer's "
            "actual ones (ground via `splunk_list_indexes` + the template's data "
            "inputs).\n"
            "   - CIM / data-model check (CRITICAL): many ESCU detections use "
            "`| tstats ... FROM datamodel=<X>` or `datamodel=<X>`, which needs the "
            "CIM app (`Splunk_SA_CIM`) installed AND the model "
            "accelerated/populated for those sourcetypes. If CIM is absent or the "
            "model isn't populated, the detection returns NOTHING as-is — either "
            "(a) rewrite to a raw `index=... sourcetype=... | ...` search mapping "
            "the CIM fields to the source's real field names, or (b) clearly flag "
            "the CIM dependency as a gap. NEVER present a datamodel detection as "
            "'runnable' when `dependency_note` says CIM/TAs are missing.\n"
            "   - Resolve referenced `macros`/`lookups`: ESCU macros live in "
            "DA-ESS-ContentUpdate; if one isn't resolvable in the calling app, "
            "inline its definition or note the dependency.\n\n"
            "5. VALIDATE the adapted SPL with `splunk_run_search` BEFORE "
            "persisting, then save via `splunk_create_saved_search` with a "
            "`description` citing the SSE/ESCU source (card name + id).\n\n"
            "Enrichment: `sse_enrich_id` / `sse_enrich_alert` add SSE's identity / "
            "alert context to results. DON'T hand-write a detection when a "
            "canonical one exists; DON'T claim a detection runs if its "
            "`dependency_note` lists missing ESCU/CIM/TA prerequisites."
        ),
        "vendor": "Splunk",
        "product": "Splunk Security Essentials",
        "tags": [
            "security-content", "sse", "escu", "detection-engineering",
            "federated-knowledge", "cim",
        ],
        "assigned_tools": [
            "sse_check_prerequisites", "sse_list_content", "sse_get_detection",
            "sse_enrich_id", "sse_enrich_alert",
        ],
    },
]


# ─────────────────────────────────────────────────────────────────────────
# v1.4.0 — Tier B overlay for the `conf-searchbnf` connector.
#
# ENRICHMENT ONLY. The authoritative syntax / availability comes from the LIVE
# searchbnf.conf read (Tier A). These notes add the good_for / common-mistakes /
# gotchas guidance Splunk's BNF does not ship. Keep the set SMALL and reviewed —
# patches over live truth, not a parallel command database. Keyed by exact_name
# = command name. `applies_when: always` merges even when the live BNF is rich
# (because the GUIDANCE is still useful); `bnf_thin_or_missing` merges only when
# the live stanza is terse. GLOBAL (DFLT/DFLT) — see KNOWLEDGE_LAYER.md.
# ─────────────────────────────────────────────────────────────────────────
COMMAND_NOTE_SEEDS = [
    {
        "name": "bin",
        "exact_name": "bin",
        "label": "bin (bucket / discretize)",
        "kind": "command-note",
        "applies_when": "always",
        "verified": "true",
        "source": "curated-shiptime",
        "good_for": [
            "Bucketing a continuous field (time or numeric) into ranges BEFORE a stats/chart so you can aggregate per bucket.",
        ],
        "common_mistakes": [
            "Using `bin` on its own and expecting aggregation — bin only LABELS each row's bucket; you still need a following `stats`/`chart`/`timechart` to aggregate.",
            "Confusing `span` (the size/width of each bucket, e.g. span=1h or span=10) with `bins` (the TARGET NUMBER of buckets). Setting both is contradictory.",
        ],
        "gotchas": [
            "On `_time`, `| timechart` already bins internally — only reach for `bin _time` when you need the bucketed _time as a normal field for a later `stats by _time`.",
        ],
        "notes": "Alias: `bucket`, `discretize`. `bin span=1h _time | stats avg(x) by _time` is the canonical pattern.",
        "tags": ["transforming", "bucketing", "time"],
    },
    {
        "name": "stats",
        "exact_name": "stats",
        "label": "stats",
        "kind": "command-note",
        "applies_when": "always",
        "verified": "true",
        "source": "curated-shiptime",
        "good_for": [
            "The default aggregation command — counts, sums, averages, distinct counts, value lists, grouped by zero or more BY fields.",
        ],
        "common_mistakes": [
            "`count` vs `dc(field)` (distinct count) vs `count(field)` (non-null count of that field) are three different things — pick deliberately.",
            "A `stats` rename cannot mix a `*` wildcard with a single output name (e.g. `count(*) AS total` errors 'number of wildcards do not match'). Use an explicit field: `count AS total` or `dc(object) AS total`.",
            "Forgetting that `stats` DROPS every field not named in the agg or the BY clause — `_raw`, `_time` and others are gone afterward unless you carry them with `values()`/`latest()`.",
        ],
        "gotchas": [
            "`stats` is far cheaper than `transaction` and `join` for grouping — prefer it. For 'first/last per group' use `stats latest(...)/earliest(...) by key` not `dedup`+`sort`.",
        ],
        "notes": "`stats count` (no BY) ALWAYS returns exactly one row (count=0 when empty) — use that shape for single-value panels that must show 0 rather than 'No results'.",
        "tags": ["transforming", "aggregation"],
    },
    {
        "name": "rex",
        "exact_name": "rex",
        "label": "rex (regex field extraction)",
        "kind": "command-note",
        "applies_when": "always",
        "verified": "true",
        "source": "curated-shiptime",
        "good_for": [
            "Ad-hoc, search-time field extraction with a named-capture regex; or `mode=sed` for substitution/redaction.",
        ],
        "common_mistakes": [
            "Forgetting `field=...` — `rex` defaults to `field=_raw`. To extract from an already-extracted field you MUST set `field=<thatfield>`.",
            "Naming a capture group with a hyphen or a reserved name — use `(?<name>...)` with `[A-Za-z0-9_]` names.",
            "Assuming PCRE lookbehind/recursion — Splunk's regex engine rejects some constructs; test on a sample first.",
        ],
        "gotchas": [
            "`rex` runs at search time on every matching event — heavy regex over large result sets is slow; extract once early and reuse, or define a permanent field extraction for repeated use.",
            "`max_match=0` returns ALL matches as a multivalue field; default is 1 (first match only).",
        ],
        "notes": "Inside Simple XML `<query>`, the builder escapes `<`/`>`/quotes for you — pass RAW regex like `(?<EventID>\\\\d+)`, never `&lt;`.",
        "tags": ["streaming", "extraction", "regex"],
    },
    {
        "name": "transaction",
        "exact_name": "transaction",
        "label": "transaction",
        "kind": "command-note",
        "applies_when": "always",
        "verified": "true",
        "source": "curated-shiptime",
        "good_for": [
            "Grouping a sequence of related events into one multivalue 'transaction' by shared field(s) plus time/ordering constraints (maxspan, maxpause, startswith/endswith).",
        ],
        "common_mistakes": [
            "Reaching for `transaction` when `stats ... by <key>` would do — `stats` is dramatically cheaper and parallelisable. Only use `transaction` when you genuinely need ordering, maxpause/maxspan windows, or startswith/endswith boundaries.",
        ],
        "gotchas": [
            "`transaction` is memory-bound and NOT distributed across indexers the way `stats` is — it can blow up on high-cardinality keys or long windows. Always bound it with `maxspan`/`maxopenevents`.",
        ],
        "modern_replacement": "",
        "notes": "Rule of thumb: if you only need counts/first/last/duration per key, use `stats range(_time) AS duration, count BY key` instead.",
        "tags": ["transforming", "correlation", "performance"],
    },
    {
        "name": "tstats",
        "exact_name": "tstats",
        "label": "tstats (accelerated stats)",
        "kind": "command-note",
        "applies_when": "always",
        "verified": "true",
        "source": "curated-shiptime",
        "good_for": [
            "High-performance stats over INDEXED fields or an ACCELERATED data model / tsidx namespace — orders of magnitude faster than raw `stats` for the supported shapes.",
        ],
        "common_mistakes": [
            "Using `tstats` over fields that are NOT indexed / not in the data model — it only sees indexed fields, `_time`, and data-model fields, NOT search-time-extracted fields.",
            "Omitting `summariesonly=t` when you intend to read ONLY accelerated summaries — without it, tstats falls back to raw scanning for gaps and can be slow/inconsistent.",
            "Wrong clause order — `tstats` is a GENERATING command: it must be FIRST in the pipeline (`| tstats ...`), with `FROM datamodel=...` / `WHERE ...` / `BY ...` in that grammar.",
        ],
        "gotchas": [
            "Field references use the data model's dotted path (e.g. `Authentication.action`); `BY _time span=1h` for trends.",
        ],
        "notes": "For an accelerated DM: `| tstats summariesonly=t count FROM datamodel=Authentication WHERE nodename=Authentication.Failed_Authentication BY _time span=1h`.",
        "tags": ["generating", "performance", "datamodel"],
    },
    {
        "name": "eval",
        "exact_name": "eval",
        "label": "eval",
        "kind": "command-note",
        "applies_when": "bnf_thin_or_missing",
        "verified": "true",
        "source": "curated-shiptime",
        "good_for": [
            "Computing or rewriting a field per event with functions (if/case/coalesce/strftime/round/mvjoin/...).",
        ],
        "common_mistakes": [
            "Quoting confusion: field names are bare or in single quotes when they contain special chars (`'My Field(s)'`); string LITERALS use double quotes (\"text\"). Mixing them silently misbehaves.",
            "Putting a bare `field=*` comparison in `where`/`eval` — that's invalid; use the base `search` command for `field=*`, and `==`/comparison operators inside eval expressions.",
        ],
        "gotchas": [
            "`eval` creates ONE field per statement; chain with commas: `| eval a=1, b=a+1`. A null operand usually makes the whole expression null — guard with `coalesce()`/`isnull()`.",
        ],
        "notes": "For 'show 0 not blank' single-value panels, `eval` after a `stats count` is unnecessary — `stats count` already returns a 0 row.",
        "tags": ["streaming", "compute"],
    },
]


# ─────────────────────────────────────────────────────────────────────────
# v1.4.0 — Tier 1 shipped overlay for the `conf-visualizations` connector.
# Distilled-offline-under-review (or hand-authored) viz SEMANTICS the platform
# REST never gives. Merged at fetch time onto the LIVE installed-viz read +
# demo-dashboard harvest; live harvest wins on conflict. GLOBAL (DFLT/DFLT).
# Versioned items: source_id = <app>.<viz>@<version>; exact_name = <app>.<viz>.
# Seeded set starts small and reviewed; the build-time Splunkbase generator
# (VISUALIZATION_KNOWLEDGE_SPEC.md §4) scales this later under a human review
# gate. The first item is Region Chart Viz — the spec's worked example, the
# canonical "useless from REST alone" viz: its `regions` band is a data-driven
# SPL column, not a config option, which only this overlay explains.
# ─────────────────────────────────────────────────────────────────────────
VIZ_KNOWLEDGE_SEEDS = [
    {
        "name": "region_chart_viz.region_chart_viz@1.1.12",
        "source_id": "region_chart_viz.region_chart_viz@1.1.12",
        "exact_name": "region_chart_viz.region_chart_viz",
        "label": "Region Chart Viz",
        "kind": "visualization-spec",
        "knowledge_version": "1.1.12",
        "splunkbase_id": 4911,
        "splunkbase_url": "https://splunkbase.splunk.com/app/4911",
        "distilled_at": "2026-06-06",
        "verified": "true",
        "source": "curated-shiptime",
        "overlay": {
            "good_for": [
                "time-series with threshold / SLA bands drawn behind the line (e.g. avg latency with red/amber/green bands)",
            ],
            "avoid_when": [
                "a single flat series with no thresholds",
                "categorical-only data (no continuous _time axis)",
            ],
            "render_modes": [
                "Lighter & dashed — historical vs current comparison",
                "Coloured — when the series are peers (e.g. CPU of 3 servers in a cluster)",
            ],
            "property_meanings": {
                "regions": "A COLUMN you compute in SPL (NOT a config option). Its value per row defines the coloured band behind the chart. A single colour name (e.g. \"red\") = one solid region. A comma list (e.g. \"green,1000,orange,1500,red\") = stacked threshold bands from bottom to top. A leading-underscore form (e.g. \"_1000,Warningorange,1500_Criticalred\") names the bands.",
            },
            "gotchas": [
                "Requires continuous _time; sparse data breaks the band rendering.",
                "Region overlays apply to the PRIMARY series only.",
                "The 'regions' value is data-driven per row — set it with eval, not in the format menu.",
            ],
        },
        "data_contract": {
            "row_shape": "timechart",
            "required_columns": ["_time", "<numeric series>"],
            "optional_columns": ["regions"],
            "min_fields": 2,
            "example_spl": "index=foo | timechart avg(alert_value) as avg | eval regions=\"green,1000,orange,1500,red\"",
            "search_fragment": "| timechart avg(alert_value) | eval regions = \"red\"",
        },
        "declared_properties": [
            {"name": "regionOpacity", "fqn": "display.visualizations.custom.region_chart_viz.region_chart_viz.regionOpacity", "type": "float", "default": 0.5, "required": False},
        ],
        "xml_emission": {
            "charting_chart_value": "region_chart_viz.region_chart_viz",
            "option_template": [
                "<option name=\"charting.chart\">region_chart_viz.region_chart_viz</option>",
            ],
        },
        "tags": ["region-chart", "thresholds", "sla", "bands", "timechart"],
    },
]
