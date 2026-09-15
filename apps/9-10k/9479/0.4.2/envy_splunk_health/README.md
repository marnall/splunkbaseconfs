# Envy Splunk Health

**Which security detections can actually fire on your data?**

Most detection content matches raw vendor field names, not CIM. A rule only ever
produces a result if your events happen to carry the field names its author
assumed -- and nothing tells you which ones do. Envy Splunk Health answers that
from inside your own Splunk, read-only, alongside the data-collection traffic
light Splunk doesn't ship.

Built by **Envyously** (a platform of Envy Group, Inc. -- Pennsylvania). Envy Splunk
Health is the free front door to the **Envyously for Splunk** line: on-prem and
air-gapped Splunk tooling for the environments the cloud-only AI wave skips. Learn
more at **https://envyously.com/splunk**.

---

## Why it exists

Two failure modes, both quiet.

**Your data does not match what your detections expect.** Field mapping is the work
nobody finishes. A data model that never populates, or a rule waiting on a field
name you do not have, fails by returning nothing -- which looks exactly like "no
threats found".

**A feed stops arriving and nothing says so.** A sourcetype that was reliably
landing simply stops. The dashboards still look normal, the searches still run,
they just quietly return less truth every day.

This app makes both loud.

## Dashboards

- **CIM Gap Report** -- which CIM data models your data could actually drive, the
  core fields each one still needs, and a paste-ready `| rename` overlay that
  normalises on read. No re-ingest, no data-model rebuild.
- **Detection Coverage vs Your Data** -- how many of 2,909 community detections
  could fire on the field names you really have, which absent field costs you the
  most detections, and which of your sourcetypes feed anything at all. A detection
  counts as supported only when **one** sourcetype carries every field it needs;
  pooling fields across sourcetypes would claim coverage no single event has.
- **Data-Collection Health** -- every sourcetype as a traffic light by freshness,
  with explicit **STOPPED** detection.
- **Config & License Status** -- license usage by index, a 14-day burn trend, index health.
- **License Burn & Junk Finder** -- where your licensed GB actually go, and what's safe to drop.
- **Full Health Report** *(licensed)* -- the complete scorecard, SLA state, and remediation guidance.
- **Activate** -- license status + how to activate.

## No Enterprise Security required

The app references no data model, no `notable`, and neither
`SplunkEnterpriseSecuritySuite` nor `Splunk_SA_CIM`. It scores CIM compliance by
matching field names against its own shipped dictionary rather than accelerating
data models, so it returns a useful answer on a bare Splunk with nothing in it but
raw data.

## Honest about its own limits

Every scoring dashboard opens with a **scope panel**: the search head that
answered and its roles, the account it ran as (only indexes those roles can search
are counted), how many search peers it reached, and whether ES, Security
Essentials or the CIM add-on are present anywhere it can see. If yours run on a
different search head, the panel says so rather than letting a percentage be
mistaken for the whole estate.

Time windows are **snapped**, so the same question asked twice returns the same
answer. Sampling takes the most recent N events per sourcetype; a field that none
of those events carried is reported missing, and the sample size is yours to raise.

## What you get

| Tier | Includes | Requires |
|---|---|---|
| **Free** | CIM Gap Report, Detection Coverage, Data-Collection Health, Config & License Status, License Burn & Junk Finder -- all on **your own data**, out of the box | nothing |
| **Licensed** | **Full Health Report** (scorecard + SLA + remediation guidance) and the **scheduled STOPPED-feed alert** | a license key or signed offline token |

The free dashboards never call the license gate -- they always work. Only the
Full Health Report panels and the scheduled alert are gated, and they **fail closed**
to the free tier if a key is missing, lapsed, or invalid.

## Activation

Get an instant free 7-day key at **https://envyously.com/splunk/activate/**. For
**Splunk Cloud** or **air-gapped** Splunk you also receive a *signed offline token*
that the app verifies locally against an embedded public key -- **no outbound calls,
nothing leaves your perimeter.** See the **Activate** dashboard for steps.

## Privacy & security

- **Read-only, field names only.** The scoring dashboards read field *names* from
  sampled events plus Splunk's own `_internal` license logs. No field values are
  inspected, nothing is written, and nothing leaves the instance.
- **Your data never leaves.** Offline activation makes zero network calls. The
  optional online check sends **only the license key** to a single Envyously
  endpoint -- never events, never customer data -- and fails closed if unreachable.
- **No token minting from the app.** The shipped app carries only the *public*
  verification key.
- **Third-party content.** The detection-coverage tables are derived metadata only
  -- an opaque rule id, its platform, and the field names it references. No rule
  titles, no rule logic, no vendor names. Upstream rules are SigmaHQ content under
  the Detection Rule License 1.1.

## Support

Robert Ayers -- **support@envygroupinc.com** -- Envy Group, Inc., Plains, PA, US
Part of the Envyously for Splunk line: **https://envyously.com/splunk**
