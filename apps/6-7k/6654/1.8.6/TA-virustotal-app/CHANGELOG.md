## Release Notes

### Version 1.8.6

* Added Python 3.13 compatibility and dual package for x86_64 and AArch64 architectures.

### Version 1.8.5

* Fixed a bug that resulted in the MITRE ATT&CK dashboard loading with an empty matrix despite having underlying data.

### Version 1.8.4

* Add support for ingesting IoC Streams as modular inputs https://docs.virustotal.com/reference/ioc-stream-introduction

### Version 1.8.3

* Update Addon Builder version

### Version: 1.8.2

* Get the management port from the Splunk configuration instead of the default.

### Version: 1.8.1

* This version addresses a packaging problem encountered in 1.8.0.

### Version: 1.8.0

* Add view-context documentation in each panel of the integration.
* Implement an update mechanism for saved searches, prompting users to update queries that are not aligned with the latest add-on version. This ensures all searches leverage the most current functionality.

### Version: 1.7.3

* Python 3.7 dependencies have been updated.
* Update the automatic correlation saved searches increasing their performance
* Update the automatic correlation saved searches to deduplicate Iocs before being ingested by the vt4splunk command

### Version: 1.7.2

* Update Splunk SDK for python.

### Version: 1.7.1

* New CIM data models correlations.

### Upgrade from version 1.6.7

* Execute the following command to keep up to date your threat actors.
```
| vtadversaryupdate
```

### Version: 1.7.0

* A new dashboard to manage correlations allows users to define their own correlations, giving them greater control over the index and the fields used by each correlation.
* Add granular controls to enable/disable correlations individually.
* The basic correlation saved searches performance has been improved.
* The basic correlation saved searches execution interval has been reduced from 30 to 15 minutes.

### Version: 1.6.7

* The performance of the `vt4splunk` command has been drastically improved.
* The MITRE ATT&CK techniques tab from Adversary Intelligence has been moved to the MITRE ATT&CK dashboard.
* Events drilldown tables has been replaced by a Splunk Search action, so the users can get more control refining the search query to match the IoCs in their events.

### Version 1.6.6

* Update VT Augment version to 1.7.4
* Fix error when dashboards are loaded outside of add-on context (i.e. on Splunk home view)

### Version 1.6.5

* Cloud compatibility

### Version 1.6.4

* Fixed bug when detecting if Splunk REST uses SSL or not.
* New unknown pivot en Severity pie chart.
* Fix empty values in pie charts.
* Upgrade Add-on builder version to 4.2.0.

### Version 1.6.3

* Added HTTPS proxy support.
* Added JARM information to IP addresses and domains.

### Version 1.6.2

* Improve saved searches performance.
* Disable saved searches by default.
* Improve fields validation to avoid inconsistent states.

### Upgrade from all versions

* We have changed the way the add-on stores some configuration values like the `Lookup table expiration`, `Index names` and the `Enable automatic correlation`. Values stored before the upgrade will not work as expected, please, after the upgrade, enter again the configuration in the General and Correlation Settings and save both forms.

### Version 1.6.1

* Run `vt4splunk` command locally.
* Fix compatibility with Splunk 9.1.*.
* Added the IoC severity for VT Enterprise users.
* Fix bug when lists in Correlation Settings contained spaces.
* Added whois information to domains.

### Version 1.6.0

* Allow users to run `vt4splunk` command locally.
* Added VPN, Tor and Proxy IPs tab in Threat Intelligence dashboard.
* Added the number of VT comments on each IoC.
* Added the number of Crowdsource Yara rules matches to file IoCs.
* Avoid to enrich private IP addresses.
* `vtdeleteiocs` command is able to receive IoCs as input.
* Improved window time selector by allowing any relative time.
* Fix bug in hashes tables when displaying SHA256 instead of ID.
* Fix bug where the Configuration tab didn't open in some cases.

### Version 1.5.3

* Fix bug when `vt4splunk` command process records with non utf-8 encoding.

### Version 1.5.2

* Fix bug when checking the API key.

### Version 1.5.1

