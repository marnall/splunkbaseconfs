# vCISO Threat Intel - Splunk app

Pull your **vCISO personal IOC feed** (uploads, saved-from-posts, subscriptions,
enriched verdicts) straight into Splunk as indicators, with dashboards and a
KV-store lookup for threat matching. No Enterprise Security required.

## What you get

- **Modular input** that polls `https://<host>/api/feed/<key>?format=json` on an
  interval, checkpointed on `created_at` so each run only pulls new IOCs.
- Indicators land in the **`vciso_iocs`** index, sourcetype **`vciso:ioc`**, with
  `_time` set to when the IOC was added.
- **Public community data (no key needed).** The *vCISO Community Intel (public)*
  input pulls the open datasets everyone on the website sees - ransomware victims
  (`/api/victims`), news/advisories/CVEs/darkweb items (`/api/incidents`), and
  darkweb-marketplace metadata (`/api/darkweb/markets`) - into the same index under
  sourcetype `vciso:public` (a `dataset` field separates victim / news / market).
  Free, for the community. The darkweb data is metadata only: no .onion, no stolen data.
  **Optional key:** leave the input's `feed_key` blank for public data only; add your
  `vciso_` key to ALSO pull your personal IOC feed in the same input (dataset=ioc).
- **Dashboards**
  - *vCISO - Overview*: totals, malware-attributed count, by type, by source,
    additions over time, top malware / threat types (your personal IOC feed).
  - *vCISO - Community Intel*: ransomware victims (top groups/countries, timeline,
    table), news/advisories by category, darkweb listings - the whole platform's intel.
  - *vCISO - IOC explorer*: filter by type/source/value, browse the table.
- **KV-store lookup `vciso_iocs_kv`** (rebuilt every 10 min) for correlation:
  ```
  index=firewall | lookup vciso_iocs_kv value AS dest_ip OUTPUT ioc_type threat_type malware source
  | where isnotnull(ioc_type)
  ```

## Install

1. Get your feed key: vCISO profile -> **Personal SIEM Feed** -> *Generate feed key*
   (it starts with `vciso_`).
2. Install the app:
   - **Splunk Web**: Apps -> *Manage Apps* -> *Install app from file* -> upload
     `vciso_threat_intel.spl`, then restart if prompted; **or**
   - **Manual**: copy the `vciso_threat_intel/` folder into
     `$SPLUNK_HOME/etc/apps/` and restart Splunk.
3. Configure the input: **Settings -> Data Inputs -> vCISO Threat Intel Feed ->
   New**. Set:
   - *Feed base URL*: `https://vciso.au` (or your instance)
   - *Feed key*: your `vciso_...` key
   - *Interval*: `300` (seconds), *Index*: `vciso_iocs`
4. Open the **vCISO - Overview** dashboard. Data appears within one interval.

## Notes

- Rotating the feed key in your profile instantly revokes the old one - update the
  input afterwards.
- If your environment manages indexes centrally, delete `default/indexes.conf` and
  point the input's `index =` at an existing index.
- Standard-library Python only; runs on Splunk's bundled Python 3 (Splunk 8/9).
