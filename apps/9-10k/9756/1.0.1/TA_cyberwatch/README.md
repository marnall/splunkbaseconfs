# Cyberwatch Add-on

Collects assets, vulnerabilities, compliance findings and security issues from
the Cyberwatch API and normalizes vulnerabilities to
the Splunk Common Information Model.

One event per asset and CVE, which is the grain the Vulnerabilities data model
expects, so Enterprise Security works on the data without a summary index or a
scheduled search in between.

## Compatibility

| | |
|---|---|
| Splunk Enterprise | 10.4 and above — built and verified on 10.4.2 |
| Splunk Cloud Platform | Victoria and Classic |
| Cyberwatch | API v3, verified against 15.8.3 |
| Splunk CIM | 8.5 — Vulnerabilities data model |
| Python | 3.9 or 3.13, declared with `python.required` |

`python.required` needs Splunk 10.2 or above, which 10.4 covers. Earlier
releases ignore it and fall back to `python.version`, which the add-on also
declares.

Cyberwatch must expose its v3 API and you need an API user with read access to
the scope you intend to collect.

## What it collects

Thirteen inputs, each added and scheduled on its own.

| Input | Sourcetype | One event is | Default interval |
|---|---|---|---|
| Assets | `cyberwatch:asset` | an asset, with OS, groups, environment, counts | 1 h |
| Agents | `cyberwatch:agent` | a Cyberwatch agent | 1 h |
| Nodes | `cyberwatch:node` | a Cyberwatch node | 1 h |
| Asset groups | `cyberwatch:group` | an asset group | 24 h |
| Operating systems | `cyberwatch:operating_system` | an OS, with its end-of-life date | 24 h |
| Discoveries | `cyberwatch:discovery` | a network discovery | 1 h |
| Discovery assets | `cyberwatch:discovery_asset` | a host found by discovery | 1 h |
| Application scans | `cyberwatch:application_scan` | an application scan | 1 h |
| Vulnerabilities | `cyberwatch:vulnerability` | **one asset and one CVE** | 24 h |
| Compliance findings | `cyberwatch:compliance_finding` | **one asset and one rule** | 24 h |
| Security issues | `cyberwatch:security_issue` | a security issue | 24 h |
| CVE catalog | *none* | — fills a KV store lookup | 24 h |
| Compliance rule catalog | *none* | — fills a KV store lookup | 24 h |

The two catalog inputs **index nothing**. They keep reference data in the KV
store so a CVE present on two hundred assets does not repeat its description two
hundred times. Their activity is in `_internal`, sourcetype `ta:cyberwatch:log`.

Browse them directly:

```spl
| inputlookup cyberwatch_cve_lookup
| inputlookup cyberwatch_compliance_rule_lookup
```

### Volume

One vulnerability event per asset and CVE. Size the
index accordingly, and enable only the inputs you use.

After the first run the Vulnerabilities input only fetches assets Cyberwatch has
re-analysed since, so later runs are cheaper.

## Install

**Splunk Enterprise.** Install the package, then restart Splunk. The restart is
required: the add-on ships index-time settings.
On a distributed deployment, data collection runs on a heavy forwarder or a search-head and the
add-on must also be present on the search heads and indexers for the parsing and
CIM knowledge objects.

**Splunk Cloud Platform.** Install from Splunkbase. On a distributed deployment,
data collection runs on a heavy forwarder or an Inputs Data Manager, and the
add-on must also be present on the search heads and indexers for the parsing and
CIM knowledge objects.

The add-on grants no capability to any role. Roles that need to read the data
need access to the index you choose.

## Configuration

### 1. Account

**Configuration > Accounts > Add**. One account per Cyberwatch instance.

| Field | |
|---|---|
| Cyberwatch URL | instance root, for example `https://cyberwatch.example.com`, no path |
| API key / Secret key | created under **Profile > API keys** on the Cyberwatch interface. Read access to the whole scope you collect |
| CA certificate file | absolute path to the PEM holding the authority that signed your Cyberwatch certificate |
| Disable TLS verification | leave off |

The account is checked against the instance when you save it. A wrong URL or a
revoked key is reported on the form, not hours later in a log.

**About the CA certificate.** Most on-premises Cyberwatch instances present a
certificate signed by an internal authority, so this is the usual case rather
than the exception. Retrieve it with:

```bash
echo | openssl s_client -connect cyberwatch.example.com:443 -showcerts 2>/dev/null \
  | openssl x509 -outform PEM > /opt/splunk/etc/auth/cyberwatch-ca.pem
```

If your certificate is signed by a corporate authority, supply that authority's
PEM instead of the server certificate.

Disabling verification is a separate, explicit choice. When it is on, the API
key and secret key travel over a connection that is not protected against
interception, and the add-on writes a warning on every run.

### 2. Proxy and logging