* Added `vt_ignore_cache` to ignore desired IoCs.
* Fix bug when using proxy with username and password.
* Fix bug in Vulnerability Intelligence dashboard when using the time window selector.

### Version 1.5.0

* Added signature severity to MITRE ATT&CK techniques in Adversary Intelligence dashboard.
* Added a control to filter by signature severity to MITRE ATT&CK techniques in Adversary Intelligence dashboard.
* Change flagged files by extension chart to by type in Threat Intelligence dashboard.
* Clicking on cards works as clicking on tabs in Threat and Adversary Intelligence dashboards.
* Fix a bug in MITRE ATT&CK dashboard when number of files with MITRE ATT&CK techniques was greater than 100.
* Change workflow action endpoint for URLs.
* Fix bug when using saved searches in distributed environment.
* Fix cloud compatibility.

### Upgrade from 1.4.* versions

* Delete content of the MITRE lookup table to make it compatible with the new version:
```
| outputlookup vt_mitre_cache
```

### Version 1.4.1

* Fix cloud compatibility.

### Version 1.4.0

* Added a brand new MITRE ATT&CK matrix dashboard.
* Added a new command `vtmitreupdate` to extract tactics and techniques from IoCs.
* Added a new attack techniques and sub-techniques table to the Adversary dashboard.
* Added a saved search to keep up-to-date the MITRE data.
* Added a validator to the API key field to avoid enter by mistake an invalid value.
* Improve errors feedback, no quota, API key not set or other errors are now displayed in all dashboards.
* Improve the support on distributed installations, now the app and config are replicated across the search head cluster.
* Improve logging, app logs can now be read at $SPLUNK_HOME/var/log/splunk/ta_virustotal_app_*.log.
* Now automatic correlation can be disabled per IoC type, leaving the input of the field names empty.
* Now saved searches don't run if there is not a valid API key configured.
* Fix the vt4splunk command search error `_last_correlation_date`.
* Fix the vt4splunk command search error `vt_tags`.
* Fix workflow action error for URLs.

### Version 1.3.0

* Added a new Adversary Intelligence dashboard.
* Added a new command `vtdeleteiocs` to delete iocs selectively.
* Added a new command `vtadversaryupdate` to gather adversary intelligence data from VirusTotal.
* Added a new command `vtvulnerabilitiesupdate` to extract vulnerabilities from the iocs.
* Added a saved search to delete iocs older than a configured value.
* Added a saved search to keep up-to-date the adversary intelligence data.
* Added a saved search to keep up-to-date the vulnerabilities data.
* Added a malware category pie chart (file) to the Threat Intelligence dashboard.
* Added a categories pie chart (urls, domains) to the Threat Intelligence dashboard.
* Added a country pie chart (ip) to the Threat Intelligence dashboard.
* Added a TLD pie chart (urls, domains) to the Threat Intelligence dashboard.
* Added a ASN pie chart (ip) to the Threat Intelligence dashboard.
* Added country flags.
* Improve quota errors feedback when `vt4splunk` is executed.
* Fix a bug when a non-valid IoC aborts the entire query.
* Breaking change: `vt_malicious` has been renamed to `vt_detections`.

### Upgrade from 1.2.0 version

* Delete content of the ioc lookup tables to make them compatible with the new version:
```
| outputlookup vt_file_cache
| outputlookup vt_domain_cache
| outputlookup vt_url_cache
| outputlookup vt_ip_cache
| outputlookup vt_cve_cache
```

### Version 1.2.0

* Added saved searches to automate the v4splunk enrichment.
* Added a malware category pie chart in the Threat Intelligence dashboard.
* Added a lookup date column in the Threat Intelligence dashboard.
* Fix bug where the VT Augment didn't open in some cases.

### Version 1.1.0

* Fix several dashboards errors.
* Fix proxy error when user and pass were missing.

### Version: 1.0.0

* Added a `vt4splunk` command to enrich events.
* Added a threat intelligence dashboard to show all malicious IoCs collected from your events.
* Added a dashboard to show all CVEs found in your events.
* Added a dashboard to monitor the consumption of the VT API quota.
