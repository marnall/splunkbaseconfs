# TA-Oracle-OCI — Technology Add-on for Oracle Cloud Infrastructure (HEC push + API key pull)

> **Independent, third-party add-on.** This is not affiliated with,
> endorsed by, certified by, or supported by Oracle Corporation or
> Splunk Inc. "Oracle", "Oracle Cloud Infrastructure", "OCI", "Splunk",
> and associated marks are trademarks of their respective owners, used
> here only to describe compatibility. Support for this add-on is
> provided by its author (see the Support section below), not by
> Oracle or Splunk.

## Why this exists
The official **Splunk Addon for OCI** (Splunkbase app 5222, pull-based) and
**Splunk Cloud Addon for OCI** (app 7021, streaming-based) are both
**archived by Splunk** and capped at platform version 9.2. Neither installs
or runs on Splunk 9.3+ or Splunk 10 — their bundled OCI SDK binaries
(`_cffi_backend`, `cryptography` bindings) are compiled against Python 3.7,
and Splunk's embedded Python interpreter moved past that version.

This TA replaces them with two supported methods:
1. **Push**: an OCI Function posts events to Splunk's HTTP Event Collector.
2. **Pull**: a native modular input (`bin/oci_stream.py`) polls OCI
   Streaming directly using API-key auth — the same Tenancy/User OCID,
   Fingerprint, and private key `.pem` fields TA 5222 originally asked for.

Because this TA contains **no compiled binaries**, and the pull method's
one dependency (`oci` SDK) is installed fresh at deploy time against
whichever Python interpreter Splunk actually ships, neither method is tied
to Splunk's embedded Python version — both should stay compatible across
future platform upgrades without a rebuild.

**Declared vs. verified compatibility:** the declared range is Splunk
Enterprise 9.4.0–10.4.0 plus Splunk Cloud, based on the reasoning
above. **Actually tested so far: Splunk Enterprise 10.2.7 only, with
Python 3.13, on-prem/standalone.** The rest of the range is a
technically sound claim, not a proven one — treat any other platform
version as unverified until confirmed there directly.

## Two ways to get data in — pick one
| | Push (HEC) | Pull (API key) |
|---|---|---|
| Auth needed | none (SCH invokes the Function via its own identity) | Tenancy/User OCID, fingerprint, private key `.pem`, optional passphrase — same fields the old TA 5222 asked for |
| Where polling logic runs | OCI Function (Oracle-side) | Splunk modular input (`bin/oci_stream.py`), typically on a heavy forwarder |
| OCI infra needed | Service Connector Hub + Function | none beyond the Stream itself |
| Supports Alarms/Notifications | yes | no (Streaming/Logging only, same as old TA) |
| Good fit when | you can stand up OCI Functions/SCH | client already issued API key credentials, or Functions isn't an option |

