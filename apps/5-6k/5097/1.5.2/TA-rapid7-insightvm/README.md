# Rapid7 InsightVM Technology Add-On

## Description
The Rapid7 InsightVM Technology Add-On is used for retrieving asset and vulnerability data from InsightVM and ingesting 
into Splunk following the Common Information Model (CIM). The add-on is designed to be compatible with Splunk 
Enterprise and Splunk Cloud with the use of a Universal Forwarder.

This Technology Add-On is intended to import asset and vulnerability findings from the InsightVM Platform without the use of the InsightVM console. It is designed to only import assets and vulnerabilities for devices that have been scanned since the last import run. Key functionality includes:
- Import all asset and vulnerability data when it runs for the first time
- Track previous import times to only import assets and their associated vulnerabilities that have been scanned in the time since the last import
- Vulnerabilities that are newly found or have been remediated will be imported as new events in Splunk and 
respectively assigned a status of `new` or `remediated`
- Previously imported vulnerabilities that have not changed in status will not be imported as new events and will retain their `found` status

The Rapid7 InsightVM Dashboard and Technology Add-On are recommended in place of the Nexpose Dashboard and Technology Add-On listed on Splunkbase for all InsightVM customers.

## Installation

There are two ways to install the technology add-on - via the Splunk app listing, or manually with a provided 
technology add-on package. To install the add-on via the app listing, follow these steps:

1. From the `Apps` menu in Splunk, select `Manage Apps`
2. Select `Browse More Apps`
3. Do a search for the "Rapid7 InsightVM Technology Add-On"
4. Select `Install` from the app listing
5. Perform a restart of Splunk when prompted

To install the add-on manually, follow these steps:

1. From the `Apps` menu in Splunk, select `Manage Apps`
2. Select `Install app from file`
3. Select the InsightVM Technology Add-On package
4. Perform a restart of Splunk when prompted

The add-on should now appear as `Rapid7 InsightVM` under the Apps menu in Splunk.

## Configuration

The following details the configuration of the technology add-on in order to perform retrieval and ingestion of
InsightVM data.

### Creating a connection

A connection must be created within the add-on to facilitate the retrieval of InsightVM data. This connection utilizes 
a generated Insight platform API key. The following details how to generate a new API key:

