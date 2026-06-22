# Demo data input using a URL lookup

## Shipped with the TA (build / Splunkbase)

The package includes **`default/lookups/demo_phishiq_urls.csv`** with a few **benign** URLs (e.g. Google, Apple, Microsoft, Wikipedia, Splunk) and **`[demo_phishiq_urls]`** in **`default/transforms.conf`**. After install you can run:

```spl
| inputlookup demo_phishiq_urls | fields url
```

(from the **PhishIQPlus** app context — see below).

## Optional: larger lab list (repo only)

Under **`README/examples/`** there is a longer CSV (**48** URLs) for local testing. To use it instead of the shipped file, copy over the installed lookup and restart Splunk:

```bash
cp README/examples/demo_phishiq_urls.csv "$SPLUNK_HOME/etc/apps/phishiq_ta/lookups/demo_phishiq_urls.csv"
```

(Or merge into **`local/transforms.conf`** only if you use a different filename.)

---

## Verify in Search **from the PhishIQPlus app** (important)

   Lookups live in `phishiq_ta`. If you run `inputlookup` from the default **Search & Reporting** app, Splunk resolves lookups in the **search** app namespace and you get errors or zero rows.

   - Open **Apps → PhishIQPlus Technical Add-on**, then use **Search** from that app (or set the app context to PhishIQPlus), and run:

```spl
| inputlookup demo_phishiq_urls
| fields url
```

The modular input’s REST searches use this TA’s app id so `inputlookup` in **Source Search** works without duplicating transforms in `search`.

**Enriched events in `main`:** use a time range that includes the modular input runs (e.g. **Last 24 hours**). A search that starts with `index=main` is **not** the same as `| inputlookup`.

**Troubleshooting the modular input:** in `index=phishiqplus_internal`, check `event_type=run_summary` field **`rest_namespace_app`**. It should be **`phishiq_ta`**. If it were `search`, TA lookups would not resolve.

---

## Data input settings (PhishIQPlus URL Enrichment)

| Field | Value |
|--------|--------|
| **Mode** | `dynamic` |
| **Source Search (dynamic)** | `| inputlookup demo_phishiq_urls | fields url` |
| **Source URL Field (dynamic)** | `url` |
| **Source Search Limit (dynamic)** | `100` |
| **Source Search Earliest (dynamic)** | `-24h` |
| **Source Search Latest (dynamic)** | `now` |
| **Emit Source Event Context** | unchecked (lookup rows are not real source events) |
| **Index** | `main` |
| **Sourcetype** | `phishiq_enriched` |
| **Telemetry Enabled** | checked |
| **Internal Index** | `phishiqplus_internal` |
| **Internal Sourcetype** | `phishiqplus:internal` |
| **Interval** | `60` for demos |

---

## Editing the list

- **Shipped file:** edit `$SPLUNK_HOME/etc/apps/phishiq_ta/lookups/demo_phishiq_urls.csv` (or override with **`local/lookups`** / merge in **`local/transforms.conf`** if you use another filename), then restart Splunk.
- **From source:** edit `default/lookups/demo_phishiq_urls.csv` in the repo and rebuild the package; or use the larger **`README/examples/demo_phishiq_urls.csv`** and copy over **`lookups/demo_phishiq_urls.csv`** on the instance.

---

## Security

Lab / demonstration only. Do not treat this list as a production control.
