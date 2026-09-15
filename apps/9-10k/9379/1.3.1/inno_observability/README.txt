Inno Observability
==================
APM, infrastructure, Kubernetes and OpenTelemetry-agent monitoring built on
OTel telemetry already indexed in Splunk.

Version 1.1.0
Publisher: Inno Software (sole proprietorship, Republic of Korea)
Author: Inho Jung


Copyright and ownership
-----------------------
Copyright (c) 2026 Inno Software. All rights reserved.

PROPRIETARY AND CONFIDENTIAL — LICENSED, NOT SOLD.

Inno Software owns and retains all right, title, and interest in and to this
software, including the source code, the search logic (SPL), classification
rules, severity models, rendering specifications, dashboard definitions, user
interface, and documentation. This is an unpublished proprietary work protected
by the copyright laws of the Republic of Korea and by international treaties;
portions constitute trade secrets.

That this package ships in human-readable form, and that a Splunk administrator
can inspect it, does NOT grant any right to copy, reuse, or redistribute it.

Copying, redistribution, resale, sublicensing, providing the software as a
service to third parties, sharing or transferring a license key, and removal or
alteration of proprietary notices are PROHIBITED without written permission.
Resellers and systems integrators are included: each end customer requires its
own key.

Full terms:  LICENSE.txt in this package
             https://innosw.net/observability/terms.html
Contact:     support@innosw.net


Licensing model
---------------
This is a commercial, paid application. A valid license key issued by Inno
Software and locked to your Splunk deployment identifier is REQUIRED.

Without a valid key, only the "License" dashboard opens, so that an
administrator can enter a key or request an evaluation. There is no free tier,
no sample mode, and no reduced-functionality mode.

Licensed features:
  servicemap      Service topology map (Overview, Service Detail)
  scatter         X-View style trace scatter plot (Overview, Trace List)
  fleetmap        Infrastructure Fleet Map honeycomb
  serverlist      Infrastructure server list
  classification  Classification Admin and Category Settings
  studio          Chart Studio (self-service SPL chart/dashboard builder)
  agent           Agent collection (fleet, inventory, detail, deploy)
  events          System Events
  rca             AI root-cause analysis

Enforcement is fail-safe, never destructive. When a license is absent, expired,
or used on a deployment it was not issued for, the app stops presenting its
dashboards. It does not delete data, does not stop Splunk, and does not touch
the customer's indexes. An expiring subscription gets a grace period (14 days
annual / 3 days monthly) during which everything keeps working with a warning.

A transient failure to verify does not lock the app: verification is retried,
and the last successful verdict is cached for the session. A blocked screen
distinguishes "no valid license" from "could not verify" so the operator knows
which one they are looking at.

To enter a key: open the "License" dashboard in this app (admin only). The key
is stored in local/inno_license.conf and is never sent to the browser.

Evaluation licenses are available on request — the blocked screen shows the
deployment identifier needed to issue one.


Dashboards
----------
  Overview                Service map, golden signals, DB signals, live
                          active-transaction cylinder, trace scatter
  Service Detail          Per-service RED metrics, endpoints, slow/error
                          traces, instance cards, runtime metrics
  Trace List              Searchable trace list plus scatter plot
  Trace View              Per-trace span waterfall with correlated infra
                          metrics, logs, and actual bound SQL values
  Infrastructure          Fleet Map, server list, server detail,
                          classification admin, category settings
  Agent                   OTel Collector fleet health, inventory, per-agent
                          detail, install-command generator
  Kubernetes              One-View (cluster > namespace > workload > pod with
                          metric/APM/log/event correlation), Cluster Detail
                          (nodes, requests vs usage, storage, control plane),
                          Deployment Timeline (config-version ledger that
                          survives rollbacks)
  Studio                  Chart Studio — build charts from raw SPL, assemble
                          dashboards, publish them as views in other apps
  System Events           Collector lifecycle and host events
  License                 Key entry and subscription status (admin only)


Data requirements
-----------------
Telemetry is expected from the Splunk OpenTelemetry Collector (HEC). Point the
macros at your own indexes — the app ships no indexes.conf and creates no
indexes.

  sourcetype=otel:trace        OTel spans. Fields: trace_id, span_id,
                               parent_span_id, kind, start_time / end_time
                               (epoch nanoseconds), service.name,
                               deployment.environment, status.code,
                               attributes.*
  sourcetype=otel:log          Application logs (optional)
  metrics indexes              hostmetrics, kubeletstats, k8s cluster receiver
  sourcetype=kube:events       Kubernetes events (optional)
  sourcetype=apm:span_start    Optional span-lifecycle events
                               (event=span_started|span_ended). Enables true
                               real-time in-flight detection; without it the
                               cylinder replays completed spans instead.
  attributes.db.statement.bound
                               Optional bound-SQL attribute. Produced
                               generically for Java by the apm-sql-bind OTel
                               agent extension, or for Python/psycopg2 by a
                               cursor wrapper. Trace View highlights it when
                               present.


