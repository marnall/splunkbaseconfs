# PolySwarm App

For use with Splunk Enterprise and Splunk Cloud Platform.

Version 1.0.0.

Written for a Splunk administrator who has only the installed package.

## 1. What the app does

PolySwarm is a malware threat intelligence platform whose verdicts come from
many detection engines scanning the same artifact rather than from one vendor.
This app brings those verdicts into Splunk: it annotates the hashes, URLs and
domains already in your events with a score, a banded verdict and a detection
count, extracts and refangs indicators out of raw text without leaving the
search head, and submits URLs to a cloud sandbox and writes the findings back.
It ships five search commands, three dashboards, three workflow actions, an
alert action and two modular inputs.

## 2. Version support

Splunk Enterprise 9.4 or later, and Splunk Enterprise 10.x. Splunk Cloud
Platform is supported through a private app upload.

Tested live on Splunk Enterprise 10.4.2, which is the instance the dashboards,
the setup page, the commands and the role behaviour were exercised on.

The source holds to the Python 3.9 floor Splunk 9.x ships, and continuous
integration runs the suite on Python 3.9 and Python 3.13, the 9.x and 10.x
pairing. One package therefore runs across a mixed estate.

Every stanza that runs Python, the five search commands, the two modular inputs
and the alert action, declares support for both interpreters with
`python.required = 3.9,3.13`. That is a list rather than a pinned version, so
Splunk selects the newest interpreter on it that your release actually provides:
Python 3.13 on 10.x, and Python 3.9 on 9.x, which predates the setting and
selects the interpreter from `python.version` instead. There is nothing to
choose and nothing to edit for either release.

Splunk Enterprise Security. Every feature works on a search head that has
Enterprise Security installed, and nothing in the app requires it. The
PolySwarm Detonate alert action additionally declares itself an adaptive
response action, written to Splunk's documented contract and not verified on a
licensed Enterprise Security instance, because none was available. Treat the
first run on one as the test.

## 3. System requirements

Install on a search head only. The app reads credentials and KV store
collections, both of which live on the search head. There are no indexer
components, no index time configuration, and nothing to deploy to a forwarder.

The KV store must be enabled. Its collections hold the verdict cache, the
sandbox task list, entitlement state and the intel pull checkpoint.

On a search head cluster there is nothing extra to configure. The app ships a
`[shclustering]` stanza in `default/server.conf` that asks Splunk to replicate
the app's own configuration file, so the community and the daily limit you save
through the setup page on one member apply on all of them instead of staying on
the member that served the form. The stanza carries replication settings only
and enables no clustering of its own: whether an instance is clustered is
decided by your deployment's configuration, not by an app's.

Outbound HTTPS from the search head to the PolySwarm API host named in
`bin/ps_client.py`, which is `api.polyswarm.network`, on port 443. Nothing
inbound is needed.

A PolySwarm API key, on a plan whose entitlement includes integrations. The
basic plan carries no integration entitlement and no included detonations, so a
basic key installs cleanly and then answers nothing. The one command that needs
neither key nor entitlement is `polyswarmextract`.

## 4. External data sources

The app calls one external source, the PolySwarm API at
`api.polyswarm.network`, over HTTPS. Four groups of endpoints: enrichment
(artifact and URL search, plus attribution), account (identity, plan and
entitlement), sandbox (the provider list, a submit and a task status read), and
metadata search (the threat intel pull).

What is sent is the indicator being asked about, a hash, a URL or a domain out
of your own events, plus the sandbox target URL when you detonate. What comes
back is a score, a verdict, a detection count, engine assertions, attribution
and sandbox findings. The key travels in a request header.

Nothing else leaves the search head. The app collects no telemetry and reaches
no other host. Opening the Overview or Sandbox Tasks dashboard makes no request
at all, and `polyswarmextract` never makes one.

## 5. Installation

1. In Splunk Web, go to Apps, then Manage Apps, then Install app from file,
   choose the package and select Upload. On the file system instead, extract it
   into `$SPLUNK_HOME/etc/apps/polyswarm_app_for_splunk/`.