**Configuration > Proxy** and **Configuration > Logging**, if you need them.

### 3. Inputs

**Inputs > Create New Input**, one per type. Each carries its own interval,
index and account.

Start with **Assets** and **Vulnerabilities**. Add **CVE catalog** to enrich
vulnerability events with the CVE description, CWE and EU Vulnerability Database
identifier — see below.

The CVE catalog has a **Scope**: *Active on my estate only* (a few thousand CVEs)
or *All known CVEs* (several hundred thousand). Start with the first.

## CIM mapping

`cyberwatch:vulnerability` is tagged `report` and `vulnerability`, the pair the
Vulnerabilities data model is constrained on.

| CIM field | Source | Present |
|---|---|---|
| `dest` | asset hostname, or first address | always |
| `dvc` | the Cyberwatch instance | always |
| `cve` | CVE code | always |
| `cvss` | CVSS base score | always |
| `severity` | CVSS score banded per [CVSS v3.1](https://www.first.org/cvss/v3.1/specification-document) | always |
| `signature` | CVE code | always |
| `signature_id` | CVE code | always |
| `vendor_product` | `Cyberwatch` | always |
| `category` | CWE identifier | **CVE catalog input** |
| `vendor_severity` | Cyberwatch `level_*`, verbatim | **CVE catalog input** |
| `xref` | `EUVD:<id>` | **CVE catalog input** |

The three fields on the right come from the KV store lookup and are empty until
the CVE catalog input has run. This is not an oversight: a Splunk lookup empties
its destination field when it does not match, so a field cannot both come from a
lookup and keep a fallback. Each field therefore has one source, chosen on
whichever can always answer.

`severity` is banded from the score rather than taken from Cyberwatch's own
rating, which is what CIM asks for — it defines `severity` as the normalized
value and `vendor_severity` as the vendor's own wording.

Non-CIM fields worth knowing: `cyberwatch_epss`, `cyberwatch_triage_status`,
`cyberwatch_active`, `cyberwatch_prioritized`, `cyberwatch_detected_at`,
`cyberwatch_fixed_at`, `cyberwatch_environmental_score`, and from the catalog
`cyberwatch_cve_content`, `cyberwatch_cwe`, `cyberwatch_exploit_code_maturity`,
`cyberwatch_exploitable`.

### Event time

`_time` is the **collection time**, not the detection date. Each run is a
snapshot: a vulnerability found six months ago is reported again today, still
open, and stamping it with its detection date would pile identical events onto
one instant and leave every recent-window dashboard empty. The detection, fix and
publication dates are on the event as `cyberwatch_detected_at`,
`cyberwatch_fixed_at` and `cyberwatch_published`.

## Troubleshooting

Everything the add-on does is in `_internal`:

```spl
index=_internal sourcetype="ta:cyberwatch:log"
| table _time log_level file message
```

Each run ends with a line worth reading:

```
finished in 7.2s: written=7419 detail_calls=1 skipped_unchanged=9 skipped_empty=3
```

| Symptom | Cause |
|---|---|
| `HTTP 401` on save or on collection | API key or secret key wrong, or revoked. Check **Profile > API keys** on Cyberwatch |
| `HTTP 403` | the API user lacks read access to part of the scope |
| `TLS verification failed` | supply the CA certificate of your instance, as above |
| `did not answer within …` | Cyberwatch unreachable from the Splunk host, or a proxy is needed |
| No events, `skipped_unchanged` equals the asset count | normal: nothing has been re-analysed since the last run |
| `category`, `vendor_severity` or `xref` empty | the CVE catalog input has not run |
| `severity` is `unknown` | Cyberwatch has not scored that CVE. Check `cvss` on the event |
| Events land hours out | the add-on was updated without restarting Splunk; index-time settings need a restart |
| Collection stops with `refusing calls for rate limiting` | lower the frequency or reduce the number of enabled inputs |

Validate the shipped configuration at any time:

```bash
splunk btool props list --app=TA_cyberwatch --debug
```

## Known limitations

- Vulnerability events include findings Cyberwatch has already marked fixed
  (`cyberwatch_active=false`). They carry `cyberwatch_fixed_at`. Filter them out
  if you only want current exposure.
- The CVE catalog in *Active on my estate only* scope covers CVEs active
  somewhere on the estate, so events about already-fixed vulnerabilities are not
  enriched.
- Compliance findings and inventory carry no CIM tag.
- Asset data is not mapped to a data model.

## Support

**support@process-it.fr**

## Licence and attribution

Apache License 2.0. Author: Thomas Dussossoy, Process-IT.

Cyberwatch is a trademark of its owner. This add-on is built by Process-IT for
use with Cyberwatch and is neither produced nor endorsed by Cyberwatch. Its
icons reproduce the Cyberwatch mark, to identify the product this add-on
integrates with.
