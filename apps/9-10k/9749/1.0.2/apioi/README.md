# apioi — API Operational Intelligence

Dashboards, alerts and a morning report for **Amazon API Gateway** access
logs and **CloudTrail**: traffic, latency, errors, callers, user sessions,
deploy audit and the health of the ingestion pipeline itself.

Source, issues and the AWS ingestion pipeline (CloudWatch Logs → Firehose →
HEC, with an overnight replayer for anything Firehose could not deliver):
[github.com/earth2recon/e2r-apioi](https://github.com/earth2recon/e2r-apioi).

## What it expects

| | |
|---|---|
| Access logs | API Gateway JSON access logs, one event per request, with the fields below as **indexed** fields (the repo's Firehose processor sets them; `props.conf` also extracts them from `_raw` at search time). |
| CloudTrail | Ingested by the [Splunk Add-on for AWS](https://splunkbase.splunk.com/app/1876) (`aws:cloudtrail`). |
| Replayer | Optional — the repo's overnight replayer logs one JSON event per run; dashboard 10 reads it. |

## Configuration — `macros.conf`

The app never names an index or a sourcetype outside these macros. Set
them once (Settings → Advanced search → Search macros, or a `local/macros.conf`)
and every dashboard, alert and report follows:

| Macro | Default | |
|---|---|---|
| `apigw_access` | `index=apigw sourcetype=e2r:apigw:access` | the access-log events |
| `cloudtrail` | `index=cloudtrail sourcetype=aws:cloudtrail` | CloudTrail |
| `replayer` | `index=apioi sourcetype=e2r:apioi:replayer` | replayer run log |
| `apioi_indexes` / `apioi_index_names` | the three indexes above | ingestion dashboard |
| `licence_alert_gb` | `8` | daily volume alert threshold (≈80 % of your licence) |

`indexes.conf` creates `apigw`, `cloudtrail` and `apioi` with no size caps;
set caps in `system/local` (AppInspect does not allow them in a package).

**Lookup `api_keys.csv`** maps API Gateway key ids to an app name and a
channel (`portal`, `app`, `sandbox`). The shipped file is a template — fill
in your key ids (`aws apigateway get-api-keys`). Dashboard 4 shows only
`channel=portal` traffic; the *App* dropdown on the traffic dashboards uses
the names.

## Fields

`apiName` is the API (in the reference pipeline, the repository that owns
it); `service` is the stage underneath it. Every access-log event carries:

`apiName service stage domain api method resourcePath path status statusClass isError
responseLatencyMs integrationLatencyMs integrationStatus authorizerStatus
authorizerLatencyMs sub email group actingAs sourceIp userAgent apiKeyId
errorType checkpoint requestId waf`

The whole record stays in `_raw` as JSON for everything else.

## Dashboards

1. AWS Audit (CloudTrail) · 2. CI/CD Audit · 3. All Microservices ·
4. API Portal · 5. API Automated QA · 6. Splunk HEC Ingestion Status ·
7. Index Daily Ingestion · 8. Find Requests · 9. User Activities ·
10. Pipeline Health

## Alerts

5xx spike · authorizer refusal burst · replayer quarantined a batch ·
overnight not caught up by 08:00 · licence usage above threshold; plus a
morning summary report. Each has the Splunk Secure Gateway mobile action
enabled — it does nothing until a device is paired. Cron schedules assume
the server's local time zone.

## Regenerating the dashboards (repo)

The views are generated from `scripts/gen-dashboards.py` so the traffic
dashboards share one panel library. Edit the script, run it, commit both;
the *Validate* workflow fails if they drift.