1. Login to the Insight platform [here](https://insight.rapid7.com/)
2. Select the gear icon on the top menu and click `API Keys`
3. Select `Organization Key`
4. Select `+ New Key`
5. Enter a name for the key and click `Generate`
6. Copy and securely store the generated key

Once you have an API key, you can configure a connection for the technology add-on in Splunk. To create a connection, 
follow these steps:

1. Navigate to the Rapid7 InsightVM technology add-on, available under the `Apps` menu in Splunk
2. Select `Configuration`
3. Select `Add`
4. Enter a name for the connection
5. Enter your region. Additional info on regions is available [here](https://insight.help.rapid7.com/docs/product-apis#section-supported-regions)
6. Enter your generated API key
7. Click `Add`

### Inputs

There are two types of inputs in the technology add-on, and three sourcetypes that result from these inputs. They are:

* rapid7:insightvm:asset
* rapid7:insightvm:asset:vulnerability_finding
* rapid7:insightvm:vulnerability_definition

When configuring the inputs it is important to select the proper index for storing the imported events. The Technology 
Add-On defaults to an index name of `rapid7`; however, the index is not automatically created. Make sure to either have 
 a Splunk administrator create the `rapid7` index or select an index that already exists.

#### InsightVM Asset Import

The InsightVM Asset Import can be configured to perform an import of two types of data from InsightVM: assets and 
(optionally) vulnerability findings. To configure this input, select `Inputs` from the technology add-on menu, then 
select `InsightVM Asset Import` under `Create New Input`.

The fields for this input are as follows:

| Field  | Description  |
|---|---|
| Name  | The name of the input as it will appear in Splunk |
| Interval |  The frequency in seconds that the import of InsightVM data will occur. Default is once per hour |
| Index  |  Your preferred Splunk index for data. Default is `rapid7` |
| InsightVM Connection | The InsightVM connection, created as per the instructions in the Configuration section above |
| Asset Filter | A query for filtering assets that are imported |
| Import vulnerabilities | An option for whether to import vulnerability findings into Splunk in addition to assets |
| Vulnerability filter | A query for filtering vulnerability findings that are imported |

Here are some example asset filters that can be applied within this input configuration:

* `sites IN ['site-name']`
* `tags IN ['tag-name']`
* `os_family = 'Windows'`

And some example vulnerability filters:

* `cvss_v2_score > 6`
* `severity = 'Critical'`

#### InsightVM Vulnerability Definition Import

The InsightVM Vulnerability Definition Import is used to import vulnerability definitions from InsightVM. This can be 
used to correlate with vulnerability findings, should you want to import those, as well. This input is not required 
for visualizing asset findings in your environment. However, it does provide additional details about the 
vulnerabilities.

The fields for this input are as follows:

| Field  | Description  |
|---|---|
| Name | The name of the input as it will appear in Splunk |
| Interval | The frequency in seconds that the import of InsightVM data will occur. Default is once per day |
| Index | Your preferred Splunk index for data. Default is `rapid7` |
| InsightVM Connection | The InsightVM connection, created as per the instructions in the Configuration section above |
| Vulnerability filter | A query for filtering vulnerability definitions that are imported |

**Important Note:** Due to the large amount of data contained within vulnerability definitions, we recommend
importing them a maximum of once per day.

## Data Visualization

We've also created the Rapid7 InsightVM Dashboard as a starting point for visualizing data that's imported with the 
InsightVM technology add-on. The dashboard can be installed as an app much like the add-on and further customized to 
suit your visualization needs.

## FAQs

**Does the asset input import all assets each time it is run?**

No. When the asset import is run for the very first time, it will import all assets.
After that, all subsequent imports will only pull in assets that have been newly scanned since the 
last import occurred. In other words, if the last import of data occurred on June 5 at 12 PM, then only assets that 
have been scanned between then and now will be imported.

**Does the vulnerability definition import input import all definitions each time it is run?**

Yes, all vulnerability definitions will be imported each time it is run. For this reason, we recommend running this 
import at a maximum of once per day.

**Can I identify whether a vulnerability has been remediated?**

Yes, all vulnerability findings will have a `finding_status` when they are imported into Splunk. Those that are 
remediated will have a `finding_status` of `remediated`.

**How do I know if a vulnerability is new versus remediated?**

Check the `finding_status` of a vulnerability finding to determine whether it's new, remediated, or unchanged. The 
`new` and `remediated` statuses indicate new and remediated vulnerabilities respectively, while the status `found` 
indicates a previously found, unchanged vulnerability finding.

**Why am I not seeing any data in my add-on/dashboard?**

Check the selected index and time period for filtering data. These often need to be adjusted to filter correctly 
for assets and vulnerabilities. In addition, if the default `rapid7` index was defined for the inputs, make sure this 
input has already been created.

## Debugging

Two log files are available to help debug issues, usually located at <splunk_home>/var/log/splunk/:

splunkd.log - Splunk general log
ta_rapid7_insightvm_insightvm_asset_import.log - Log for the Rapid7 Technology Add-on

## Changelog:
* 1.5.2 - Update add-on for compatibility with Splunk 10.2
* 1.5.1 - Update Splunk SDK to make compatible with Splunk Cloud
* 1.5.0 - Update AOB dependencies
* 1.3.2 - Bug fix to remove user input conflicts with those in in default.meta
* 1.3.1 - Add debug logs that print imported assets and vulnerability finding counts
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
* 1.0.2 - Bug fix to ensure all vulnerabilities are returned by InsightVM on paged requests. Change maximum records per page to 100.
* 1.0.1 - Fixed bug to properly map Tags to Event Types for CIM | Added retry logic when saving import state fails due to Splunk `ConnectionError`
* 1.0.0 - Initial release of Rapid7 InsightVM Technology Add-On providing functionality to import asset and vulnerability findings from the InsightVM Platform
