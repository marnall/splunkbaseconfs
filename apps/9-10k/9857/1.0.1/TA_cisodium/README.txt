Cisodium Add-on
===============

Version 1.0.1

The Cisodium Add-on brings the records of a Cisodium information security
management platform into Splunk: incidents, vulnerabilities, risks, assets,
security controls and the platform's audit log. Every create, change and
deletion of a record arrives as a JSON event with the record's full state, so
Splunk always has the current picture and its history.

The add-on calls an external data source: the Cisodium tenant you configure,
over HTTPS, with an API key you create in Cisodium. Nothing is sent to Cisodium
apart from the requests themselves.


Requirements
------------

* Splunk Enterprise 9.2 or later, or Splunk Cloud Platform.
* A Cisodium tenant, reachable over HTTPS from the Splunk instance that runs the
  inputs (a heavy forwarder, an Inputs Data Manager, or a single instance).
* The KV store enabled on that instance (the inputs keep their position there).
* A Cisodium API key with the "SIEM Feeds (read)" scope.


Where to install
----------------

* Search heads: install, for the field extractions and CIM mappings. Do not
  create inputs on a search head cluster.
* Heavy forwarder / IDM / single instance: install and configure the account
  and the inputs here.
* Indexers: not needed (all extractions happen at search time).


1. Create an API key in Cisodium
--------------------------------

Cisodium → Settings → Integrations → Splunk → "Splunk Add-on" tab →
"Create API key for Splunk". The key is shown once; copy it. It starts with
cso_ and carries the "SIEM Feeds (read)" scope, which reads the feeds and
nothing else. You can also create one under Settings → Integrations →
API Keys; choose that scope. Keys can be restricted to the IP addresses Splunk
connects from, rate-limited, given an expiry date, and revoked at any time.


2. Add the account in Splunk
----------------------------

Apps → Cisodium Add-on → Configuration → Cisodium accounts → Add:

* Name: any name, e.g. acme_prod
* Cisodium URL: the address you open Cisodium at, e.g. https://acme.cisodium.com
* API key: the key from step 1 (stored encrypted in Splunk's credential store)

The add-on checks the URL and key with Cisodium before saving, and shows
Cisodium's own reason if it refuses them.

If Splunk reaches the Internet through a proxy, set it on the Proxy tab first.


3. Create inputs
----------------

Inputs → Create New Input → Cisodium feed. One input per feed:

  Feed              Sourcetype              CIM data model
  ----------------  ----------------------  ------------------------------------
  Incidents         cisodium:incident       Ticket Management (Incident)
  Vulnerabilities   cisodium:vulnerability  Vulnerabilities
  Risks             cisodium:risk           -
  Assets            cisodium:asset          Inventory (Network)
  Security controls cisodium:control        -
  Audit log         cisodium:audit          Change, Authentication

* Interval: how often to ask for changes (default 300 seconds).
* Index: where the events go.
* Start date (optional): only records changed since this date on the first
  run. Leave it empty to copy the whole history. After the first run the input
  continues from where it stopped, whatever the start date says.
* Page size (optional): records per request, 1–1000 (default 500).


What the events look like
-------------------------

One event per change of a record, as JSON. Common fields:

  id            the record's id in Cisodium (stable across changes)
  ref           its human-readable code (INCD-…, VULN-…, RISK-…, AST-…, CTRL-…)
  event_time    when it changed (this is _time)
  deleted       true once the record was deleted in Cisodium
  fingerprint   a digest of the record's content without its timestamps
  cisodium_url  a link to the record in Cisodium ("Open in Cisodium" in the
                event actions menu)

The latest state of every record:

  sourcetype="cisodium:vulnerability" | dedup id | where deleted="false"

Some Cisodium jobs re-save records without changing them (for example a cloud
asset sync); each such save sends the record again with the same fingerprint.
To see only real changes:

  sourcetype="cisodium:asset" | dedup id fingerprint

A change reaches Splunk about two minutes after it is made in Cisodium, plus
the input's interval.


Troubleshooting
---------------

Logs: index=_internal source=*ta_cisodium*  (one log file per input), and the
add-on's Monitoring dashboard.

* "Cisodium rejected the API key (HTTP 401)": the key is wrong, revoked or
  expired, or its IP allowlist does not include this Splunk server.
* "not allowed to read this data (HTTP 403)": the key lacks the
  "SIEM Feeds (read)" scope.
* "does not answer on /api/v2/siem (HTTP 404)": the URL is not the Cisodium
  tenant, or the tenant runs a Cisodium version without SIEM feeds.
* "Cloudflare in front of Cisodium refused the request": the request was
  blocked before it reached Cisodium; send the Ray ID to Cisodium support.
* "rate-limiting this API key (HTTP 429)": the input backs off and continues on
  its next run; raise the key's rate limit in Cisodium if it persists.

To read a feed again from the start, delete the input and create it again
(deleting an input deletes its checkpoint).


Dependencies (bundled in lib/)
------------------------------

splunktaucclib 8.2.0, solnlib 7.0.0, splunk-sdk 2.1.1, requests 2.32.5,
urllib3 1.26.20, PySocks 1.7.1 and their pure-Python dependencies.


Support
-------

support@cisodium.com — https://cisodium.com


Release notes
-------------

1.0.1
* Packaging for Splunkbase: app.manifest no longer states Splunk platform or
  CIM versions (Splunkbase lists the supported versions itself); the app
  icons are the Cisodium favicon. No change to what the add-on collects.

1.0.0
* First release: six feeds, CIM mappings for Vulnerabilities, Ticket
  Management, Inventory, Change and Authentication, account validation on save,
  KV store checkpoints, proxy support.
