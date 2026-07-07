# Change Log
All notable changes to the Recorded Future App for Splunk add-on will be
	documented in this file.

## [5.0.10] - 2020-01-20
### Bug Fix
- Fixed bug with Risk List downloads when using SHC.

## [5.0.9] - 2019-11-27
### Bug Fix
- Disabled Risk Lists were still fetched.
	
## [5.0.8] - 2019-11-07
### Changes
- Added compatibility with Python 3.
- Mandatory use of https when setting the API URI.
	
## [5.0.7] - 2019-10-11
### Bug Fix
- Issue when the app is installed together with the Splunk ES 
add-on.
### Changes
- Validated on Cloud platform.
	
## [5.0.6] - 2019-10-03
### Bug Fix
- Issue with the Configuration view when load balancers are used.
	
## [5.0.5] - 2019-09-30
### Bug Fix
- Edge cases dealing with stale CSRF cookies.

## [5.0.4] - 2019-09-24
### Bug Fix
- Issues when IPv6 is used.
- Issue with the Configuration view when the web was running on 
  port other than 8000. 
	
## [5.0.3] - 2019-09-11
### Bug Fix
- Search head replication of config file app.conf was missing.
	
## [5.0.2] - 2019-08-27
### Bug Fix
- Lookup files unnecessary distributed to indexers du to wrong path in 
  replicationBlacklist stanza in distsearch.conf.
- Search head replication of config file app.conf was missing.

## [5.0.1] - 2019-08-12
### Changes
- Use the is_configured flag to move the user to the configuration 
  page to input the API-token before using the dashboards.
### Bug Fix
- Some links on the help pages no longer existed and have been updated.


## [5.0.0] - 2019-08-02
### Changes
- Removed the dependency on Splunk Add-on Builder.
- Refactored to only use REST API calls.
- New configuration page.
- Removed almost all external dependencies.
- Not using inputs.conf to comply with Splunk Cloud requirements.
- Storing Risk List metadata in kvstore instead of index.
- Improved documentation.
### Bug fix
- A couple of panels with related entities were hidden even though 
they contained data in the enrichment dashboards.

	
## [4.0.12] - 2019-02-14
### Bug fix
- Problem identifying the captain properly on Search Head clusters.
### Changes
- Added server.conf to replicate important configuration files for Search Head 
  Clusters without manual configuration.
	
## [4.0.11] - 2019-01-28
### Bug fix
- Non existant view referenced from the navigation menu.
### Changes
- Performance enhancements in the custom REST handler.
	
## [4.0.10] - 2019-01-18
### Bug fix
- Multiword malware names were not handled correclty in the Malware
enrichment dashboard.
- Broken drill down in the domain correlation dashboard.
- Alerts failed to be fetched when title was non-ascii.

### Changes
- Increased timeout for the internal REST call in the Malware
enrichment dashboard since response times from the Recorded Future
API can be high for this type of queries.
- Added selective drilldowns to the domain, hash, vulnerability and
url correlation dashboards. Clicking on the IOC searches for events 
with the IOC, clickon on count brings the enrichment dashboard up for
the IOC.
	
## [4.0.9] - 2019-01-07
### Changes
- Rewrite of custom variables extraction in the REST handler.

## [4.0.8] - 2018-12-17
### Changes
- Additional logging in the REST handler.
- Modified exception handling.
	
## [4.0.7] - 2018-12-13
### Bug fix
- Vulnerability dashboard show wrong vulnerability in some circumstances.
	
## [4.0.6] - 2018-12-11
### Changes
- Additional logging in the REST handler.
	
## [4.0.5] - 2018-11-22
### Bug fix
- The about page contains the Release number. This is now automatically kept 
  in sync. 
- Risk lists were always downloaded on Windows servers du to a checksum 
  calculation error. 

## [4.0.4] - 2018-11-15
### Cloud certification issues
- Removed debug logging that contained proxy credentials.
- Added configuration validation to requiere https for an alternate API URL.
- Adjusted permissions when creating the app's tmp folder.
- Corrected typo in README.txt
- Switched schema version of app.manifest.

## [4.0.3] - 2018-11-09
### Bug fix
- Compatibility issue with python-requests shipped with the Splunk server.
- Internal rest calls intermittently failed on clusters.
- Links to advisories from the Vulnerability enrichments dashboard were broken.
- Fixed naming of Intelligence card in some locations.
- Fixed improper sizing of logotypes in some locations.
- Added setting to disable SSL verification if needed.
- Search head cluster checks in the validation report.
- Problems reading config files on Windows servers.

### Improvements
- Sample data has been filtered to avoid being flagged as malware.
- Improved validation report which detects missing configuration on search head
  clusters.
- Added configuration option to disable SSL verification (needed with some
  proxy configurations).

## [4.0.2] - 2018-09-11
### Bug fix
- Detection of Search head failed on Splunk server running without licenses.
- Link to ASN information cards was wrong. 

