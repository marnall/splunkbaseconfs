# TA-guardrails

Splunk Technology Add-on for AI guardrail and content safety events.

**Version 0.1.1** · MIT · Splunk Enterprise 9.1+ and Splunk Cloud · CIM 5.x

---

## Why

Guardrail systems already emit exactly what a SIEM wants: an attempted action, a
policy that fired, a category, a severity, an identity, a timestamp. Today that
data stays inside the AI platform team's tooling and the SOC never sees it.

Which means nobody is alerting on the fact that one contractor account attempted
four hundred prompt injections against the legal assistant this week — even
though every one of them was detected and blocked, and the evidence is sitting in
a log somewhere.

This add-on normalizes guardrail events from seven providers into one
CIM-compliant schema so that those events can be correlated with the identity,
DLP, and insider-threat content already running in Enterprise Security.

## Supported sources

| Provider | Sourcetype |
|---|---|
| AWS Bedrock Guardrails | `guardrail:bedrock` |
| Azure AI Content Safety | `guardrail:azure:contentsafety` |
| Azure OpenAI content filter | `guardrail:azure:openai` |
| Google Vertex AI safety ratings | `guardrail:vertex` |
| Meta Llama Guard | `guardrail:llamaguard` |
| Lakera Guard | `guardrail:lakera` |
| NVIDIA NeMo Guardrails | `guardrail:nemo` |

The normalized schema is specified in [docs/SCHEMA.md](docs/SCHEMA.md).

## Install

Search heads and indexers need this add-on for parsing and search-time knowledge.
Forwarders only need it if you are collecting self-hosted guardrail logs from
files.

Create the index:

```ini
[guardrails]
homePath   = $SPLUNK_DB/guardrails/db
coldPath   = $SPLUNK_DB/guardrails/colddb
thawedPath = $SPLUNK_DB/guardrails/thaweddb
```

### Getting the data in

**Most guardrail telemetry already arrives through an add-on you have.** Do not
enable inputs here for those sources — set the sourcetype on the existing input
instead.

- **Bedrock Guardrails** ride inside model invocation logs. Enable model
  invocation logging on the guardrail, route to CloudWatch Logs or S3, and
  collect with the Splunk Add-on for AWS. Override the sourcetype to
  `guardrail:bedrock`.
- **Azure Content Safety and Azure OpenAI** emit diagnostic logs to Azure
  Monitor. Route through Event Hub and collect with the Splunk Add-on for
  Microsoft Cloud Services, setting sourcetype accordingly.
- **Vertex AI** safety ratings appear in Cloud Logging. Collect with the Splunk
  Add-on for Google Cloud Platform.
- **Llama Guard, Lakera, NeMo** are typically self-hosted. Either enable the file
  monitors in `local/inputs.conf`, or POST directly to HEC with the sourcetype
  set on the token.

Note that Bedrock model invocation logging is **disabled by default** and must be
turned on before any of this produces data.

## Searches

Every adversarial attempt, all providers, one query:

```
`guardrail_attacks`
```

Repeat offenders over a week:

```
| `guardrail_top_offenders(7d)`
```

Bypass reconnaissance — one identity probing many distinct categories in a short
window, which looks like someone mapping the guardrail rather than a confused
user:

```
| `guardrail_bypass_recon`
```

PII egress attempts. The filter caught it; the attempt is still the signal:

```
| `guardrail_pii_attempts`
```

Guardrail volume collapsing while traffic continues — the signature of a
disabled or misconfigured policy. Absence of evidence is the alert, so schedule
this rather than watching it on a panel:

```
| `guardrail_silent_failure`
```

Accurate per-category counts across providers:

```
| `guardrail_findings`
| stats count BY category, category_family, guardrail_vendor
```

## Evaluations vs findings

One guardrail invocation is **one evaluation** and produces **zero or more
findings**. An evaluation scoring four content categories and matching two PII
entities is one evaluation and six findings.

Event-level fields describe the evaluation as a whole — did anything block, what
was the most severe category. They are single-valued and safe to accelerate in a
datamodel.

The `guardrail_findings` macro expands the nested arrays into one row per
finding. **Use it whenever you are counting.** Counting events answers "how much
traffic did we screen"; counting findings answers "what did we find". Alerting on
the wrong one produces either false confidence or false alarm.

The reason for the split is practical: Splunk's automatic lookups behave
inconsistently across versions when the input field is multivalue, so the
guaranteed-correct path applies lookups after explosion.

## Testing

`bin/gen_test_data.py` generates a 24-hour scenario across all seven providers
with three planted patterns the shipped macros are supposed to catch: bypass
reconnaissance, persistent injection from one account, and a provider going
silent. If a detection does not fire against this data, the detection is broken.

```
# inspect
python3 bin/gen_test_data.py --stdout

# write newline-delimited JSON, one file per sourcetype
python3 bin/gen_test_data.py --out /tmp/gr_test

# push straight into Splunk
python3 bin/gen_test_data.py --hec https://localhost:8088 --token <TOKEN> --insecure
```

Then confirm:

```
`guardrail_events` | stats count BY guardrail_vendor, category
| `guardrail_top_offenders(24h)`
| `guardrail_bypass_recon`
```

## Identity normalization

Providers carry the calling principal in three shapes: an IAM role ARN, a UPN
email, and a bare service account name. Grouping on `user` therefore splits one
actor into several rows, and each slice can fall below an alert threshold — a
sustained attack across three providers looks like three quiet ones.

Use `actor` for any grouping or alerting. It reduces all three shapes to a
common key. `user` is preserved unchanged for provenance, and `user_domain`
carries the email domain where one exists, which is useful for separating
contractors from employees.

## Privacy

Flagged content is, by construction, the most sensitive text in the system — it
is the material that triggered the finding. **This add-on does not index it.**
Categories, scores, verdicts, and PII entity *types* are kept; matched strings,
prompt bodies, and completions are stripped at index time by `SEDCMD` rules.

If you need content-level investigation, store it separately under different
access controls and join on `request_id`. Do not remove the redaction so that a
whole SOC can read flagged prompts.

## CIM

Events map to the **Intrusion Detection** datamodel with `ids_type=application`,
so ES risk rules, notable events, and existing IDS content work without
modification.

One documented gap: CIM Intrusion Detection has no field for direction, because
network IDS assumes inbound traffic. Guardrails evaluate both input and output,
and the distinction matters — an injection attempt inbound is a security event
for the SOC, while unsafe content outbound is a safety event for the AI platform
team. `direction` is carried as a non-CIM field.

## Limitations

**The vendor mappings were built against published schemas, not captured
production records.** Providers change log shapes between API versions. Validate
against your own data before relying on this for alerting, and file issues where
the shapes differ.

**Unmapped categories resolve to `unknown` rather than being dropped.** A rising
`unknown` count means a provider added categories. Monitor it:

```
`guardrail_events` category=unknown
| stats count BY guardrail_vendor, vendor_category
```

**Severity normalization is lossy by design.** Coarse vendor bands are placed at
the middle of their range so thresholds behave consistently across providers.
Where a provider gives a float score, prefer it over `guardrail_score` for
precision work.

**No detection content ships here.** This is a normalization add-on. Correlation
searches and risk rules belong in a separate security app.

## Extending

Adding a provider takes four steps, documented in
[docs/SCHEMA.md §10](docs/SCHEMA.md). The last one — running the mapping against
a real record and confirming every value resolves — is the one that matters.
`bin/build_lookups.py` regenerates the lookup CSVs from a single source of truth.
