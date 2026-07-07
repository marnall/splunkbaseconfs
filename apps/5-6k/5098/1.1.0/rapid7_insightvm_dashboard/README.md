# Rapid7 InsightVM Dashboard


## Description

The Rapid7 InsightVM Dashboard is used for visualizing data that has been ingested from InsightVM via the Rapid7 
InsightVM Technology Add-On. The dashboard is intended to be a starting point for data visualization, and users are 
encouraged to further enhance and customize the dashboard as desired.

There are two dashboards included to start: the InsightVM Assets dashboard used for visualizing asset details, and 
the InsightVM Vulnerability Findings dashboard used for visualizing details of vulnerability instances found within 
assets. This Dashboard is meant to complement the `Rapid7 InsightVM Technology Add-On` listed on Splunkbase.


The Rapid7 InsightVM Dashboard and Technology Add-On are recommended in place of the Nexpose Dashboard and Technology Add-On listed on Splunkbase for all InsightVM customers.

## Installation

There are two ways to install the dashboard - via the Splunk app listing, or manually with a provided dashboard 
package. To install the dashboard via the app listing, follow these steps:

1. From the `Apps` menu in Splunk, select `Manage Apps`
2. Select `Browse More Apps`
3. Do a search for the "Rapid7 InsightVM Dashboard"
4. Select `Install` from the app listing
5. Perform a restart of Splunk when prompted

To install the add-on manually, follow these steps:

1. From the `Apps` menu in Splunk, select `Manage Apps`
2. Select `Install app from file`
3. Select the InsightVM Dashboard
4. Perform a restart of Splunk when prompted

The add-on should now appear as `Rapid7 InsightVM Dashboard` under the Apps menu in Splunk.

## Configuration

This dashboard must be used alongside the Rapid7 InsightVM Technology Add-On. The add-on serves as the method for 
retrieving asset and vulnerability data, which is then visualized with this dashboard. There are three sourcetypes to 
keep in mind when searching or creating visualizations of this data:

* rapid7:insightvm:asset
* rapid7:insightvm:asset:vulnerability_finding
* rapid7:insightvm:vulnerability_definition

### InsightVM Asset Dashboard

There are a few different components in the Asset Dashboard that display or visualize the imported InsightVM asset 
data. It's important to ensure that the correct index is selected here, as otherwise you may not see any data. The 
default index for the Dashboard follows that of the Technology Add-On and will be set to `rapid7`, but you can update 
this if a different one was chosen for data import.

Additional filtering can be done with the `Tags` dropdown, which uses tags - aggregates of site, asset groups, and 
asset tags - retrieved from InsightVM, and the `Time Period` dropdown, which allows you to select a date range for 
your data.

| Field  | Description  |
|---|---|
| Total Assets Scanned  | The total number scanned across imported assets |
| Total Asset Riskscore | The total risk score across imported assets |
| Average Asset Riskscore | The average risk score across imported assets |
| Most Common Operating Systems | A chart showing a breakdown of operating systems in the environment |
| Most Vulnerable Hosts | A table listing most vulnerable hosts based on risk score |

### InsightVM Vulnerability Findings Dashboard

There are a few different components in the Vulnerability Dashboard that display or visualize the imported InsightVM 
vulnerability data. It's important to ensure that the correct index is selected here, as otherwise you may not see 
any data.

Additional filtering can be done with the `Time Period` dropdown, which allows you to select a date range for your 
data.

| Field  | Description  |
|---|---|
| New Vulnerability Findings | A count of new vulnerability findings based on the latest import of InsightVM data |
| Remediated Vulnerability Findings | A count of remediated vulnerability findings based on the latest import of InsightVM data |
| Active Vulnerabilities by Solution Type | A chart showing a breakdown of solutions available for active vulnerabilities |
| Top Vulnerability Occurrences | A table listing the most frequently occurring vulnerabilities across assets |
| Top Solutions by Asset Count | A table listing the top solutions based on their applicability across assets |

## Changelog:

1.1.0 - Addition of Asset and Vulnerability Finding Dashboards
1.0.1 - Removed unnecessary index dependency
1.0.0 - Initial release of Dashboard for use with Rapid7 InsightVM Technology Add-On
