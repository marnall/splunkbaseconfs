# HoneyLabs Intelligence

Query a honeypot dataset from Splunk, enrich the IP addresses already in your
events with what its sensors observed, and index threat feeds of active
exploiters and malware staging infrastructure.

HoneyLabs runs open-source honeypot sensors on the public internet. Every
connection they receive is unsolicited, so every observation is an unsolicited
scan, probe, brute-force attempt or exploit. This app puts that in reach of
your searches.

- Author: HoneyLabs
- Version: 1.1.0
- Works on: Splunk Enterprise and Splunk Cloud 10.0+, search heads
- Tested against Splunk 10.4.2. The app declares `python.required = 3.13`,
  which is what current Splunk expects; support for 9.x is not claimed because
  it has not been tested.
- License: Apache-2.0
- An account is optional for enrichment and the feeds, and required for the
  dataset queries. Keys are free.

## What it gives you

**Two search commands.** `| honeylabs` annotates addresses you already have.
`| honeylabssearch` queries the dataset itself.

### Enrichment: `| honeylabs`

Annotate any event that carries an IPv4 address:

```
index=firewall | honeylabs field=src_ip
| where honeylabs_events > 0
| table _time src_ip honeylabs_verdict honeylabs_events honeylabs_asn_org honeylabs_reference
```

Fields written back, all prefixed `honeylabs_` (change it with `prefix=`):
`verdict` (the sentence a human reads), `verdict_key` (the stable machine
value to write alerts against), `network_type`, `events`, `first_seen`,
`last_seen`, `country`, `asn`, `asn_org`, `rdns`, `top_port`, `ports`,
`exploit_hits`, `reference`.

### Dataset queries: `| honeylabssearch`

A generating command, so it opens a search rather than decorating one. Nine
modes, each answering a question that does not start from an address in your
own index:

```
| honeylabssearch mode=events dest_port=8080 limit=200
| honeylabssearch mode=payloads query="/cgi-bin/authLogin.cgi"
| honeylabssearch mode=cve cve="CVE-2024-4577"
| honeylabssearch mode=ioc ioc="185.220.101.0/24"
| honeylabssearch mode=asn asn=14061
| honeylabssearch mode=attackers by=country
| honeylabssearch mode=timeline bucket=hour
| honeylabssearch mode=fingerprint fp_type=ja4 fingerprint="t13i131000_..."
| honeylabssearch mode=population fp_type=ja4 fingerprint="t13i131000_..."
```

`mode=events` returns raw sensor events with every field the sensor recorded,
including URL path, request headers, user agent, TLS and SSH fingerprints.
`mode=payloads` is a literal substring search over captured request text, which
is how you find everyone who sent a particular exploit string. `mode=ioc` takes
a CIDR range or a domain as well as a single address.

`since` and `until` default to the search's own time range, so the time picker
applies. Both can be set per search when a panel needs a fixed window. Results
are one Splunk event per record, unprefixed, because they are HoneyLabs' events
and cannot collide with your fields.

This command needs an API key. It spends one credit per row returned, so
`limit` is the cost dial.

**Threat feeds.** Two inputs, shipped disabled, index active exploiter
addresses and captured malware staging URLs on a schedule. Enable them under
*Settings > Data inputs > HoneyLabs threat feed*. They need no credentials.

**Feed field names.** The malware-infrastructure feed has a `host` column,
which collides with Splunk's own `host` metadata field. The input renames it to
`indicator_host` on the way in, so a search joining on it gets the indicator
rather than the name of the machine that indexed it.

**A dashboard.** *Triage* ranks your own traffic by what the sensors
already watched those addresses do. Its first two panels match against the
indexed feeds and call nothing, so they run as soon as the page opens. The
third asks the API about your busiest talkers and spends a credit per address,
so it stays switched off until you turn it on.

**A second dashboard.** *Explorer* is the dataset on its own, with no
reference to your traffic: attack volume over time, who is probing, the request
paths they are asking for, a payload hunt and a CVE check. Nothing on it runs
until you press Submit, because every panel spends credits.

## Running Enterprise Security?

Use ES's own threat intelligence framework instead of the feed inputs here, so
indicators reach correlation searches and risk scoring rather than only being
searchable. Add a URL-based threat source pointing at:

```
https://honeylabs.net/feed/exploiters.csv
  Fields: ip:$1,description:$7    Skip header lines: 1    Delimiter: ,

https://honeylabs.net/feed/malware-infrastructure.csv
  Fields: url:$1,description:$6   Skip header lines: 1    Delimiter: ,
```

Full walkthrough: <https://honeylabs.net/integrations/splunk-es>

The search command in this app is useful alongside that, for enriching on
demand rather than matching against a downloaded list.

## Setup

There is none to do. The app is usable the moment it is installed: no gate, no
required field. The setup page exists only to store an API key, and it sits in
the app's navigation bar next to the dashboard.

- **No key.** The `| honeylabs` command works anonymously at a lower daily cap.
- **A key.** Free, from <https://honeylabs.net/dashboard>. Raises the cap and
  attributes usage to your account. Stored through Splunk's
  `storage/passwords`, encrypted at rest, never written to a `.conf` file.

## What leaves your deployment

This matters, so it is stated exactly.

**The search command sends IP addresses to `honeylabs.net`.** When a search
runs `| honeylabs field=src_ip`, the values of that one field are collected,
de-duplicated and sent over HTTPS to the HoneyLabs API to be looked up.

**Nothing else is transmitted.** Not the raw event, not any other field, not
your index, host, source or sourcetype names, not your Splunk version or
licence, not the search string.

