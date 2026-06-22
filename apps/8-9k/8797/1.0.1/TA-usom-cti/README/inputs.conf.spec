[usom_ti://<name>]
* Modular input that periodically fetches IOCs (IP, domain, URL) from the
* USOM (Turkey's TR-CERT) public threat-intelligence API and writes them
* into Splunk lookups for correlation.

criticality_threshold = <integer>
* MAXIMUM USOM criticality_level to include. Per the USOM OpenAPI spec,
* 1 = most critical and 10 = least critical, so threshold=3 keeps only
* the top 3 most critical levels and threshold=10 keeps everything.
* IOCs with criticality_level greater than this value are dropped.
* Default: 7

types = <comma-separated string>
* Subset of USOM IOC types to fetch. Any combination of: ip, ip6, ip6net,
* domain, url. Whitespace is ignored.
* Default: ip,ip6,ip6net,domain,url

interval = <integer>
* Number of seconds between polls.
* Default: 14400 (4 hours)

api_base_url = <url>
* Base URL of the USOM threat-intelligence list endpoint. Override only for
* testing against a mock server or a future TR-CERT mirror. Note: the
* legacy www.usom.gov.tr domain is being retired in favour of
* siberguvenlik.gov.tr, which serves the same API surface.
* Default: https://siberguvenlik.gov.tr/api/address/index

request_delay_seconds = <integer>
* Polite delay between paginated requests against the USOM API. Increase if
* your environment is rate-limited or you want to be gentler on the upstream.
* Default: 5

http_proxy = <url>
* Optional HTTP/HTTPS proxy URL for environments that egress through a
* corporate proxy. Example: http://user:pass@proxy.example.com:8080
* Default: (empty)

stats_index = <index>
* Splunk index that receives one stats event per fetch cycle, with
* sourcetype usom_ti:stats. The default `_internal` is licence-free
* and the conventional home for app operational data; override to a
* custom index if your role layout requires it.
* Default: _internal

setup_debug = <boolean>
* When true, the setup REST handler (bin/setup_rest.py) raises its log
* level to DEBUG and emits per-request HTTP traces, splunkd round-trip
* status codes, and threatlist toggle decisions to
* $SPLUNK_HOME/var/log/splunk/ta_usom_cti.log. Leave off for normal
* operation; turn on temporarily to diagnose a save that did not stick.
* Default: false

# Note: when this input is deployed across a search head cluster it
# automatically runs only on the captain; non-captain members skip the
# fetch cycle. Standalone instances always run.