## Package layout (standard Splunk app structure)
```
TA-Oracle-OCI/
├── README/
│   └── inputs.conf.spec  — parameter docs for the oci_stream:// modular input
├── bin/
│   ├── oci_stream.py     — pull-method modular input (API key auth)
│   ├── requirements.txt  — `oci` SDK; install fresh against THIS instance's Python
│   └── lib/                — (created at deploy time by pip --target, not shipped)
├── default/
│   ├── app.conf          — app metadata
│   ├── inputs.conf       — no shipped stanzas; python.version/python.required only
│   ├── props.conf        — sourcetype definitions (timestamping, JSON parsing)
│   ├── eventtypes.conf   — basic event categorization
│   ├── tags.conf         — CIM tag assignments
│   └── data/ui/
│       ├── nav/default.xml       — app nav, opens to the Inputs tab
│       ├── views/inputs.xml      — in-app Inputs landing page (links, no setup.xml)
│       └── manager/oci_stream.xml — friendlier field grouping for the native
│                                     Data Inputs create/edit form
├── metadata/
│   └── default.meta      — sharing/permissions (admin + sc_admin), incl. private
│                            storage/passwords
├── oci-function/          — companion OCI-side code for the PUSH method (NOT
│   ├── func.py              installed in Splunk; deployed separately to OCI Functions)
│   ├── func.yaml
│   └── requirements.txt
└── README.md
```
No `setup.xml` and no `local/` are shipped — both are disallowed for
Splunk Cloud vetting. Configure inputs via the in-app Inputs tab or
Settings > Data Inputs after install (see "Configuring inputs from
inside the app" below). If you need the old one-page setup-wizard
experience for an **Enterprise-only, on-prem build**, see the note in
that same section — it's a one-file addition, not part of this package.

## Install (Splunk side)
Package and install like any other add-on:
```bash
cd /path/containing/TA-Oracle-OCI
tar czf TA-Oracle-OCI.spl TA-Oracle-OCI/
```
Then in Splunk Web: **Apps > Manage Apps > Install app from file**, upload
`TA-Oracle-OCI.spl`, restart when prompted (required — this registers the
modular input's scheme).

Install this on:
- **Indexers** (or the HEC-receiving tier) — required, for props.conf to
  parse incoming events correctly. On Splunk Cloud this tier is
  Splunk-managed; the app installs there via the normal Cloud app
  install/vetting flow.
- **Search heads** — recommended, for eventtypes.conf/tags.conf to drive
  CIM-based dashboards and searches. Same Cloud install path as above.
- **Heavy forwarder** — required if using the pull method (`oci_stream.py`),
  and on Splunk Cloud this **must be a customer-managed, on-prem/VPC heavy
  forwarder** — see the Cloud compatibility note below.

### Splunk Cloud compatibility note (pull method)
The `oci` Python SDK depends on `cryptography`, which ships compiled C
extensions. Splunk Cloud's multi-tenant search head/indexer tier gives
customers no shell access, so nothing can `pip install` there, and
arbitrary compiled binaries aren't accepted through standard self-service
app vetting. Practically, that means:
- The **push (HEC) method** is fully Cloud-native: HEC ingestion runs on
  Splunk's managed tier, and the token/input is provisioned via **ACS**
  (see the Push section below) rather than shipped in the app.
- The **pull (API key) method** only runs where you control the OS and
  Python environment — a self-managed **heavy forwarder** (on-prem or in
  your own VPC) that then forwards parsed events on to your Splunk Cloud
  stack. It cannot run on the Cloud-managed indexer/search head tier
  itself. This TA's `default/` package (props/eventtypes/tags/CIM config)
  installs on Cloud normally either way; only `bin/oci_stream.py`'s
  execution is restricted to infrastructure you manage.

If you need the pull method with zero customer-managed infrastructure,
use the push method instead — it has no such restriction.

## Configuring inputs

This package ships **without** `setup.xml` — required for Splunk Cloud
vetting (Cloud requires config changes to go through ACS, not an app's
own setup screen). Configure inputs the reliable way: go to
**Settings > Data Inputs** (top menu) and find **"OCI Streaming (API Key
Pull)"** in the list of input types. This app does not attempt to deep-
link directly to that page from inside its own UI — those links can
404 or error depending on your specific Splunk Web version, so
Settings > Data Inputs is the one path guaranteed to work.

Once you're on that native page, the create/edit form is customized by
this app (`data/ui/manager/oci_stream.xml`) with grouped fields
(Authentication / Stream / Tuning) instead of the raw generic form.

For the push method, create the HEC token under **Settings > Data
Inputs > HTTP Event Collector** (Splunk Enterprise) or via ACS (Splunk
Cloud) — see below.

> **Building an Enterprise-only, on-prem package instead?** A one-page
> `setup.xml` wizard (Private Key Passphrase, then OCI Connection
> Details in one form, backed by `storage/passwords` +
> `data/inputs/oci_stream`) is a straightforward addition if you don't
> need Splunk Cloud compatibility for that build — ask and it can be
> added back to a separate copy of this package. It is intentionally
> left out of this Cloud-compatible build.

## Pull method setup (API key auth) — on a self-managed heavy forwarder

Skip this section if you just used the setup screen above and it worked.
This is the manual/CLI alternative — useful for a second stream, for
Splunk Cloud builds (where `setup.xml` is removed), or for scripted
deployment:

1. **Know which Python your Splunk version actually uses, and install
   against that one explicitly** — don't rely on `splunk cmd python3`
   alone. Splunk's embedded Python version differs by platform version:
   - **Splunk 10.x** → Python 3.13. Use:
     ```bash
     $SPLUNK_HOME/bin/python3.13 -m pip install --break-system-packages \
         --target=$SPLUNK_HOME/etc/apps/TA-Oracle-OCI/bin/lib \
         -r $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/bin/requirements.txt
     ```
   - **Splunk 9.x** → Python 3.9. Use the same command with
     `$SPLUNK_HOME/bin/python3.9` instead.

   This matters because some instances (especially after an in-place
   upgrade from 9.x to 10.x) have **more than one Python binary present
   at once**, and the generic `splunk cmd python3` command can silently
   resolve to the older, wrong one — even though Splunk itself actually
   runs your modular input under the newer one. Installing against the
   wrong Python produces a version-mismatched compiled
   `_cffi_backend*.so` file (a transitive dependency of `cryptography`)
   that fails to import at runtime, and is reported simply as `FATAL:
   oci package not installed` — even though the real cause is a Python
   version/ABI mismatch, not a missing package. This exact failure mode
   was hit and confirmed during testing on a Splunk 10.2.7 instance
   that had a stray Python 3.9 also present; using
   `$SPLUNK_HOME/bin/python3.13` explicitly (as above) fixed it.

   **If you're not sure which version applies**, verify first instead
   of guessing:
   ```bash
   $SPLUNK_HOME/bin/splunk cmd python3 -m pip --version
   ```
   The path shown must match the Python version your Splunk instance's
   own internal logs show it actually running under — check
   `index=_internal source=*splunkd.log*` for any modular input's
   startup line, which reports the interpreter path it ran with. If
   they don't match, use the explicit `python3.1X` path instead of
   `splunk cmd python3`, substituting whichever version you confirmed.

3. **Place the private key** on disk:
   ```bash
   mkdir -p $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys
   cp /path/to/client-key.pem $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
   chmod 600 $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
   chown splunk:splunk $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
   ```

4. **Store the passphrase securely** (skip if the key has none):
   ```bash
   $SPLUNK_HOME/bin/splunk add secret-storage-password \
       -realm TA-Oracle-OCI -name <stanza-name> -password '<passphrase>' \
       -auth admin:changeme
   ```
   The script looks this up via `storage/passwords` at runtime rather than
   reading it from `inputs.conf`.

5. **Configure the stanza** — create (or edit)
   `$SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/inputs.conf` with:
   ```ini
   [oci_stream://prod]
   disabled = 0
   tenancy_ocid = ocid1.tenancy.oc1.....
   user_ocid = ocid1.user.oc1.....
   fingerprint = aa:aa:aa:aa:aa:ae:aa:aa:aa:aa:aa:aa:ac:aa:aa:aa
   key_file = /opt/splunk/etc/apps/TA-Oracle-OCI/local/keys/oci_api_key.pem
   region = us-ashburn-1
   stream_ocid = ocid1.stream.oc1.iad.....
   stream_endpoint = https://cell-1.streaming.us-ashburn-1.oci.oraclecloud.com
   index = oci
   ```
   (`pass_phrase` is intentionally omitted — it's read from
   `storage/passwords`, previous step, not written here in plaintext.) This
   `local/inputs.conf` is per-environment state you create after install;
   it is not part of the distributed `.spl` package.

6. **Restart** the heavy forwarder and check
   `index=_internal source=*oci_stream.py*` for startup errors, then
   `index=oci` for incoming events.

For a second OCI stream, add another `[oci_stream://<name>]` stanza with
its own name and its own `storage/passwords` entry (same realm, different
username). Full parameter reference: `README/inputs.conf.spec`.

## Restricted/air-gapped servers (no PyPI access)

If the Splunk server can't reach PyPI directly (common for restricted or
air-gapped environments), install on an internet-connected server that
matches the target's Python version, OS, and CPU architecture first, then
transfer the compiled dependencies over:

