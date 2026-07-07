ZeroFox Data Collector for Splunk
==================================
Version 4.0.0 | ZeroFox Inc. | ask@zerofox.com


OVERVIEW
--------
The ZeroFox Data Collector (TA-zerofox) ingests threat intelligence and alert
data from the ZeroFox platform into Splunk. It provides two modular input types:

  - ZeroFox Intel (CTI): collects threat intelligence feeds from the ZeroFox
    CTI API (botnet, ransomware, phishing, indicators of compromise, and more).

  - ZeroFox Alerts: collects ZeroFox platform alerts in real time, with
    optional filtering for escalated alerts only.

Data is indexed as structured JSON events, ready for search, dashboards,
correlation rules, and Splunk Enterprise Security (ES) workflows.


REQUIREMENTS
------------
  - Splunk Enterprise or Splunk Cloud 8.0 or later
  - Python 3.9 or later (Splunk's bundled Python 3 runtime)
  - A ZeroFox account with API access
  - Network access from the Splunk instance to api.zerofox.com (port 443)


INSTALLATION
------------
1. Download TA-zerofox from Splunkbase.
2. In Splunk Web: Apps > Manage Apps > Install app from file.
3. Upload the .tar.gz package and click Upload.
4. Restart Splunk if prompted.

For a Splunk Enterprise distributed environment, install the TA on the Search
Head (or Heavy Forwarder) that will run the modular inputs. No deployment to
indexers is required.


CONFIGURATION
-------------

Step 1 — Create an account

  Go to: ZeroFox Data Collector > Configuration > Accounts > Add

  - Name: a label for this credential set (e.g. "production")
  - API username: your ZeroFox platform username (email address)
  - API password: your ZeroFox platform password, or a Personal Access Token
    for Alerts inputs. CTI inputs use username + password for token exchange.

Step 2 — Create a CTI input

  Go to: ZeroFox Data Collector > Inputs > Create New Input > ZeroFox Intel (CTI)

  - Name: a unique label (e.g. "indicators_prod")
  - Interval: polling interval in seconds (default: 3600)
  - Index: target Splunk index
  - Account: select the account created in Step 1
  - Intel source: select the feed to collect (see Supported Feeds below)
  - Email / domain filter: optional, only available for Compromised Credentials
    and Botnet Credentials feeds

  Repeat for each feed you want to collect. Each feed requires its own input.

Step 3 — Create an Alerts input

  Go to: ZeroFox Data Collector > Inputs > Create New Input > ZeroFox Alerts

  - Name: a unique label (e.g. "alerts_prod")
  - Interval: polling interval in seconds (default: 120)
  - Index: target Splunk index
  - Account: select the account created in Step 1
  - Alert filter: "All alerts" or "Escalated only"


SUPPORTED CTI FEEDS
-------------------
  Intel source value       Sourcetype
  -----------------------  ---------------------------
  botnet                   zerofox:cti:botnet
  botnet_credentials       zerofox:cti:botnet:credentials
  c2_domains               zerofox:cti:c2domains
  credentials              zerofox:cti:credentials
  credit_cards             zerofox:cti:creditcards
  disruption               zerofox:cti:disruption
  exploits                 zerofox:cti:exploits
  indicators               zerofox:cti:indicators
  malware                  zerofox:cti:malware
  phishing                 zerofox:cti:phishing
  ransomware               zerofox:cti:ransomware
  vulnerabilities          zerofox:cti:vulnerabilities

Alerts are indexed with sourcetype: zfox


UPGRADE NOTES — v3.x to v4.0
------------------------------
Version 4.0 introduces breaking changes. Please read carefully before upgrading.

  - The 13 separate per-feed inputs (zfox_cti_botnet://, zfox_cti_ransomware://,
    etc.) are replaced by a single unified "ZeroFox Intel (CTI)" input type with
    a feed selector. Existing inputs will not carry over automatically — they
    must be recreated in Settings > Data inputs > ZeroFox Intel (CTI).

  - Checkpoints are migrated automatically on first run. No data will be
    re-collected and no historical events will be lost.

  - The internal framework changed from Add-on Builder (AoB) to UCC. Do not
    mix files from 3.x and 4.x installations.

  - Accounts must be reconfigured after upgrade due to the credential storage
    format change.


TROUBLESHOOTING
---------------
Logs are written to the Splunk internal index under sourcetype tazerofox:log.
To search for errors:

  index=_internal sourcetype=tazerofox:log level=ERROR

To enable verbose (DEBUG) logging:
  ZeroFox Data Collector > Configuration > Logging > set to DEBUG


SUPPORT
-------
  Email:      ask@zerofox.com
  Splunkbase: https://splunkbase.splunk.com/app/5041
  Website:    https://www.zerofox.com