### Improvements
- Updated XML in dashboard to new SimpleXML specification.
- Updated color settings to adapt to new visuals in Splunk 7.1.
- Minor look-n-feel improvements to dashboards.
- Changed the default view to the Alerts view.
	
## [4.0.1] - 2018-06-27
### Improved
- Added a placeholder for the getting_started dashboard to redirect
  old installations with customized navigation to the new start page.
- Documentation improvements.

### Removed
- Removed server.conf since Splunk prohibits it. Search head installs
  will have to manually add it.

## [4.0.0] - 2018-06-01
### New
- New enrichment dashboards
	- URLs
	- Malwares
- New correlation dashboard:
	-  URLs
- A new Explorer dashboard has been added. Using drop-down menus it's
	possible to explore different sourcetypes, risklists and fields
	to find the best way to correlate event data.
- A new Global Map dashboard was added.
- A new Alerts dashboard was added. It displays summary information about
	alerts pulled from Recorded Future using the alerts modular input.
- Support for Custom risklist using Recorded Future Fusion was added. Any
	number of risklists can be added.
- New macros:
  - rf_correlate - extends the functionality of previously available
    rf_hits with support for multiple risklists. This macro does
    however not unpack and format the evidence string. The new macro
    format_evidence can be used for this.
  - format_evidence - unpacks and reformats the evidence details for a
    matching entity.
  - to_date - extract the date from data and formats it.
  - to_time - extract the date and time from data and formats it.
  - to_splunk_time - extract the date and time but perform no
    formatting.
  - unpack_metrics - unpacks the metrics field used in enrichment.
  - unpack_relatedEntities - unpacks Related Entities used in
    enrichment.
  - unpack_riskyCIDRIPs - unpacks the information about risky IPs in
    the CIDR used by IP enrichment.
- Support for retreiving alerts from Recorded Future has been added.
- Help pages are included in the app (including this Changelog).
- New reports:
	- A new report "Latest updates of all risklists" was added.
	- A new report that show all log events from the app was added.
	- A new validation feature has been added. This feature can be
	used to verify that the app can work or to gather information
	about potential issues.
- Search head cluster synchronization:
	- Only one cluster member retrieves risklists before distributing
	them to the rest of the cluster.
	- Configuration is synchronized, ex the API key can be added to
      any node in the cluster, it will be propagated to all nodes.

### Changed
- Correlation dashboards have been improved:
	- The Triggered Rules and Evidence strings that were previously
	shown in two different fields have now been combined into one,
	making it much easier to match Risk Rule with the corresponding
	Evidence String. For each event the Evidence is listed in
	descending criticality. A colored dot also provides information
	about how critical the evidence is.
	- An addtional column has been added to the table of events found
	in the correlation search: the count of occurences of the entity
	(ex IP).
	- Two additional panes have been added:
		- The top Risk Rules over the last 24 hours.
		- The top entity (ex IP) which matches the risk list
		during the last 24 hours.
- Enrichment dashboards have been improved:
	- To help focus on the most relevant information the respective
	dashboard mimics the corresponding information card from Recorded
	Future.
	- The "Current Risk Indicators" panel has been renamed to
	"Triggered Risk Rules". The content is sorted by descending
	Criticality (which is shown and color coded).
	- When Recorded Future has information that the entity is present
	on a Treat list this information is shown in the "In Threat Lists"
	panel.
	- If Recorded Future's Insikt Group has produced research about
	the entity this is shown in the "Threat Research Insikt Group" panel.
	- The number of categories of related entities has been
	increased. Only panels with information are shown. The following
	categories have been added:
		- Related Attacker
		- Related Target
		- Related Actors
		- Related Products
		- Related Countries
		- Related Technologies
		- Related E-Mail Addresses
		- Related Attack Vectors
		- Related Operations
	- Some dashboards have been made more efficient by removing
	additional API calls.
- Recorded Future Cyber Vulnerability Enrichment has been improved:
	- Information from NVD is displayed in the "NVD Summary" panel.
	- Information about affected versions is shown in the "Affeced
	Versions" panel.
	- Information third party information is shown in the "Advisories,
	Assessments and Mitigations" panel.
- The filenames of the risklists in the the lookups folder have
  changed. Ex: rf_ip_threatfeed.csv has become rf_ip_risklist.csv. The
  transform used to map between the name and the file name has been
  adapted to ensure backwards compatibility.
- Complete rewrite of the scripts included in the app.
	- Updates of the risklists and retreival of alerts have been
	implemented as modular inputs to improve reliability and
	scalability. Updates are performed as soon as new versions of the
	risklists become available. 
	- Enrichment is performed using an extension of Splunk's REST
	endpoint.
	- The setup GUI has been extended and leverages Splunk's
	framework.