1. On the internet-connected server: install this TA and complete the
   pip install step from above. Confirm it's actually working (check
   `index=_internal source=*oci_stream.py*` shows clean polling, not
   import errors) before bundling — otherwise you're just freezing a
   broken state.
2. Verify the two servers match on all three of these, since `bin/lib`
   contains compiled binaries tied to the exact combination:
   ```bash
   $SPLUNK_HOME/bin/splunk cmd python3 -c "import sys; print(sys.version_info)"
   uname -s
   uname -m
   ```
3. Run `tools/build_bundled_spl.sh` on the internet-connected server —
   it packages the already-installed `bin/lib` into a new `.spl`, and
   drops a `bin/lib/BUNDLED_FOR.txt` marker recording exactly what
   Python/OS/arch it was built for.
4. Copy that bundled `.spl` to the restricted server and install
   normally — no pip install needed there, since the dependencies are
   already inside the package.

If the two servers don't match, don't use the bundled `.spl` — run the
normal pip install step fresh on the restricted server's own
internet-connected staging point, or vendor the specific wheel manually.

## Push method setup (OCI Function -> HEC)

1. **Splunk side — create the HEC token.**
   - **Splunk Enterprise (self-managed):** Settings > Data Inputs > HTTP
     Event Collector > New Token. Name it `oci-sch`, set the default index
     (e.g. `oci`), leave "Source type" on Automatic so the function's
     per-event `sourcetype` field is honored.
   - **Splunk Cloud:** HEC tokens must be created via **ACS**, not shipped
     in the app or created through Splunk Web on the Cloud-managed tier:
     ```bash
     acs hec-token create -f - <<'EOF'
     {
       "name": "oci-sch",
       "allowedIndexes": ["oci"],
       "defaultIndex": "oci",
       "defaultSourcetype": "",
       "useAck": false
     }
     EOF
     ```
     `defaultSourcetype` is left blank so the function's per-event
     `sourcetype` field is honored, matching Enterprise's "Automatic"
     setting. See Splunk's ACS documentation for token rotation/deletion.