**Private space never leaves.** Private, loopback, link-local, multicast and
otherwise reserved addresses are filtered out locally before the request is
built. A search over a firewall index full of RFC1918 traffic sends only the
public addresses in it.

**The feed inputs send nothing about you.** They are ordinary HTTPS downloads
of a public file.

**What HoneyLabs retains.** Usage events for quota accounting: which account
made a request, which endpoint, how long it took, how many rows it returned.
Request and response bodies are not logged, so the addresses you looked up are
not retained as belonging to you. Full policy:
<https://honeylabs.net/privacy>

**If none of that is acceptable**, use the feed inputs alone and never run the
search command. The feeds give you the indicator list with no outbound
disclosure at all.

## Daily limits

Enrichment is metered in credits, one per address looked up. The command tells
you when it matters and stays quiet when it does not: it warns once per search
if the run left you short, and says nothing while there is headroom.

Anonymous use has the smallest allowance, a free account raises it, and paid
plans raise it further and widen the history window from days to months. The
app never blocks a search over quota; it annotates what it can and passes
the rest through with `honeylabs_error` set.

## Support

- Setup guide: <https://honeylabs.net/integrations/splunk-es>
- API docs: <https://honeylabs.net/docs>
- Email: info@honeylabs.net

## Third-party software

Bundles the Splunk SDK for Python (`splunklib`), Apache-2.0, copyright Splunk
Inc. See `LICENSE-splunk-sdk.txt`. No other third-party code is included and
the app has no external Python dependencies.

## Release notes

### 1.1.0

Adds `| honeylabssearch`, a generating command that queries the honeypot
dataset directly. Until now the app could only answer questions that began
with an IP address already sitting in your own index, which left most of what
the sensors record out of reach from Splunk. The new command covers raw sensor
events with every recorded field, literal substring search over captured
request payloads, CVE exploitation, ASN profiles, attacker rankings, attack
volume over time, and TLS, JA4, JA4H and SSH fingerprint searches. `mode=ioc`
also accepts a CIDR range or a domain, which the enrichment command cannot.

`since` and `until` default to the search's own time range, so the time picker
drives the query rather than being ignored.

Adds a second dashboard, *Explorer*, covering the dataset on its own
terms. Nothing on it runs until submitted, because every panel spends credits.

The three views are now named Triage, Explorer and Setup rather than
repeating the app name. Splunk draws its collapsed sidebar icon from the
first letter of a view's label, so the old names gave three identical `H`
buttons with no way to tell them apart.

Generated events now carry a `_raw` value. Without one the Events tab listed
the right number of rows with an empty event column, which reads as a broken
search even though every field was present and searchable.

Tables that link out to honeylabs.net now carry the URL as a column rather
than relying only on the cell drilldown. On Splunk 10.4.2 an external-link
drilldown is styled like a link and does not fire when clicked, which is a
platform behaviour rather than an app one, but a cell that looks clickable
and is not is worse than no link at all.

Attacker rankings arrive from the API as IPv4-mapped IPv6, carrying an
`::ffff:` prefix, while raw event searches return the plain dotted form. Both name the same host, but
Splunk does not know that, so a join against your own `src_ip` would have
matched nothing and reported no error. Addresses are normalised to the plain
form on the way in.

The enrichment command's warning text is now passed as a format argument
rather than as the format string. An upstream error containing braces, which
the API's validation errors do, would previously have raised inside the error
handler.

### 1.0.2

This release fixes a defect that left the app unusable after installation.

Versions 1.0.0 and 1.0.1 declared `is_configured = false` alongside a
`setup_view`, which is how Splunk is told that an app cannot be used until it
has been configured. Splunk therefore displayed its "app has not been fully
configured yet" page in place of every view in the app. Clearing that page
requires a write to `apps/local/honeylabs`, which the setup page never
performed, so saving an API key appeared to succeed while the dashboard and the
search view stayed out of reach. Users holding only the `user` role could not
clear it under any circumstances, because that write requires
`admin_all_objects` or `edit_local_apps`.

The app has no required configuration, so it no longer declares a `setup_view`.
Nothing is gated, and the setup page is reached from the app's navigation bar
alongside the dashboard.

Also fixed in this release:

- The dashboard's time range control was scoping the threat feed lookups in
  addition to your own events. Feed events are timestamped with the date the
  sensors last observed the indicator, which can be up to two weeks earlier, so
  at the default 24 hour range only 30 of the exploiter feed's 211 addresses
  were eligible to match. The feed subsearches now read the complete list, and
  the time range selects your own traffic only.
- The `honeylabs_error` field, documented as where a failed lookup reports its
  reason, was never populated. A spent quota or a rejected key produced empty
  columns and no explanation. The reason is now written to the events whose
  addresses went unanswered. An HTTP 4xx response also stops further requests
  for the remainder of the search, and a failed request no longer caches its
  addresses as misses, which previously left them unenriched even after a later
  request succeeded.
- The dashboard's live API panel ran automatically on every page load and could
  spend up to 100 credits each time. It is now off by default and runs when
  selected. This also keeps the dashboard within the three concurrent searches
  granted to the `user` role by default.

Other changes:

- The app is now named HoneyLabs Intelligence.
- The setup page and the dashboard link to each other.
- The README refers to the dashboard by its actual name.

Verified against Splunk Enterprise 10.4.2. AppInspect precert reports 0 errors,
0 failures and 0 future failures.

### 1.0.1

Version reported in the API user agent now comes from `app.conf` rather than a
constant that had drifted a release behind.

### 1.0.0

First release. Search command, two threat feed inputs, triage dashboard, setup
page.
