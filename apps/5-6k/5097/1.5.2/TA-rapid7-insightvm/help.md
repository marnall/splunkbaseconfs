# Description

The Rapid7 InsightVM Technology Add-On for Splunk is designed to retrieve asset and vulnerability data via the 
InsightVM Cloud for import and ingestion into Splunk. This integration features an initial import of all 
InsightVM asset and vulnerability data and provides options for customizing and filtering the data that is retrieved. 
It also allows for tracking of new and remediated vulnerabilities, as these will be imported into Splunk as new events 
when they are discovered or remediated in InsightVM.

# Key Features

* Imports asset and vulnerability data from InsightVM into Splunk
* Provides filtering options for asset and vulnerability data
* Allows for tracking of new and remediated vulnerabilities

# Requirements

* Rapid7 Platform API Key

# Documentation

Help documentation and FAQ for the InsightVM Technology Add-On for Splunk and InsightVM Dashboard can be referenced on the [InsightVM Technology Add-On for Splunk](https://docs.rapid7.com/insightvm/insightvm-technology-add-on-for-splunk) integration help page.

In addition, the Splunkbase listings include basic installation and configuration details on the `Details` page for each listing:

* [InsightVM Technology Add-On](https://splunkbase.splunk.com/app/5097/#/details)
* [InsightVM Dashboard](https://splunkbase.splunk.com/app/5098/#/details)

# Version History

* 1.3.0 - Add support for unauthenticated proxies.

* 1.2.0 - Improve request logic around retries & data returned. Add a configuration option that allows a full import every X number of days.

* 1.1.4 - Upgrade to Splunk Add-on builder 4.

* 1.1.3 - Improvements to the InsightVM query. Add logs to display the imported number of vulnerability finding events per job. 

* 1.1.2 - Changes to the InsightVM query intended to ensure all new/remediated vulnerability findings are imported as well as reducing the amount of duplicate data.

* 1.1.1 - Region field in account configuration is now able to accept 3 characters to support us2/us3 regions.

* 1.1.0 - Improvements to asset filter logic to reduce the window of time where newly scanned/assessed assets can affect existing page requests. Added "Include same vulnerabilities" check box to import found vulnerabilities during a partial import.

* 1.0.5 - Rapid7 Agent collection data is retrieved using a separate request as sometimes agents are unscanned or sync data infrequently.

* 1.0.4 - For initial imports remove the comparisonTime of 90 days ago, which only affects how vulnerabilities are grouped. Increase the TRUNCATE setting for vulnerability findings and vulnerability definitions. If a `vulnerability definition` is still larger than the TRUNCATE setting the length of some of its fields are truncated by the add-on. Always set the ingest time to the CURRENT time instead of letting Splunk default the ingest time.

* 1.0.3 - Logging level changes when requests return non 200 responses. Update the request retry backoff time to allow more time between retries. Asset import checkpoint is now the most recent last_scan_end rather than the current time.

* 1.0.2 - Bug fix to ensure all vulnerabilities are returned by InsightVM. Change maximum records per page to 100.

* 1.0.0 - Initial release of Rapid7 InsightVM Technology Add-On providing functionality to import asset and 
vulnerability findings from the InsightVM Platform

# Links

## References

* [Splunkbase Listing](https://splunkbase.splunk.com/app/5097/)