2. Restart splunkd. This is required on a first install: the five search
   commands, the alert action and the two modular inputs are registered when
   splunkd starts.

       $SPLUNK_HOME/bin/splunk restart

3. The app ships `is_configured = false`, so Splunk offers a Set up affordance
   beside it in the app list. Select it, or go to
   `/app/polyswarm_app_for_splunk/setup`. Paste your key, select Save, then
   select Test credentials. An account row means the key works.

4. After an upgrade, bump Splunk Web's static asset version. The setup page's
   script and stylesheet are served from a URL carrying Splunk's build number
   rather than the app's version, so a browser keeps the previous release's
   copy until that URL changes. Open `/en-US/_bump` as an administrator and
   select Bump version. A splunkd restart does not do this.

## 6. Configuration

The setup page is the whole of the required configuration. It writes the key
into Splunk's encrypted credential storage, under realm
`polyswarm_app_for_splunk` and username `api_key`, and does not read it back.
No restart is needed to save or change a key. An upgrade does not send a
configured instance back to the page.

The community setting, on the same page, is optional, and blank is right for
almost every deployment: the app then reads the communities the account is
entitled to and scopes a detonation to the most private one, falling back to
the platform default. Name one only if detonations must go to a specific
private community. Every task row records the community it ran in.

Two modular inputs, both under Settings, then Data inputs.

- PolySwarm sandbox task poller, stanza
  `[input_task_poller://polyswarm_sandbox_tasks]`, ships enabled at a 120
  second `interval`. It follows each detonation until the platform settles it,
  and spends nothing when there are none. `max_polls` caps the status requests
  one run may make, default 50. `max_task_age_hours` is how long an unsettled
  detonation stays on the worklist before the poller stops asking, default 24,
  at least 1 and at most 168. Raise it if rows are retired sooner than your
  detonations finish.
- PolySwarm threat intel pull, stanza
  `[input_intel_pull://polyswarm_intel_pull]`, ships **disabled** at a 900
  second `interval`, because every page of results it fetches is a metered
  request. Before enabling it, point `index` at a threat intel index you have
  created, choose `families` or `tags` or neither, set the `min_polyscore`
  floor, and read `max_artifacts_per_run`, the cap that makes the input
  affordable. `lag_seconds`, default 300, is how far behind the clock each
  window closes: an artifact becomes searchable a little after the platform
  takes it, so a window closing at the clock would permanently skip what was
  not yet searchable. Preview a cycle with `polyswarmsync`, then enable the
  stanza or write `disabled = 0` into the app's own `local` inputs file.

Roles. An administrator installs the app and saves the key. A non-administrator
running a metered command needs a Splunk capability as well: the commands read
the stored key from splunkd's `storage/passwords` endpoint as the searching
user, Splunk gates that endpoint with `list_storage_passwords`, and the
built-in `power` role does not hold it. The app ships a role that does,
`polyswarm_analyst`, which imports `power` and enables that one capability;
assign it in Settings, then Users. Without it a non-administrator gets "Could
not read the PolySwarm API key from credential storage" from every metered
command on an otherwise correct install. Adding the capability to a role you
already use works too. `polyswarmextract` and the portal link need neither.

## 7. How to run

Three dashboards, from the app's navigation bar. Overview is the account and
cache picture and costs nothing to open. Triage runs a search of your own
through enrichment and shows the per engine assertions behind one verdict.
Sandbox Tasks is every detonation submitted from this app and what came back.

Five search commands.

Prove the key works and see what the account is entitled to. Two requests.

    | polyswarmusage

Enrich a field of hashes, at most 500 distinct indicators.

    index=endpoint file_hash=*
    | stats count by file_hash
    | polyswarmsearch field=file_hash limit=500
    | table file_hash, polyswarm_verdict, polyswarm_polyscore, polyswarm_detections, polyswarm_cache

