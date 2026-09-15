# Axiom for Splunk

This Splunk app connects the datasets your team keeps in Axiom to the Splunk searches and workflows your team already uses.

It is not trying to replace Splunk. It lets Splunk users discover Axiom datasets, run Axiom-backed searches, push common aggregations down into Axiom, look up Axiom context for Splunk events, and then keep using normal SPL for the final shaping, dashboards, alerts, and analysis.

## Operational Model

This app is a query bridge, not an index replication tool. Axiom remains the system that stores and queries Axiom datasets. Splunk remains the system where users compose investigations, shape results, run dashboards, trigger alerts, and connect output to existing operational workflows.

Key behaviors to understand before writing searches:

| Area | Behavior |
| --- | --- |
| Authentication | The app reads a shared Axiom API token from Splunk `storage/passwords`. Dataset visibility and query permissions come from that token. |
| Time range | Axiom query commands use the Splunk dispatch time range by default. The Splunk time picker normally controls the Axiom API `startTime` and `endTime`. Command options can override either boundary. |
| Execution | Filtering, projection, and aggregation run in Axiom. Splunk receives tabular rows and continues with normal SPL. |
| Command shape | `axsearch`, `axstats`, and `axtimechart` expose a Splunk-aligned surface. `axquery` runs raw APL for cases that need the full Axiom language. |
| Pipeline placement | Most commands are generating commands and must start the search. `axlookup` is streaming and runs after a base Splunk search. |
| Field conventions | Dataset-scoped generated events include `axiom_dataset`. Fields added by `axlookup` are prefixed and normalized to Splunk-friendly names. |
| Inspection | Use `explain=true` to inspect generated APL and resolved time ranges before querying Axiom. Use `debug=true` on `axquery` for runtime logs. |

## How To Think About It

Use Axiom for the work that should happen close to Axiom data:

- discovering datasets and fields
- sampling recent events
- filtering large Axiom datasets before results enter Splunk
- aggregating large event sets into small result tables
- looking up latest Axiom context for existing Splunk events
- running full APL when you need the whole Axiom language

Use Splunk for the work your team already does well there:

- joining this output into existing SPL workflows
- table, chart, stats, and dashboard presentation
- saved searches and alerts
- operational workflows that already live in Splunk

The best searches usually push the expensive part into Axiom, return a focused result set, and then use SPL for presentation.

## Command Map

| Command | Use it for | Pipeline type |
| --- | --- | --- |
| `axdatasets` | List datasets visible to the configured Axiom token. | Generating |
| `axfields` | List fields in one Axiom dataset. | Generating |
| `axsample` | Fetch recent sample events without writing APL. | Generating |
| `axsearch` | Search one Axiom dataset with Splunk-like `q`, `search`, and `where` options. | Generating |
| `axstats` | Push `stats`-style aggregations into Axiom. | Generating |
| `axtimechart` | Push time-bucketed aggregations into Axiom. | Generating (reporting) |
| `axlookup` | Look up Axiom context and add selected fields to existing Splunk events. | Streaming |
| `axquery` | Run raw APL for full control. | Generating |

Generating commands must be the first command in a Splunk search. `axlookup` is a streaming command, so it appears later in an SPL pipeline. `axtimechart` generates reporting output, so its results are a chartable table rather than events.

All commands return Axiom fields as real Splunk fields. See Field And Workflow Conventions.

## Quick Start For Users

1. Open the Axiom app in Splunk.
2. Complete setup with an Axiom API token that can read the datasets you want to query.
3. Find the datasets available to that token:

```spl
| axdatasets
| table name, kind, retentionDays
| sort name
```

4. Inspect fields in a dataset:

```spl
| axfields dataset="app-logs"
| table name, type, unit
| sort name
```

5. Sample events:

```spl
| axsample dataset="app-logs" fields="service,status,message" limit=20
```

6. Search with Splunk-like syntax:

```spl
| axsearch dataset="app-logs" q="status>=500 service=checkout" fields="service,status,message" limit=100
| table _time, service, status, message
```

7. Aggregate in Axiom, then present in Splunk:

```spl
| axstats dataset="app-logs" q="status>=500" stats="count as errors" by="service" limit=100
| sort -errors
```

## Choosing The Right Command

Start with the most specific command that matches the job.

Use `axsample` when you are learning a dataset:

```spl
| axsample dataset="payments" limit=10 fields="customer_id,amount,status"
```

Use `axsearch` for event searches where you want Splunk-like syntax and event-shaped rows back:

```spl
| axsearch dataset="payments" q="status=failed amount>1000" fields="customer_id,amount,status,reason" limit=500
```

Use `axstats` when the next thing you want is a grouped table:

```spl
| axstats dataset="payments" q="status=failed" stats="count as failures, sum(amount) as failed_amount" by="reason"
| sort -failures
```

Use `axtimechart` when the next thing you want is a time series. It is a reporting
command, so the results are already a chartable table and the Visualization tab works
without any further piping:

```spl
| axtimechart dataset="payments" q="status=failed" span=15m agg="count as failures" by="reason" limit=1000
```

Use `axlookup` when the base events are already in Splunk and Axiom has useful context to look up:

```spl
index=main service=api
| axlookup dataset="deployments" on="service=service.name" fields="version,owner,team"
| table _time, service, axiom_version, axiom_owner, axiom_team
```

For Axiom fields with dots or other punctuation, `axlookup` writes Splunk-friendly output names:

```spl
index=main service=api
| axlookup dataset="otel-demo-logs" on="service=service.name" fields="service.version,resource.k8s.deployment.name"
| table _time, service, axiom_service_version, axiom_resource_k8s_deployment_name, axiom_lookup_dataset
```

Use `axquery` when the command-specific surface is not enough and you want raw APL:

```spl
| axquery apl="['app-logs'] | where status >= 500 | summarize errors=count() by service, bin(_time, 1h) | sort by _time asc"
| table _time, service, errors
```

## Time Ranges

Commands that query Axiom data use the Splunk dispatch time range by default. In practice, the Splunk time picker, saved search schedule, or dispatch earliest/latest values become the Axiom API `startTime` and `endTime`. A user who runs a search for "Last 15 minutes" should get the same 15-minute Axiom window without adding command-specific time arguments.

This applies to `axsample`, `axsearch`, `axstats`, `axtimechart`, `axlookup`, and `axquery`. `axdatasets` and `axfields` do not query event time ranges.

Time resolution is per boundary:

| Boundary | First choice | Second choice | Default |
| --- | --- | --- | --- |
| Start | `startTime` | `earliest` | Splunk dispatch earliest time |
| End | `endTime` | `latest` | Splunk dispatch latest time |

If a boundary still cannot be resolved, that side is omitted from the Axiom request. Splunk "All time" commonly arrives as a non-positive dispatch value, so the app treats it as unbounded rather than sending `1970-01-01T00:00:00Z`.

Use explicit options when the Axiom query should intentionally differ from the current Splunk search range:

```spl
| axsearch dataset="app-logs" q="error" startTime="-24h" endTime="now" limit=100
```

The Splunk-style aliases are useful in saved searches or when you want the command invocation to read like native SPL:

```spl
| axquery apl="['app-logs'] | where status >= 500 | sort by _time desc | limit 1000" earliest="-7d@d" latest="@d"
```

Supported time inputs:

- RFC3339 UTC, such as `2026-07-02T12:00:00Z` or `2026-07-02T12:00:00.123456Z`
- Splunk-style relative time, such as `-15m`, `-24h`, `-7d@d`, `@d`, or `+1h`
- `now`

Relative inputs are resolved on the Splunk search head at command runtime and normalized to UTC before being sent to Axiom. If an exact boundary matters, use explicit RFC3339 UTC.

For raw APL in `axquery`, the command-level time window is still sent to the Axiom API. If the APL also contains `_time` predicates, both constraints apply. Prefer one clear source of truth unless you are deliberately narrowing a wider dispatch range inside the query.

For `axlookup`, the time range controls the Axiom lookup dataset, not the already-returned Splunk events. By default, the same Splunk dispatch window applies to both the upstream SPL and the Axiom lookup. Override the lookup window when your context data lives outside the base search window.