2. **Splunk side — sourcetype definitions.** Already shipped in this TA's
   `default/props.conf` — nothing extra to deploy.

3. **OCI side — Service Connector Hub.** Enable the log sources you need
   (Audit, VCN Flow Logs, etc.), create a Service Connector with Source =
   Logging (or Streaming), Target = Functions, pointing at the function
   below. Grant the SCH's dynamic group policy permission to invoke it.

4. **OCI side — deploy the function** (`oci-function/`):
   ```bash
   fn create app oci-splunk-app --annotation oracle.com/oci/subnetIds='["<subnet-ocid>"]'
   cd oci-function
   fn deploy --app oci-splunk-app
   fn config function oci-splunk-app oci-logs-to-splunk-hec SPLUNK_HEC_URL "https://your-splunk:8088/services/collector/event"
   fn config function oci-splunk-app oci-logs-to-splunk-hec SPLUNK_HEC_TOKEN "<hec-token-guid>"
   ```

5. **Test**:
   ```bash
   echo '{"eventType":"com.oraclecloud.audit","eventTime":"2026-08-21T12:00:00.000Z","data":{"eventName":"GetBucket"}}' \
     | fn invoke oci-splunk-app oci-logs-to-splunk-hec
   ```
   Then check Splunk: `index=oci sourcetype=oci:*`

## ⚠️ TODO before go-live: verify sourcetype names against the client's existing TA 5222 setup

The sourcetypes this TA produces (`oci:audit`, `oci:flowlogs`,
`oci:cloudguard:problem`, `oci:loadbalancer`, `oci:objectstorage`,
`oci:log`) are a naming convention chosen for this rebuild — **not
confirmed to match what the client's existing TA 5222 deployment actually
used**, since 5222's setup screen let the admin manually pick/type the
sourcetype per connector rather than enforcing fixed names.

Before cutting over, check what the client is actually running:
```
index=oci | stats count by sourcetype
```
If it differs, update `SOURCETYPE_MAP` in **both**
`oci-function/func.py` and `bin/oci_stream.py` (kept in sync manually,
see comments in each file), plus the sourcetype stanza names in
`default/props.conf`, `default/eventtypes.conf`, and `default/tags.conf`
to match.