`limit` is required, because each distinct indicator not already cached spends
one request. Read `polyswarm_cache` on each row: `hit` cost nothing.

Extract indicators out of any text field. No key, no request, no quota.

    | makeresults
    | eval body="Phish landing hxxps://evil[.]example[.]com/pay then beacon to 203.0.113[.]9, sender billing@evil[.]example[.]com"
    | polyswarmextract textfield=body
    | eval pairs=mvzip(polyswarm_ioc, polyswarm_ioc_type)
    | mvexpand pairs
    | table pairs

Detonate one URL in the sandbox. This is the most expensive thing the app does.

    | polyswarmdetonate url="https://example.com"

Preview one cycle of the intel pull, which indexes nothing and never advances
the input's checkpoint.

    | polyswarmsync stanza=polyswarm_intel_pull | table window_start, window_end, artifacts, requests, limit_reached, note

Workflow actions. Click a field value in a search result and the field menu
offers Enrich with PolySwarm, Enrich with PolySwarm (with attribution), and
Open in PolySwarm portal. The first two dispatch a search over that value; the
third is a hyperlink and spends nothing.

The alert action. PolySwarm Detonate submits a URL from a search result for
detonation. Attach it to a scheduled or correlation search and set
`param.field` to the field holding the URL. `param.max_detonations` defaults to
1 and is capped at 5 in code, so no value typed into the form can spend more
than five detonations per firing. No saved search here attaches it.

## 8. Troubleshooting

The app writes one structured line per event to its own log,
`$SPLUNK_HOME/var/log/splunk/polyswarm_app_for_splunk.log`. splunkd indexes that
directory, so read it from a search bar:

    index=_internal source=*polyswarm_app_for_splunk.log

Match on `source` rather than a sourcetype: the app ships no monitor stanza, so
a search keyed on a sourcetype would be silently empty. The lines carry no
indicator, field value, query string or key, so an extract is safe to attach to
a support ticket. Look first for a `start` line with no matching `finish`.

Four errors account for most of what goes wrong. The class name is on the log
line, under `reason`.

- `ClientConfigurationError`. No key is stored, or no usable configuration
  could be assembled. No request was made. Save a key on the setup page.
- `AuthenticationError`. PolySwarm rejected the key, HTTP 401 or 403, and it is
  never retried, because a wrong key stays wrong. Paste the key again from your
  PolySwarm account settings. If a key is stored and only one user's commands
  fail, read the role note in section 6 instead.
- `RateLimitError`. Every attempt came back rate limited, so the account is
  over its allowance. The fix is more allowance or fewer requests, not a
  restart. Lower `limit` or run the search later.
- `ClientError`. Everything else that survived three attempts: a server fault,
  a network failure, or a body that was not JSON.

Every dashboard is blank after a splunkd restart, with the tab titled just
"Dashboard" and no toolbar. Splunk Web can fill its parsed view cache while
splunkd is still starting, before views can be read, then serve an empty shell
from it. The files on disk are intact. Restart the web tier alone, which
touches neither splunkd nor any session, then reload the page.

    $SPLUNK_HOME/bin/splunk restart splunkweb -auth <admin user>

Pages load in waves on a small search head. Every panel is its own search and
the Overview has around twenty five, so Splunk queues what it cannot run
concurrently and logs "The maximum number of concurrent historical searches on
this instance has been reached" each time. Nothing fails and the queue drains
in seconds. That throttle is Splunk's rather than the app's, and the limits
behind it belong to the Splunk administrator.

## 9. Support

Support contact: support@polyswarm.io. Include the app version from app.conf, the Splunk version, the finish line from the app log for the failing run, and the search or page involved. Never paste an API key or a session key into a ticket; a copy of a log line is safe as it comes out.

## 10. Documentation

The full guides ship with the app's source repository: installation and roles,
every command option and dashboard panel, a troubleshooting page, and a
run-of-show for demonstrating each feature with the search and cost per step.
They are linked from this app's Splunkbase listing.
