Veza Add-on for Splunk — Release Notes
==================================================

Version 0.2.0 (Beta)
--------------------

Renamed the app ID from TA-veza to veza and re-published as a new
Splunkbase listing. No functional changes to the modular inputs,
sourcetypes, or configuration.

Version 0.1.0 (Beta)
--------------------

Initial release. Ships two modular inputs that ingest data from the Veza
platform via the cursor-paginated /api/v1 export endpoints:

  - veza_events:     drains /api/v1/events/export
                     default sourcetype: veza:events
  - veza_audit_logs: drains /api/v1/system/audit/export
                     default sourcetype: veza:audit

Both inputs authenticate via the OAuth2 client_credentials grant,
checkpoint the server-provided cursor between runs, and deliver events
at least once.

Requirements
------------
  - Splunk Enterprise 9.0 or later, or Splunk Cloud Platform
  - Python 3.13 (Splunk-bundled interpreter)
  - Network reachability from the Splunk host to the Veza tenant's
    HTTPS endpoint
  - Veza OAuth2 client with the Auditor role (or a custom role with
    at least the events:view scope), created under Settings → OAuth
    in the Veza UI

Configuration
-------------
After installing, create one input per tenant under
Settings → Data inputs → Veza Events / Veza Audit Logs.
See README/inputs.conf.spec for the full argument schema.

Support
-------
Contact vezasplunk@servicenow.com or visit https://www.veza.com/.