**Detection reliability status**, confirmed against official Oracle
documentation (https://docs.oracle.com/en-us/iaas/log-analytics/doc/oci-parser-details.html)
and real production data — no longer guesses:

- `oci:audit` — **confirmed**, via `oracle.loggroupid == "_Audit"` (OCI's
  reserved literal ID for the Audit log group). The `type` field for real
  Audit records varies per action (e.g.
  `com.oraclecloud.logging.GetGeneratedUnifiedAgentConfiguration`,
  `com.oraclecloud.Compartments.ListCompartments`) and does not reliably
  contain "audit" at all, so `loggroupid` is the only dependable signal.
- `oci:flowlogs` — **confirmed**, real type is
  `com.oraclecloud.vcn.flowlogs.DataEvent`.
- `oci:loadbalancer` — **confirmed**, real types are
  `com.oraclecloud.loadbalancer.access` and `.error` (also catches `.waf`
  and `.waa` variants, which is fine - no separate sourcetype exists for
  those yet).
- `oci:objectstorage` — **confirmed**, real types are
  `com.oraclecloud.objectstorage.getobject`, `.getbucket`, etc.
- `oci:cloudguard:problem` — **two distinct real patterns confirmed,
  mapped to the same sourcetype**:
  - `com.oraclecloud.workloadprotection.cloudguard*` (e.g.
    `.cloudguarddatasource.wlp_scheduled_query_logs`,
    `.cloudguardtarget.recipelog`) — Cloud Guard's own scan/query/agent
    activity logs, found via an earlier check against real production
    data.
  - `com.oraclecloud.cloudguard.problem*` (e.g. `.problemremediated`,
    `.problemdetected`) — actual Problem lifecycle events (the security
    findings the sourcetype name implies), confirmed via a real example
    payload in [Oracle's own Cloud Infrastructure
    blog](https://blogs.oracle.com/cloud-infrastructure/integrating-cloud-guard-logging-analytics-part-1)
    and independently in a third-party SIEM vendor's default parser for
    the same event type.

  These likely represent genuinely different Cloud Guard event
  categories that can both occur in the same tenancy, not a
  contradiction requiring you to pick one — the earlier real-data check
  may simply not have observed a Problem-triggering event during its
  sample window. Confirm against this client's actual event samples
  which pattern(s) they see in practice.

**Also fixed**: an earlier version of `guess_sourcetype()` checked the
`source` field before `type`. Real Oracle examples across every log
format show `source` holds a resource name or OCID (e.g. a subnet OCID
for flow logs, a load balancer's display name) that varies per
environment and never contains a service identifier — `type` is the
field that actually follows the stable
`com.oraclecloud.<service>.<action>` pattern. Checking `source` first
meant `type` was effectively never reached, since `source` is almost
always non-empty.

## Known field-mapping fixes (host / source)

Two issues found via real production data, now fixed in both
`bin/oci_stream.py` and `oci-function/func.py`:

1. **`host` defaulted to the collector machine's own hostname for every
   event.** `extract_host()` now checks three schema locations, in
   order, each confirmed against a real Oracle source — OCI does not
   use one consistent envelope shape for tenancy info across log types:
   - `data.identity.tenantId` — Audit envelope. Confirmed against
     Oracle's official [Audit event
     reference](https://docs.oracle.com/en-us/iaas/Content/Audit/Reference/logeventreference.htm),
     which also documents `data.identity.ipAddress` if per-caller
     granularity is preferred instead of per-tenancy grouping.
   - `data.additionalDetails.tenantId` — Cloud Guard Problem envelope
     (a different location — Cloud Guard events have no `identity`
     object at all). Confirmed against a real example payload in
     [Oracle's own Cloud Infrastructure
     blog](https://blogs.oracle.com/cloud-infrastructure/integrating-cloud-guard-logging-analytics-part-1).
   - `oracle.tenantid` (no `data` nesting, lowercase) — VCN Flow Logs
     envelope, a third distinct shape. Confirmed against Oracle's
     official [VCN Flow Logs
     reference](https://docs.oracle.com/en-us/iaas/Content/Logging/Reference/details_for_vcn_flow_logs.htm).

   Note: tenantId/tenantid is a single fixed value for your whole OCI
   tenancy, so every event will share the same `host` — this
   groups/filters by tenancy, not by individual caller/IP. Falls back
   to Splunk's normal default when none of the three are present (most
   non-Audit log types don't have them yet — extend `extract_host()`
   for other types' relevant origin fields as real samples are
   observed, same approach as sourcetype detection).

2. **`source` field silently went blank for every Audit event.** Real OCI
   Audit records contain a literal top-level JSON key `"source"` (usually
   an empty string). Combined with `KV_MODE=json` in `props.conf`, Splunk
   auto-extracts that key at search time and it shadows Splunk's own
   `source` metadata field. Fixed by renaming the JSON's own `source` key
   to `oci_source` before the event is written (search on `oci_source` to
   see the original value; Splunk's `source` field now correctly shows
   `oci:stream` / `oci:service_connector_hub` as intended).

## Extending CIM coverage
`eventtypes.conf`/`tags.conf` currently map (tag names verified against
Splunk's current CIM 8.5 docs, not assumed from data model display
names):
| sourcetype                | eventtype              | CIM tag(s)              |
|----------------------------|-------------------------|--------------------------|
| oci:audit                 | oci_audit               | change                   |
| oci:flowlogs               | oci_flowlogs            | network, communicate     |
| oci:cloudguard:problem     | oci_cloudguard_problem  | alert                    |
| oci:loadbalancer           | oci_loadbalancer        | network, communicate     |
| oci:objectstorage          | oci_objectstorage       | change                   |

`props.conf` also sets `vendor` and `product` (search-time `EVAL-` fields,
no indexing cost) on every sourcetype — `vendor="Oracle"`, `product`
either `"Oracle Cloud Infrastructure"` or `"Oracle Cloud Guard"` for the
Cloud Guard sourcetype. These are the two fields most CIM data models
and Enterprise Security correlation searches expect for identifying
which vendor/product an event came from.

Still not included: full field-alias compliance for each CIM model
(e.g. Change, Network_Traffic, Alerts each expect specific required
field names beyond vendor/product — `action`, `src`, `dest`, `user`,
etc. — via `FIELDALIAS`/`EVAL` in `props.conf` or `transforms.conf`).
If you're running Splunk Enterprise Security and need full data model
compliance, tell me which CIM models your correlation searches/
dashboards actually use and I'll add those field mappings too.

## Customizing props/eventtypes/tags without editing this app

Never edit `default/props.conf`, `default/eventtypes.conf`, or
`default/tags.conf` directly — a future upgrade of this TA overwrites
`default/` and any local changes there are lost. Instead, use Splunk's
standard override layer, the same pattern every TA uses:

1. On the instance where this TA is installed, create (if it doesn't
   already exist):
   ```
   $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/props.conf
   $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/eventtypes.conf
   $SPLUNK_HOME/etc/apps/TA-Oracle-OCI/local/tags.conf
   ```
   (`local/` is intentionally not shipped in the `.spl` — see the
   packaging note below — so these files won't exist until you create
   them.)

2. Add only the stanzas/attributes you want to add or override — you
   don't need to copy the whole file. Splunk merges `local/` on top of
   `default/` stanza-by-stanza at startup (`local/` wins on conflicts),
   so e.g. to add a new sourcetype mapping without touching anything
   else:
   ```ini
   # local/props.conf
   [oci:apigateway]
   KV_MODE = json
   TIME_PREFIX = "eventTime":"
   TIME_FORMAT = %Y-%m-%dT%H:%M:%S.%3NZ
   ```
   ```ini
   # local/eventtypes.conf
   [oci_apigateway]
   search = sourcetype=oci:apigateway
   ```
   ```ini
   # local/tags.conf
   [eventtype=oci_apigateway]
   network = enabled
   communicate = enabled
   ```

3. **Restart** if you changed `props.conf` (required — it affects the
   indexing/parsing pipeline). `eventtypes.conf` and `tags.conf` changes
   are reloaded by Splunk automatically and don't need one.

4. If you're managing this centrally via a deployment server, put the
   same `local/*.conf` files in a dedicated app in your deployment-apps
   directory (or use an app-layering/merge strategy) rather than hand-
   editing on each forwarder, so the customization survives re-pushes.

**Why `local/` isn't shipped in the `.spl`:** Splunkbase/AppInspect
requires all distributed config to live under `default/` — a package
that ships a populated `local/` fails vetting (that content is meant to
be per-environment, admin-created state, not something a vendor
distributes). This has no effect on your ability to create and populate
`local/` yourself after install; it only means this TA can't pre-seed it
for you.
