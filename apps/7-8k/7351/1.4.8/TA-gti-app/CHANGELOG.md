## Release Notes

### Version 1.4.8

* Added Python 3.13 compatibility and dual package for x86_64 and AArch64 architectures.

### Version 1.4.7

* Added Python 3.13 compatibility and dual package for x86_64 and AArch64 architectures.

### Version 1.4.6

* Fixed a bug that resulted in the MITRE ATT&CK dashboard loading with an empty matrix despite having underlying data.

### Version 1.4.5

* Threat Lists IoCs include now the name of their associations in four new fields: threat_actor_names, campaign_names, malware_names and report_names.
* Fixed an issue in the ioc_stream input that caused ingestion to fail with large objects due to data truncation.
* Resolved a bug that prevented IP addresses from being correctly added to Splunk Enterprise Security (ES) threat intelligence.

### Version 1.4.4

* Filter threat lists: Easily refine threat list ingestion by setting a custom query filter.
* Update Addon Builder version

### Version: 1.4.3

* Optimized the CVE ingestion process, reducing data collection time by approximately 50%
* The target index for CVE data ingestion is now customizable, providing greater flexibility for data management.

### Version: 1.4.2

* Ingest CVEs: Easily bring in the latest vulnerability data.
* Automatic Matching: Correlate ingested vulnerabilities with your scan results.
* New Dashboards:
    * Vulnerability Overview: See all vulnerabilities by risk and exploitation status.
    * Vulnerability Details: View information about affected hosts.
    * Ingestion Stats: Monitor your ingested intelligence.

### Version: 1.4.1

* Ingest CVEs: Easily bring in the latest vulnerability data.
* Automatic Matching: Correlate ingested vulnerabilities with your scan results.
* New Dashboards:
    * Vulnerability Overview: See all vulnerabilities by risk and exploitation status.
    * Vulnerability Details: View information about affected hosts.
    * Ingestion Stats: Monitor your ingested intelligence.

### Version: 1.4.0

* Ingest CVEs: Easily bring in the latest vulnerability data.
* Automatic Matching: Correlate ingested vulnerabilities with your scan results.
* New Dashboards:
    * Vulnerability Overview: See all vulnerabilities by risk and exploitation status.
    * Vulnerability Details: View information about affected hosts.
    * Ingestion Stats: Monitor your ingested intelligence.

### Version: 1.3.0

* Add support for ingesting IoC Streams as modular inputs https://gtidocs.virustotal.com/reference/delete-notifications-from-the-ioc-stream
* Add compatibility with Splunk Enterprise Security, now Threat Lists and IoC Stream inputs can add IoCs to ES Threat Intelligence.

### Version: 1.2.1

* Get the management port from the Splunk configuration instead of the default.

### Version: 1.2.0

* Add view-context documentation in each panel of the integration
* Add support for ingesting Threat Lists as modular inputs https://gtidocs.virustotal.com/reference/list-provisioned-threat-lists
* Implement an update mechanism for saved searches, prompting users to update queries that are not aligned with the latest add-on version. This ensures all searches leverage the most current functionality.

### Version: 1.1.4

* Python 3.7 dependencies have been updated.
* Optimized search query for basic correlations.

### Version: 1.1.3

* Update Splunk SDK for python.

### Version: 1.1.2

* New CIM data models correlations.

### Version: 1.1.1

* Fix search in events action bug when button 'Search' is clicked.

### Version: 1.1.0

* A new dashboard to manage correlations allows users to define their own correlations, giving them greater control over the index and the fields used by each correlation.
* Add granular controls to enable/disable correlations individually.
* The basic correlation saved searches performance has been improved.
* The basic correlation saved searches execution interval has been reduced from 30 to 15 minutes.

### Upgrade from version 1.0.4

* Execute the following command to keep up to date your threat actors.
```
| gtiadversaryupdate
```

### Version: 1.0.4

* The performance of the `gti` command has been drastically improved.
* The MITRE ATT&CK techniques tab from Adversary Intelligence has been moved to the MITRE ATT&CK dashboard.
* The Events drilldown tables have been replaced by a Splunk Search action, allowing users to have more control by refining the search query to match the IoCs in their events.
* The Adversary Intelligence dashboard now displays individual tables for campaigns, malware, toolkits and collections."

### Version: 1.0.3

* Fix Adversary dashboard bug where Threat actors were not being listed
* Add GTI assessment (threat score, severity and verdict) data to IoCs in all dashboards
* Add a new role called gti which allows users to use the add-on but preventing them from editing settings

### Version: 1.0.2

* Fix settings correlation error when saved searches are saved

### Version: 1.0.1

* Added partner and crowdsourced origin selector in Adversary dashboard for Standard Google TI package
* Added partner, crowdsourced and Google Threat Intelligece origin selector for Enterprise Google TI package
* Fix MITRE matrix content

### Version: 1.0.0