### Removed
- The monitoring dashboards have been removeds since this goal is better
	achieved using alerts within Recorded Future's service.

## [3.0.5] - 2017-08-15
### Changed
- IP/Domain risk lists download once an hour

## [3.0.4] - 2017-05-26
### Changed
- Risk Lists do not download to /tmp first
- Single risklist.py scrip to download
- Commands to download risk list (Splunk Macros)
- Reduced size of demo data
- Layout of enrichment dashboards
- Default values for enrichment dashboards

### Removed
- Conifg dashboards

## [3.0.3] - 2017-05-02
### Changed
## Addressed Certification Issues
    - Removed error key log of Session Key
    - Updated documentation for API Token entry to be more explicit

## [3.0.2] - 2017-04-25
### Changed
## Addressed Certification Issues
    - Validate user proxy input

## [3.0.1] - 2017-04-17
### Changed
## Addressed Certification Issues
    - Removed Javascript from setup.xml
- Renamed the folder for the example log files


## [3.0.0] - 2017-03-17
### Changed
## Addressed Key Certification Issues
    - API Token is encrypted
    - Risk Lists are downloaded first to tmp then lookups not bin to lookups
- Getting Started has been updated to reflect new additions
- Installation Guide has been updated to reflect changes
- Proxy can be added through the UI
- Default frequency of Risk List downloads (IP/Domain 4hrs, Vuln/Hash 1 day)
- Updated layout of Enrichment dashboards
- Threat Landscape is changed to Monitor
- Changed naming conventions of .py files to fit with multiple entity types
- Updated download commands to take arguments
- Gave users permission to access stored passwords (encrypted api token)
- Refactored to take advantage of the new API
- Use Requests instead of urllib2
- Updated to new logo
- IP Correlate dashboard no longer references Wordpress demo data
- Changed version numbers to major.minor.bugfix
- Recorded Future link is now app.recordedfuture.com
- Scheduled Reports return current date when completed successfully
- Added example logs files for Correlation dashboards

### Added
- Enrichment dashboards for Vulnerabilities
- Correlate dashboards for Vulnerabilities, Domains, and Hashes
- Config dashboards to filter Risk Lists by Risk Rule
- Package sample Risk Lists and correlation data

### Removed
- Current Threat Trends Dashboard
- Deleted deprecated code
- Removed unused macros and commands

## [2.12.13] - 2016-12-13
### Changed
- Altered read/write/execute rights on bin folder

### Added
- Addition of 'lib' folder with Python modules for encryption of key

### Removed
- Removal of Recorded Future - Threatfeed from savedsearches.conf

### Added
- Heatmap color-coding has been added to table panels in the following dashboards:

Log Correlations
IP Monitoring
Domain Monitoring
Current Threat Trends

### Changed
- Altered dashboards to use rf_threatfeed.csv lookup. 

## [2.2.4] - 2016-02-04
### Changed
- IP enrichment dashboard API query uses IpAddress data_group
- Domain enrichment dashboard API query uses InternetDomainName data_group
- Hash enrichment dashboard API query uses Hash data_group
- The three changes above now give accurate risk scores and match RF intelligence cards
- /bin/rf_observablequery.py altered to handle API query changes to enrichment dashboards
- v3.0 now rf_threatfeed used as a lookup and for correlation
- Risk Score metric added to IP Enrichment dashboard
- Font size change of metrics in summary panel on enrichment dashboards
- Name changed from 'Add-on' to 'App'

### Added
- IP monitoring dashboard includes input field for IP address
- /appserver/static/rf_enrich_kpi.css to over-ride default font sizes in summary panels
- Sample threat feed included in lookups directory

## [1.11.11] - 2015-11-1
### Changed
- Added |localop to dashboards to address. Note: in some distributed environment cases, having just the 'localop' keyword is not enough. A pipe (|) is needed before. 

## [1.10.29] - 2015-10-29
### Changed
- Added 'localop' keyword to search string in IP Enrichment dashboard.

## [1.10.16] - 2015-10-16
### Changed
- Removed 'Threatfeed URL' requirement from installation setup screen. 
- Code altered to download Recorded Future's threatfeed using API token only (for added security).
- Splunk add-on documentation updated to reflect changes.
- Disabled drilldown feature - which re-directed to Splunk search - on the following dashboards: 

Current Threat Trends
IP Enrichment
Domain Enrichment
Hash Enrichment

### Added
- Heatmap color-coding has been added to table panels in the following dashboards:

Log Correlations
IP Monitoring
Domain Monitoring
Current Threat Trends

## [1.10.09] - 2015-10-09
### Fixed
- Corrected rf_hits macro syntax within macros.conf file

## [1.08.17] - 2015-08-17
### Added
- Addition of rf_threatfeed.csv threatfeed lookup to evaluate risk of IP addresses. 

### Changed
- Altered dashboards to use rf_threatfeed.csv lookup. 