Setup
-----
1. Point the data macros at your indexes:
     Settings > Advanced search > Search macros
       apm_index              trace/log index      (default: index=k8s_logs)
       apm_metrics_index      APM metrics index
       infra_otel_index       host metrics index   (default: index=infra_metrics)
       k8s_index              k8s log/event index
       k8s_metrics_index      k8s metrics index
       otel_agentlog_index    collector journald log index

2. (Optional) Enable AI root-cause analysis by setting apm_llm_endpoint to a
   quoted OpenAI-compatible chat/completions URL, plus apm_llm_model.
   The endpoint is called FROM THE USER'S BROWSER. Left empty (the shipped
   default) no external call is ever made. On Splunk Cloud the endpoint must be
   https, because browsers block mixed content.

3. (Optional) Set apm_o11y_base_url to deep-link into Splunk Observability
   Cloud APM from the service menus. Empty by default.

4. (Optional, premium) Enter your license key in the License dashboard.


Server-side components — disclosure
-----------------------------------
This section exists so a reviewer does not have to reverse-engineer intent.

1) Custom search command (bin/innolicense.py)
   `| innolicense` returns ONE row of license state (tier, premium, which
   features are allowed). It never returns the key itself. Dashboards call it
   to decide what to render. The gate is server-side on purpose: a browser-only
   gate is decoration, since any user can edit the JavaScript.

   It dispatches nothing and reads no customer data. Splunk RBAC still decides
   what data a user may see; the gate only decides whether a licensed surface
   renders at all.

2) Modular input (bin/inno_observability_license_monitor.py, hourly)
   Writes a local `license_status` event (sourcetype=inno:license) so admins
   can alert on `state!="active"` with ordinary Splunk alerting, and so a
   renewal countdown is visible. It does NOT phone home — most target customers
   are air-gapped. No network egress of any kind occurs from this input.

3) On SPL visibility — stated plainly
   The app does NOT attempt to hide its SPL, and nothing in this package is
   obfuscated, encrypted, minified-for-secrecy, compiled, or packed. No .pyc,
   .so, or binary is shipped. Every dashboard's SPL is readable in the view XML,
   and Splunk itself records each dispatched search verbatim in the customer's
   own `index=_audit`. Hiding it was considered and deliberately rejected as
   both unachievable and hostile to customers who need to audit what the app
   runs on their data.

   Licensing therefore gates *rendering of the customer's real data*, not
   knowledge of the queries. Readability is not a grant of rights: see
   LICENSE.txt.

4) License verification (bin/inno_license.py, lib/rsa)
   Fully offline RSA-SHA256 signature verification against the vendor public
   key shipped in bin/license_pubkey.pem. No online activation, no callback.

5) Optional companion component (bin/innocore.py)
   `| innocore` is a thin shuttle to an OPTIONAL companion service that the
   customer installs separately on the search head. It is NOT part of this
   package — no binary, .so, or compiled artifact is shipped here — and it is
   reached only over HTTP on the loopback interface (127.0.0.1). It performs
   chart-rendering computation server-side.

   If the companion is not installed or not running, the shuttle never raises:
   it returns a single row and the panel states the reason. Nothing leaves the
   host; there is no outbound network access.


Network behaviour and privacy
-----------------------------
  * The app makes NO outbound network calls of its own. Nothing phones home.
  * The only optional egress is the AI RCA panel, which calls the endpoint the
    administrator configures, from the browser, and is disabled by default
    (empty macro). Bound SQL sent to that endpoint is redacted first: string
    literals, e-mail addresses and long hex values are masked.
  * The license key is never sent to the browser and never leaves the Splunk
    instance.
  * No user credentials, personal data, or telemetry are collected by the app.


Notes
-----
  * Dashboards are Simple XML (version 1.1) with custom JavaScript renderers.
  * Status colours: under 3s OK (green), 3-5s slow (yellow), 5s and over
    critical (red). Error rate at or above 5% is red.
  * Health-check probe endpoints (/health, /ready, /healthz, /readyz, /livez,
    /actuator/health) are excluded from latency and throughput panels.
  * Some dashboards read KV store collections that scheduled searches in this
    app populate. They are created automatically on first app load.

Third-party components are listed in THIRD_PARTY_LICENSES.txt. Those licences
apply ONLY to the components they name and grant no rights whatsoever in the
rest of this software, which remains the property of Inno Software.