To inspect the resolved range without querying Axiom, use `explain=true` on `axsearch`, `axstats`, or `axtimechart`:

```spl
| axsearch dataset="app-logs" q="status>=500" explain=true
| table compiled_apl, startTime, endTime
```

## Field And Workflow Conventions

Every command returns Axiom fields as real Splunk fields. You do **not** need to append
`| spath` to reach them:

```spl
| axsearch dataset="app-logs" limit=10
| table _time service.name severity_text body
```

Nested Axiom objects are flattened to dotted field names, so `attributes.http.method` is
addressable directly, and arrays arrive as Splunk multivalue fields. This matches what
`| spath` used to produce, so existing searches that still call it keep working.

Commands other than `axtimechart` also keep the original row in `_raw` as JSON, so the
Events tab still shows the underlying Axiom record. `axtimechart` is a reporting command
and returns a clean stats table with no `_raw` or event metadata columns.

The app adds a small amount of metadata so Axiom-backed results can participate in normal Splunk investigation workflows:

- `axsample`, `axsearch`, `axstats`, and `axtimechart` add `axiom_dataset` to each returned event.
- `axlookup` adds `axiom_lookup_dataset` to enriched events and sets `axiom_dataset` when the event does not already have one.
- `axquery` runs arbitrary APL, so it cannot reliably infer one dataset. Add `| eval axiom_dataset="<dataset>"` after `axquery` when you want workflow actions on raw APL results.

`axlookup` output fields are normalized after the prefix is applied. The default prefix is `axiom_`, and punctuation in Axiom field names becomes `_`:

| Axiom field | Default Splunk field |
| --- | --- |
| `service.version` | `axiom_service_version` |
| `resource.k8s.deployment.name` | `axiom_resource_k8s_deployment_name` |
| `trace-id` | `axiom_trace_id` |

If two selected Axiom fields normalize to the same Splunk field name, the later field receives a numeric suffix such as `_2`.

The app also ships Splunk workflow actions. When an event has `axiom_dataset` plus a supported field, the event menu can launch a focused Axiom search for traces, spans, services, or Kubernetes deployments. The action preserves the current Splunk search time range and opens the search in the Axiom app.

## Splunk-Like `q` Syntax

`axsearch`, `axstats`, and `axtimechart` support a constrained Splunk-like `q` option that compiles to APL search syntax.

Supported patterns include:

```spl
q="error timeout"
q="error OR timeout"
q="error NOT debug"
q="(error OR timeout) service=api"
q="status>=500"
q="service=checkout"
q="service!=checkout"
q="trace_id=*"
q="service IN (api, worker)"
q="service NOT IN (api, worker)"
q="message:timeout*"
```

Use `where` on `axsearch`, or use `axquery`, when you need an APL predicate that is outside this supported subset.

Preview generated APL without querying Axiom:

```spl
| axsearch dataset="app-logs" q="status>=500 service=api" explain=true
| table compiled_apl
```

## Where To Learn More

This README and the in-app Documentation page explain how to use the Splunk app. Use the Axiom docs when you want to go deeper into APL itself:

