Astelia Add-on (TA-astelia)
===========================

Pulls your Astelia organization's data from the Astelia public REST API into
Splunk Enterprise or Splunk Cloud Platform on a polling interval. No data is
pushed from Astelia; the add-on runs where modular inputs run (a search head,
an IDM, or a heavy forwarder) and needs outbound HTTPS to your organization's
API URL.

Inputs
------
* Astelia Audit Logs (sourcetype astelia:audit) - every product action in the
  organization (who changed what, when), oldest first, delivered at least once.
  The add-on stores the API cursor in the KV store between polls and drains
  every new event on each run. Tagged for the CIM Change data model
  (Auditing_Changes): user, object, object_category, object_id, status,
  vendor_product and a normalized action are provided at search time; the raw
  Astelia action is kept as astelia_action.
* Astelia Connector Health (sourcetype astelia:connector) - one event per
  connector per poll with its health verdict (status: healthy / stale / error
  / pending) and the reason. Every poll is a complete snapshot, so the newest
  event per connector is its current state, and a connector that stops
  appearing has been removed.

Setup
-----
1. In Astelia, open Settings > API Keys and create a key with Read permission.
   Note your organization's API URL (https://api.<tenant>.astelia.io).
2. In Splunk, open the add-on > Configuration > Astelia Organization > Add.
   Enter a name, the API URL and the key. Saving verifies the key against the
   API and fails with a message if it is rejected or unreachable.
3. Optional: set a proxy under Configuration > Proxy, and the log level under
   Configuration > Logging.
4. Open Inputs > Create New Input and add an Audit Logs input and a Connector
   Health input. Pick the organization, the index and the interval (300s is a
   reasonable default; 60s for near-real-time).

Searches
--------
Audit trail:
  sourcetype="astelia:audit" | table _time user astelia_action object object_category result
CIM (Change data model):
  | datamodel Change Auditing_Changes search | search sourcetype="astelia:audit"
Current connector state:
  sourcetype="astelia:connector" | stats latest(status) as status latest(status_reason) as reason latest(_time) as seen by id name type
Alert on unhealthy connectors:
  sourcetype="astelia:connector" earliest=-15m | stats latest(status) as status by id name | search status="error" OR status="stale"
Deduplicate audit events after a retried poll:
  sourcetype="astelia:audit" | dedup id

Requirements
------------
* Splunk Enterprise 9.x or 10.x, or Splunk Cloud Platform (Victoria or
  Classic). Python 3.9 or 3.13 runtime (python.required is declared).
* Install on the instance that runs modular inputs: a search head, a heavy
  forwarder, or the IDM on Splunk Cloud Classic. Not needed on indexers.
* Outbound HTTPS (443) from that instance to your Astelia API URL
  (https://api.<tenant>.astelia.io), directly or through the configured proxy.
  This add-on calls only that external source; nothing else leaves Splunk.
* KV store enabled (default) - the audit-log cursor is stored in the
  ta_astelia_checkpoints collection.
* An Astelia API key with Read permission.

Troubleshooting
---------------
* Saving an organization fails with "Astelia rejected this API key": the key
  is invalid, revoked, or was created without Read permission. Create a new
  key in Astelia > Settings > API Keys.
* Saving fails with "Could not verify the key against ...": the instance
  cannot reach the API URL. Check the URL (https only, no path), DNS, egress
  firewall rules, and Configuration > Proxy.
* An input runs but no events arrive: search
  index=_internal source=*ta_astelia* for the input's log, and raise the
  level under Configuration > Logging. A 429 in the log is the API rate limit
  (the add-on backs off); a 503 means key verification was temporarily
  unavailable and is retried.
* Audit events stop after changing an input: the checkpoint belongs to the
  input name. Deleting and re-creating an input with the same name reuses
  its checkpoint; create it under a new name to start from "Start from".
* The monitoring dashboard in the add-on shows events ingested per input.

Notes
-----
* Delivery is at least once. If a poll fails after some events were written,
  the next poll re-reads that page; dedup on the stable id field at search time.
* Changing an input's organization or removing the checkpoint restarts the feed
  from the "Start from" timestamp, or from the oldest available event (Astelia
  keeps 12 months of audit history).
* The API rate-limits per organization (429 with Retry-After); the add-on backs
  off and resumes automatically. A 503 from the API means the key could not be
  verified right now and is retried, not treated as an invalid key.
* Requires Python 3.9 or later on the Splunk instance (Python 3.13 supported).

Release notes
-------------
0.1.0 - Initial release: audit logs and connector health inputs, CIM Change
        mapping for audit events.

Support
-------
support@astelia.io
