# OPSWAT MetaDefender for Splunk — User Guide

This guide assumes you already have **Splunk** (Cloud or Enterprise) and **MetaDefender Core**
running. It covers installing the app and sending MD Core data to Splunk.

---

## 1. Install the app

**Splunk Cloud / Enterprise (from Splunkbase):**
Splunk Web → **Apps → Find More Apps** → search **"OPSWAT MetaDefender"** → **Install**
(sign in with your Splunk.com account). Restart if prompted.

**From file (air-gapped or pre-release):**
Splunk Web → **Apps → Manage Apps → Install app from file** → upload `opswat-mdcore-<version>.spl`
→ restart if prompted.

The app auto-configures its `opswat:mdcore:cef` sourcetype and field extractions — no setup screen.

---

## 2. Send MetaDefender Core data to Splunk

MD Core sends scan activity as **CEF over syslog**.

**On MetaDefender Core:** add a syslog connection and set its type to **Splunk**.
Point it at your Splunk syslog collector — typically **TCP/UDP/TCPS on port 1514** (directly, or via
Splunk Connect for Syslog / a Universal Forwarder).

**On the Splunk side:** make sure that syslog arrives with **`sourcetype = opswat:mdcore:cef`**
(set this in your SC4S mapping or the forwarder input). Pick any existing index to store it in.

---

## 3. Set the index and verify (Setup screen)

Open the app — it lands on **Setup**. There you:
1. **Choose the index** your MetaDefender data lands in and click **Save** (all dashboards then use
   it — no per-dashboard picking).
2. Click **Check now** to confirm `opswat:mdcore:cef` events are arriving (green ✓ / red ✗).

Then open **Executive Overview** — it should populate. (You can revisit **Setup** any time to change
the index.)

---

## 4. The dashboards

| Dashboard | Shows |
|---|---|
| Executive Overview | Prevention outcomes, trends, file types, threats |
| SOC Triage | Detection queue, submitters, source IPs |
| Blocked Files | Blocked/quarantined files, reasons, threat families |
| Deep CDR | Sanitization outcomes and failures |
| Metascan | Per-engine coverage, timing, agreement |
| Sandbox & Deep Analysis | Filescan.io verdicts |
| Workflows | Decision mix, top rules, config-change audit |
| Audit & Compliance | Inspection evidence, chain of custody |
| Security Enforcing Functions | Control-execution matrix |
| Data Volume & License | Ingest sizing |

Each dashboard has a **Time range** picker; the index is set once on the **Setup** screen.

---

## 5. Not seeing data?

- Confirm MD Core's Splunk syslog connection is **enabled** and reachable.
- Confirm events land with the exact sourcetype: `index=<index> sourcetype=opswat:mdcore:cef`.
- Make sure the dashboard's **Index** selector matches where the data is indexed.
- Widen the **Time range**.

Need help? https://www.opswat.com