- [APL introduction](https://axiom.co/docs/apl/introduction): learn the structure of APL queries, datasets, pipes, tabular operators, scalar functions, and aggregation functions.
- [Sample queries](https://axiom.co/docs/apl/tutorial): browse practical APL examples you can adapt into `axquery` or `where`.
- [Splunk SPL to APL cheat sheet](https://axiom.co/docs/apl/guides/splunk-cheat-sheet): translate familiar SPL patterns into APL when the app's SPL-like commands are not enough.
- [Summarize operator](https://axiom.co/docs/apl/tabular-operators/summarize-operator): understand the APL operator behind `axstats` and `axtimechart`.
- [Aggregation functions](https://axiom.co/docs/apl/aggregation-function/statistical-functions): learn the broader aggregation catalog. `axstats` supports the common subset documented below; use `axquery` for APL aggregations outside that subset.
- [Project fields with `project-keep`](https://axiom.co/docs/apl/tabular-operators/project-keep-operator): learn the APL field-selection operator behind `fields=...`.
- [Axiom API tokens](https://axiom.co/docs/reference/tokens): understand token permissions and dataset access.
- [Axiom datasets](https://axiom.co/docs/reference/datasets): understand how Axiom organizes event data.

For Splunk command placement, see Splunk's [command types](https://help.splunk.com/en/splunk-enterprise/search/spl-search-reference/10.4/quick-reference/command-types) reference. In this app, every command except `axlookup` is generating.

## Command Reference

### `axdatasets`

List datasets visible to the configured Axiom token.

```spl
| axdatasets
| table id, name, kind, retentionDays
| sort name
```

Options:

| Option | Required | Description |
| --- | --- | --- |
| `tokenName` | No | Stored Axiom token name. Defaults to `axiom_token`. |
| `mgmtPort` | No | Splunk management port override. Normally leave unset. |

### `axfields`

List fields for one Axiom dataset.

```spl
| axfields dataset="app-logs"
| table name, type, unit
| sort name
```

Options:

| Option | Required | Description |
| --- | --- | --- |
| `dataset` | Yes | Axiom dataset ID. |
| `tokenName` | No | Stored Axiom token name. Defaults to `axiom_token`. |
| `mgmtPort` | No | Splunk management port override. Normally leave unset. |

### `axsample`

Fetch recent events from one dataset without writing APL.

```spl
| axsample dataset="app-logs" fields="service,status,message" limit=20
```

Options:

| Option | Required | Description |
| --- | --- | --- |
| `dataset` | Yes | Axiom dataset ID. |
| `limit` | No | Maximum sample events. Defaults to `20`. |
| `fields` | No | Comma-separated fields to keep. `_time` is preserved automatically. |
| `startTime`, `endTime` | No | Override the Axiom query time range. Otherwise the Splunk dispatch range is used when available. |
| `earliest`, `latest` | No | Splunk-style aliases for `startTime` and `endTime`. |
| `tokenName`, `mgmtPort` | No | Connection overrides. |

### `axsearch`

Search one Axiom dataset and return event-shaped rows.

```spl
| axsearch dataset="app-logs" q="status>=500 service=checkout" fields="service,status,message" limit=100
```

Options:

| Option | Required | Description |
| --- | --- | --- |
| `dataset` | Yes | Axiom dataset ID. |
| `q` | No | Splunk-like query expression compiled to APL search syntax. |
| `search` | No | Text search string compiled to APL `search`. |
| `where` | No | Raw APL predicate for structured filtering. |
| `fields` | No | Comma-separated fields to keep. `_time` is preserved automatically. |
| `sort` | No | APL sort expression. Defaults to `_time desc`. |
| `limit` | No | Maximum events returned. Defaults to `100`. |
| `explain` | No | Return compiled APL without querying Axiom. |
| `startTime`, `endTime`, `earliest`, `latest` | No | Time controls. See Time Ranges for precedence and default behavior. |
| `tokenName`, `mgmtPort` | No | Connection overrides. |

### `axstats`

Push grouped aggregations into Axiom.

```spl
| axstats dataset="app-logs" q="status>=500" stats="count as errors, avg(duration_ms) as avg_duration" by="service" limit=100
```

Supported aggregation functions:

- `count` or `count()`
- `sum(field)`
- `avg(field)`
- `min(field)`
- `max(field)`
- `dcount(field)` or `dc(field)`
- `stdev(field)`
- `variance(field)`
- `percentile(field, pct)`, `perc(field, pct)`, or `p95(field)` style shorthand

Options:

| Option | Required | Description |
| --- | --- | --- |
| `dataset` | Yes | Axiom dataset ID. |
| `q` | No | Splunk-like query expression compiled to APL search syntax. |
| `stats` | No | Aggregation list. Defaults to `count`. |
| `by` | No | Comma-separated group-by fields. |
| `limit` | No | Maximum grouped rows when `by` is used. Defaults to `1000`. |
| `explain` | No | Return compiled APL without querying Axiom. |
| `startTime`, `endTime`, `earliest`, `latest` | No | Time controls. See Time Ranges for precedence and default behavior. |
| `tokenName`, `mgmtPort` | No | Connection overrides. |

### `axtimechart`

Push time-bucketed aggregations into Axiom and return row-oriented time series data.

This is a reporting command: the result is a stats table with `_time` plus the
aggregation columns, so Splunk offers the Visualization tab directly.

```spl
| axtimechart dataset="app-logs" q="status>=500" span=5m agg="count as errors" by="service" limit=1000
```

Options:

| Option | Required | Description |
| --- | --- | --- |
| `dataset` | Yes | Axiom dataset ID. |
| `q` | No | Splunk-like query expression compiled to APL search syntax. |
| `agg` | No | Aggregation expression. Defaults to `count`. |
| `span` | No | Bucket width such as `30s`, `5m`, `1h`, or `1d`. Defaults to `1m`. |
| `by` | No | Optional split-by field. |
| `limit` | No | Maximum returned rows. Defaults to `10000`. |
| `explain` | No | Return compiled APL without querying Axiom. |
| `startTime`, `endTime`, `earliest`, `latest` | No | Time controls. See Time Ranges for precedence and default behavior. |
| `tokenName`, `mgmtPort` | No | Connection overrides. |

### `axlookup`

Look up latest matching context from Axiom and add selected fields to incoming Splunk events. It follows Splunk's lookup mental model, but the backing source is an Axiom dataset rather than a Splunk lookup table.

```spl
index=main service=api
| axlookup dataset="deployments" on="service=service.name" fields="version,owner,team"
| table _time, service, axiom_version, axiom_owner, axiom_team
```

Options:

| Option | Required | Description |
| --- | --- | --- |
| `dataset` | Yes | Axiom dataset used as the lookup source. |
| `on` | Yes | Join key as `field` or `splunkField=axiomField`. |
| `fields` | Yes | Comma-separated Axiom fields to add, or `*`. |
| `prefix` | No | Prefix for added fields. Defaults to `axiom_`. Added field names are normalized for SPL, so `service.version` becomes `axiom_service_version`. |
| `overwrite` | No | Whether added fields may replace existing fields. Defaults to `false`. |
| `batchSize` | No | Distinct join values per Axiom query. Defaults to `250`, capped at `1000`. |
| `maxFields` | No | Maximum added fields when `fields=*` is used. Defaults to `50`. |
| `strict` | No | Whether Axiom failures fail the Splunk search. Defaults to `true`. |
| `startTime`, `endTime`, `earliest`, `latest` | No | Time controls for the Axiom lookup. By default, the Splunk dispatch range is used when available. |
| `tokenName`, `mgmtPort` | No | Connection overrides. |

### `axquery`

Run raw APL when you need full Axiom language control.

```spl
| axquery apl="['app-logs'] | where status >= 500 | summarize errors=count() by service, bin(_time, 1h) | sort by _time asc"
| table _time, service, errors
```

Options:

| Option | Required | Description |
| --- | --- | --- |
| `apl` | Yes | Raw APL query. |
| `startTime`, `endTime` | No | Override the Axiom query time range. Otherwise the Splunk dispatch range is used when available. |
| `earliest`, `latest` | No | Splunk-style aliases for `startTime` and `endTime`. |
| `paginate` | No | `cursor` or `time`. Requires `| sort by _time [asc|desc]` in the APL. |
| `debug` | No | Enable detailed `_internal` logs. |
| `maxTime` | No | Maximum runtime in seconds. Defaults to `600`. |
| `tokenName`, `mgmtPort` | No | Connection overrides. |

Pagination notes:

- Without pagination, Axiom's per-page limit applies.
- With pagination, put `| limit n` in the APL to cap total returned events.
- `paginate=cursor` uses Axiom cursors.
- `paginate=time` advances by `_time` and deduplicates with an internal row hash.

## Debugging

For `axsearch`, `axstats`, and `axtimechart`, start with `explain=true`. It shows the generated APL without querying Axiom, which separates app syntax issues from Axiom query issues:

```spl
| axstats dataset="app-logs" q="status>=500" stats="count as errors" by="service" explain=true
| table compiled_apl, startTime, endTime
```

If the compiled APL is not what you expected, compare the expression with the [APL introduction](https://axiom.co/docs/apl/introduction) and the [Splunk SPL to APL cheat sheet](https://axiom.co/docs/apl/guides/splunk-cheat-sheet).

Use `debug=true` with `axquery` when you need detailed runtime logs:

```spl
| axquery apl="['app-logs'] | sort by _time desc | limit 20" debug=true
```

Then inspect the latest run:

```spl
`axquery_latest`
```

Logs include stable fields such as `jobId`, `command`, `event`, `instanceEvent`, page counters, status values, and Axiom rate-limit headers.

## Troubleshooting

### No datasets appear

Confirm setup saved the token, then verify the token can read/query at least one dataset. See [Axiom API tokens](https://axiom.co/docs/reference/tokens) and [Axiom datasets](https://axiom.co/docs/reference/datasets).

### The generated APL looks right, but Axiom rejects the query

Run the same APL in Axiom Console or compare it with the [APL introduction](https://axiom.co/docs/apl/introduction), [sample queries](https://axiom.co/docs/apl/tutorial), and the relevant operator or function docs. For aggregations, start with [summarize](https://axiom.co/docs/apl/tabular-operators/summarize-operator) and [aggregation functions](https://axiom.co/docs/apl/aggregation-function/statistical-functions).

### An aggregation is not supported by `axstats`

`axstats` intentionally supports the common aggregation subset. Use `axquery` for APL-only aggregations such as conditional aggregations until they are exposed directly in the Splunk-shaped command surface.

### Too many buckets

Increase `span` or narrow the time range. If the search uses the Splunk time picker, remember that broad picker ranges also widen the Axiom query window. For raw APL, check your `bin(_time, ...)` usage and the surrounding `summarize` query.

### Axiom lookup is slow

Reduce the number of distinct join values entering `axlookup`, select only the fields you need, and keep `fields=*` for exploration rather than production searches.

### Workflow actions do not appear

Workflow actions are event-menu actions. They require an `axiom_dataset` field plus a supported field such as `trace_id`, `span_id`, `service`, `service.name`, `deployment`, or `resource.k8s.deployment.name`. Direct `axsample`, `axsearch`, `axstats`, and `axtimechart` results include `axiom_dataset`; raw `axquery` results need `| eval axiom_dataset="<dataset>"` if the APL query should participate in workflow actions.

### Get help

Visit [axiom.co/support](https://axiom.co/support) or email [support@axiom.co](mailto:support@axiom.co?subject=Axiom%20for%20Splunk%20support). Include the app version, Splunk version, the command you ran, and the `jobId` from Debug when the issue involves `axquery`.

## Setup

On first use, Splunk redirects to the app setup page.

The setup page:

- asks for an Axiom API token
- stores it in Splunk `storage/passwords`
- marks the app configured
- reloads the app
- redirects to `/app/axiom`

Token guidance:

- create the token in Axiom before setup
- give it read/query access to the datasets users need
- use a shared token when the Splunk app should expose a shared Axiom view
- use `tokenName` only when you intentionally store and select another credential

## Local Development

This repository should be the only repo needed for normal local development, testing, and packaging work.

For a fresh checkout:

```bash
python -m pip install -r requirements.txt
npm run splunk:up
```

Then:

1. open `http://127.0.0.1:18000`
2. go to `/app/axiom`
3. complete first-run setup
4. run `npm run test`

If you want Splunk 10 instead of the default Splunk 9:

```bash
npm run splunk:up:10
```

To run both compatibility targets:

```bash
npm run splunk:up:all
```

Default host ports:

- Splunk 9 web: `http://127.0.0.1:18000`
- Splunk 9 mgmt: `https://127.0.0.1:18089`
- Splunk 10 web: `http://127.0.0.1:28000`
- Splunk 10 mgmt: `https://127.0.0.1:28089`

Supported npm operations:

```bash
npm run splunk:status
npm run splunk:health
npm run splunk:reload
npm run splunk:restart
npm run splunk:down
```

The Docker path mounts the repo read-only at `/workspace/axiom-src`, creates an app shim at `/opt/splunk/etc/apps/axiom`, and keeps writable Splunk state under `dev/state/...`. This avoids the Splunk container taking ownership of the working tree while preserving live edits.

For a native Splunk install, link the repo root into Splunk:

```bash
ln -s "$(pwd)" "<SPLUNK_HOME>/etc/apps/axiom"
```

Restart Splunk after changing the symlink or app layout.

## Testing And Packaging

Local packaging and validation currently assume Python `3.9`.

Install tooling:

```bash
python -m pip install -r requirements.txt
```

Run the local unit and syntax gate:

```bash
npm run test
```

Run live integration tests against running local Splunk containers:

```bash
npm run test:integration
```

Integration tests use `.env` for `AXIOM_TEST_TOKEN` and `AXIOM_TEST_DATASET`.

Package workflow:

```bash
VERSION="$(npm run --silent version:get)"
npm run package:validate
npm run package:build
splunk-appinspect inspect "dist/axiom-${VERSION}.tar.gz" --mode precert --skip-trusted-libraries-update --max-messages all
splunk-appinspect inspect "dist/axiom-${VERSION}.tar.gz" --mode precert --included-tags cloud --skip-trusted-libraries-update --max-messages all
```

The package helper stages a clean temporary app directory named `axiom` before calling `slim`, so local runtime and dev-only files do not leak into the app package.

Release candidate gate:

```bash
npm run release:check
```

This runs the unit/syntax gate, validates and builds the package, checks the tarball for leaked local/dev files, and runs AppInspect with both the standard `splunk_appinspect` and Splunk Cloud `cloud` tags. For a live Splunk/Axiom smoke pass against running local Splunk containers, use:

```bash
npm run release:check:integration
```

### GitHub Actions

The repository has three workflows:

- `CI`: runs `npm run release:check` on pull requests, pushes to `main`, and manual dispatches. This is the deterministic branch-protection check.
- `Integration`: runs separate Splunk 9 and Splunk 10 live-check jobs against Axiom. It runs on pushes to `main`, a daily schedule, and manual dispatches. If `AXIOM_TEST_TOKEN` is not configured, the workflow exits successfully after logging a warning.
- `Release`: runs the release gate for `v*.*.*` tags and manual dispatches. Tag runs verify that the tag matches the app version, build `dist/axiom-<version>.tar.gz`, write `dist/axiom-<version>.tar.gz.sha256`, upload workflow artifacts, and publish a GitHub Release.

Required repository secret for live integration:

```text
AXIOM_TEST_TOKEN
```

Optional repository variables:

```text
AXIOM_TEST_DATASET=splunk_app_ci
AXIOM_TEST_LOOKUP_KEY=service
AXIOM_TEST_LOOKUP_VALUE=api
```

Release tags must match the app version in `default/app.conf` and `app.manifest`. The release workflow creates the GitHub Release from the tag and attaches the Splunk app tarball plus its SHA-256 checksum. Manual release workflow runs are packaging dry runs and do not publish a GitHub Release.

### Release Procedure

Prepare release metadata with the npm helper:

```bash
npm run version:set -- 1.1.1
```

This updates:

- `default/app.conf` `[id] version`
- `default/app.conf` `[launcher] version`
- `default/app.conf` `[install] build`, incremented by one by default
- `app.manifest` version
- `app.manifest` release date

Use `--date YYYY-MM-DD` to set a specific release date, `--build N` to set an explicit Splunk build number, or `--no-build-bump` to keep the current build number.

Validate and commit the release metadata:

```bash
npm run release:check
git add default/app.conf app.manifest
git commit -m "chore(release): prepare $(npm run --silent version:get)"
git push origin main
```

Publish the GitHub Release from a matching tag:

```bash
VERSION="$(npm run --silent version:get)"
git tag -a "v${VERSION}" -m "Axiom for Splunk ${VERSION}"
git push origin "v${VERSION}"
```

The `Release` GitHub Actions workflow verifies that the tag matches the app version, rebuilds the package, uploads workflow artifacts, and publishes the GitHub Release with the tarball and SHA-256 checksum attached. Upload the released tarball to Splunkbase when publishing there.
