# Silent Push App For Splunk

## OVERVIEW
* The Silent Push App For Splunk pulls Indicators from the Silent Push platform. The integration does correlation and provides dashboards for visualization.

## REQUIREMENTS

* Splunk Common Information Model (CIM datamodels) (To match the indicators with the datamodel events)(https://splunkbase.splunk.com/app/1621).
* Enterprise Security (To generate and see the notable events of correlated data)(https://splunkbase.splunk.com/app/263).


## COMPATIBILITY MATRIX
* Splunk version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent


## RECOMMENDED SYSTEM CONFIGURATION

* Standard Splunk Enterprise configuration of [Search Head, Indexer and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## RELEASE NOTES

### Version 3.0.1

* Bumped the minimum required Python version to 3.13 as per Splunk standards.

### Version 3.0.0

* Added a feature to collect data using Bulk Data Exports, Archive Exports and IP Context.
* Added support for the Threat Check.
* Added support for Feed Management.
* Updated `Indicators Overview` and `Correlatoin Overview` dahsboards.
* Removed `Account Usage` dashboard.
* Updated the `Live Scan and Live Screenshot` dashboard to utilize the scanondemand API.

### Version 2.1.1

* Fixed Feed and Filter Profile data collection issue. 

### Version 2.1.0

* Added a feature to collect data using organization exports and IOFA exports.
* Added accelerated datamodel search option to search matching algorithm for correlation settings.
* Updated UCC to v5.64.0.

### Version 2.0.3

* Resolved the issue for non-admin users to access the Correlation custom command.
* Resolved the issue for dropping fields in Enrichment custom command.

### Version 2.0.2

* Resolved notable creation issue.

### Version 2.0.1

* Given support for non-admin users to access On-demand dashboards.
* Updated Enrichment custom command to add silent push data to provided events.
* Updated Python SDK to v2.1.0.

### Version 2.0.0

* Added feature to collect data using filter profile.
* Supported the enrichment custom command to be used as a transforming command.
* Removed the feature of data collection using indicators.

### Version 1.0.1

* Updated data collection parameter for "domain" from "domaininfo" to "host_flags".

### Version 1.0.0

* Added data collection for Silent Push Indicators.
* Added field-based correlation feature to find sightings in Splunk events.
* Added feature to generate notable events of correlated data in Enterprise Security. 
* Added Indicators Overview, Correlation Overview, Account Usage and Live Investigation Dashboards such as Enrichment, PADNS, Reputation and Explore Web Data.

## INSTALLATION
Silent Push App For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `Silent Push App For Splunk` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## UPGRADE
### General upgrade steps:

1. Log in to Splunk Web and navigate to Silent Push App For Splunk -> Inputs.
2. Here disable all configured Inputs.
3. Navigate to Apps -> Manage Apps on Splunk menu bar.
4. Click Install app from file.
5. Click Choose file and select the `Silent Push App For Splunk` installation file.
6. Check the Upgrade checkbox.
7. Click on Upload.
8. Restart Splunk.

### Upgrade to v3.0.1

* Follow the `General upgrade steps` section.

### Upgrade to v3.0.0

* Follow the `General upgrade steps` section.

### Upgrade to v2.1.1

* Follow the `General upgrade steps` section.

### Upgrade to v2.1.0

* Follow the `General upgrade steps` section.

### Upgrade to v2.0.3

* Follow the `General upgrade steps` section.

### Upgrade to v2.0.2

* Follow the `General upgrade steps` section.

### Upgrade to v2.0.1

* Follow the `General upgrade steps` section.

### Upgrade to v2.0.0

* Upgrade from lower version to v2.0.0 is not supported.

### Upgrade to v1.0.1

* Follow the `General upgrade steps` section.


## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This App can be set up in two ways:

1. Standalone Mode
    * Install the Silent Push App For Splunk.
    * Follow all the steps mentioned in `App Setup` section to configure the App.
2. Distributed Environment
    * Install the Silent Push App For Splunk on the Search Head and Heavy Forwarder.
    * Follow the steps #1, #2 , #3 and #4 from  `App Setup` section on Heavy Forwarder.
    * Follow the step #5 from  `App Setup` section on Search Head.
    * In case of Search Head Clustering, make sure that steps #4 and #5 from `App Setup `are configured only on single search head. In such cases, the configuration will not be visible on other search heads. This is recommended approach.
    * Follow the step #5 from `App Setup` section on Search Head. Following these steps will replicate the configuration on all search heads.
3. Cloud Environment
    * Install the Silent Push App For Splunk on Search Head.
    * Install the Silent Push App For Splunk on IDM instance and configure it. (For the IDM instance Splunk support team will help) Or Setup the Silent Push App For Splunk on the On-Premise Heavy Forwarder.

## CONFIGURATION
Configure Silent Push App For Splunk

### App Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.
3. Configure the settings related to Splunk KVStore and Correlation in `KV Lookup Rest` and `Correlation Settings` section respectively. 
4. After the configuration of `KV Lookup Rest` and `Correlation Settings`, users can configure the inputs by specifying the required parameters.
5. Configure the settings related to correlation searches and lookups in `Correlation Settings` section.


### Account
To configure the Account,

1. Navigate to the `Configuration`.
2. Provide your Silent Push API Key and Account Name and click on `Add`.

| Silent Push App Account parameters   | Mandatory or Optional | Description                                 |
| ----------------------------  | --------------------- | ------------------------------------------- |
| Account name                  | Mandatory        | Enter a unique name for this account. |
| API Key                       | Mandatory        | Enter the API Key for this account.   |
| Add Threat Check API          | Optional         | Add Threat Check API to check indicators against Silent Push.   |
| Threat Check API Key          | Optional         | Enter the Threat Check API Key for this account.   |

### Proxy
To configure the Proxy,

1. Navigate to the `Configuration`.
2. Click on the `Proxy` tab. 
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy     |
|    Proxy Type            |     Optional            |  Type of the Proxy. Available options are http and socks5. Default is http.|
|    Host            |     Optional            |  Host or IP of the proxy server                                                        |
|    Port            |     Optional            |  Port for proxy server                                                                 |
|  Username          |     Optional             |  Username of the proxy server |
|  Password          |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging,

1. Navigate to the `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`. By default the log level is set to 'INFO'.

### KV Lookup Rest
To configure the Splunk KVStore,

1. Navigate to the `Configuration`.
2. Click on the `KV Lookup Rest` tab.
3. Provide the required values and click on Save.

| KVStore Parameters       | Mandatory or Optional | Description                                                  |
|------------------------|----------|-----------------------------------------------------------------------------|
| Collection Type   | Mandatory   | Select mode to create lookups. (Defult: Index)            |
| Indicator Indices       | Mandatory (Index)     | Master lookup for indicators will be updated based on the indicators data in the selected indices. |
| Splunk Rest Host URL | Mandatory (lookup) | Enter the Splunk rest host or localhost (without http(s) scheme) to collect data.(Default: localhost) |
| Port | Mandatory (lookup) | Enter the management port of the Splunk.(Default: 8089) |
| Splunk Username | Mandatory (lookup) | Not required if Splunk Rest Host URL is localhost or 127.0.0.1. Configured user should have at least power role capabilities | 
| Splunk Password | Mandatory (lookup) | Enter the password for Splunk account. No need to provide a Password if Splunk Rest Host URL is localhost or 127.0.0.1 |

> **NOTE** : If using Cluster environment then make sure that all fields are configured and splunkd port 8089 of Splunk Management is open for storing lookups.

### Correlation Settings
To configure the Correlation Settings,

1. Navigate to the `Configuration`.
2. Click on the `Correlation Settings` tab.
3. Provide the required values and click on Save.

| Correlation Parameters       | Mandatory or Optional | Description                                                  |
|------------------------|----------|-----------------------------------------------------------------------------|
| Enabled Indicator Types | Optional      | Select the indicator types you want to enable correlation for. Available options are Domain and IP.         |
| Search Matching Algorithm       | Optional       | Select the method for correlating indicators. Available options are Raw search, Datamodel Search and Accelerated Datamodel Search |
| Select Datamodels  | Optional      | Select the data models from the list                   |
| Select Accelerated Datamodels  | Optional      | Select the accelerated data models from the list                   |
| IP: Target Query    | Optional       | Splunk query to get events for correlation with IP Indicators.     
| IP: Target Fields  | Optional      | Comma separated list of fields to be used in correlation. |
| Domain: Target Query | Optional | Splunk query to get events for correlation with Domain Indicators. |
| Domain: Target Fields | Optional | Comma separated list of fields to be used in correlation. |


### Inputs
To configure the Inputs,

1. Navigate to the `Inputs`.
2. Click on `Create New Input`.
3. Provide the required information related to input and click on `Add` to configure the input.

| Input Parameter |  Mandatory or Optional | Description                                                  |
| --------------- | ---------------------- | ------------------------------------------------------------ |
| Name            | Mandatory              | A name to uniquely identify the input                        |
| Interval        | Mandatory              | Time interval of input in seconds. Default=86400. |
| Index           | Optional              | Select the index in which data should be collected. Only required if "Collection Type" is set to "Index".       |
| Silent Push Account| Mandatory      | Select the Silent Push Account for which you want to collect data.             |
|Threat Intelligence Type | Mandatory | Select the type to collect the data for Threat Intelligence.|
| Source UUID      | Optional              | Enter silent push threat intelligence feed UUID. Only required if "Feed" is selected in "Threat Intelligence Type". |
| Filter Profile UUID  | Optional              | Enter silent push threat intelligence filter profile UUID. Only required if "Filter Profile" is selected in "Threat Intelligence Type". |
| Organization Exports URL (Deprecated)  | Optional          | Enter silent push threat intelligence organization exports URL. Only required if "Organization Exports (Deprecated)" is selected in "Threat Intelligence Type". |
| IOFA Exports URL (Deprecated)  | Optional          | Enter silent push threat intelligence IOFA export URL. Only required if "IOFA Exports (Deprecated)" is selected in "Threat Intelligence Type". |
| Data Export URL  | Optional          | Enter silent push threat intelligence Data Export URL. Only required if "Data Exports" is selected in "Threat Intelligence Type". |

### Dashboards

1. Indicators Overview Dashboard:
    * This dashboard provides visualization of collected indicators from Silent Push platform.
    * Indicators Overview Dashboard Panels:
        1. Total Indicators
        2. Indicators Reported in Last Week
        3. Indicators Reported in Last Day
        4. Indicators Ingested Over Time
        5. Indicators Details

2. Correlation Overview Dashboard:
    * This dashboard provides visualization of matched indicators of Silent Push Indicators data with Splunk events.
    * Correlation Overview Dashboard Panels:
        1. Total Matched Indicators
        2. Matched Indicators by Type
        3. Matched Indicators Details

3. Enrichment:
    * Enrichment Dashboard Panels:
        1. Enrichment Details : This dashboard provides details of Indicator.

4. Threat Check and Feed Management:
    * Sub Dashboards of Threat Check and Feed Management:
        1. Threat Check:
            * This dashboard provides a visualization of threat check details for indicators from the Silent Push platform.
            * Threat Check Dashboard Panels:
                1. Threat Check Domain Indicators.
                2. Threat Check IP Indicators.

        2. Feed Management:
            * This dashboard adds indicators to the Silent Push platform.
            * Feed Management Dashboard Panels:
                1. Created/Updated Indicators.
                2. Invalid Indicators.

5. PADNS:
    * Sub Dashboards of PADNS:
        1. PADNS ASN's Seen for Domain: This dashboard provides details of ASN's Seen for Domain.
        2. PADNS Density Lookup: This dashboard provides details of Density Lookup.
        3. PADNS Forward Lookup: This dashboard provides details of Forward Lookup.
        4. PADNS Reverse Lookup: This dashboard provides details of Reverse Lookup.

6. Reputation:
    * Sub Dashboards of Reputation:
        1. ASN Reputation: This dashboard provides details of ASN Reputation.
        2. ASN Takedown Reputation: This dashboard provides details of ASN Takedown Reputation.
        3. IPv4 Reputation: This dashboard provides details of IPv4 Reputation.
        4. Name Server Reputation: This dashboard provides details of Name Server Reputation.
        5. Subnet Reputation: This dashboard provides details of Subnet Reputation.

7. Explore Web Data:
    * Sub Dashboards of Explore Web Data:
        1. Live Scan & Live Screenshot: This dashboard provides live details of provided URL.
        2. Web Scanner: This dashboard provides scan details of provided query.

8. Account Usage Dashboard:
    * This dashboard provides usage of configured accounts in Silent Push App For Splunk.
    * Account Usage Dashboard Panels:
        1. Account Usage Details


## LOOKUPS
* `silent_push_indicators_enrichment_domain`: This lookup contains enrichment data for domain.
* `silent_push_indicators_enrichment_ip`: This lookup contains enrichment data for IPv4 & IPv6.
* `silent_push_matched_indicators_domain`: This lookup contains the matched indicator data for Domain.
* `silent_push_matched_indicators_ip`: This lookup contains the matched indicator data for IP.

User can check data in lookup by running following SPL query in Splunk search: `| inputlookup <NAME OF LOOKUP>`

## SAVEDSEARCHES
This application contains the following saved searches:

* **update_silent_push_enrichment_domain_indicator_master_lookup** - Update Enrichment Domain Indicators from index to `silent_push_indicators_enrichment_domain`
* **update_silent_push_enrichment_ipv4_indicator_master_lookup** -Update Enrichment IPv4 Indicators from index to `silent_push_indicators_enrichment_ip`  
* **update_silent_push_enrichment_ipv6_indicator_master_lookup** - Update Enrichment IPv6 Indicators from index to `silent_push_indicators_enrichment_ip` .
* **silent_push_correlate_Domains_indicators** -Match Indicators of type Domains from the master_lookup against Splunk events .
* **silent_push_correlate_IPs_indicators** - Match Indicators of type IPs from the master_lookup against Splunk events.
* **silent_push_correlate_IPs_indicators_network_traffic** - Match indicators from the IPs master_lookup against Network_Traffic events.
* **silent_push_correlate_IPs_indicators_malware** - Match indicators from the IPs master_lookup against Malware events
* **silent_push_correlate_IPs_indicators_intrusion_detection** - Match indicators from the IPs master_lookup against Intrusion_Detection events
* **silent_push_correlate_IPs_indicators_authentication** - Match indicators from the IPs master_lookup against Authentication events.
* **silent_push_correlate_IPs_indicators_certificates** - Match indicators from the IPs master_lookup against Certificates events.
* **silent_push_correlate_IPs_indicators_endpoint_filesystem** - Match indicators from the IPs master_lookup against Endpoint (Filesystem dataset) events.
* **silent_push_correlate_IPs_indicators_endpoint_services** -  Match indicators from the IPs master_lookup against Endpoint (Services dataset) events.
* **silent_push_correlate_IPs_indicators_endpoint_processes** -  Match indicators from the IPs master_lookup against Endpoint (Processes dataset) events.
* **silent_push_correlate_IPs_indicators_email** -  Match indicators from the IPs master_lookup against Email events.
* **silent_push_correlate_IPs_indicators_compute_inventory** -  Match indicators from the IPs master_lookup against Compute_Inventory events.
* **silent_push_correlate_IPs_indicators_network_resolution** - Match indicators from the IPs master_lookup against Network_Resolution events.
* **silent_push_correlate_IPs_indicators_updates** -  Match indicators from the IPs master_lookup against Updates events.
* **silent_push_correlate_IPs_indicators_web** -  Match indicators from the IPs master_lookup against Web events.
* **silent_push_correlate_Domains_indicators_network_traffic** - Match indicators from the Domains master_lookup against Network_Traffic events .
* **silent_push_correlate_Domains_indicators_malware** - Match indicators from the Domains master_lookup against Malware events .
* **silent_push_correlate_Domains_indicators_intrusion_detection** - Match indicators from the Domains master_lookup against Intrusion_Detection events .
* **silent_push_correlate_Domains_indicators_authentication** - Match indicators from the Domains master_lookup against Authentication events .
* **silent_push_correlate_Domains_indicators_certificates** - Match indicators from the Domains master_lookup against Certificates events.
* **silent_push_correlate_Domains_indicators_endpoint_filesystem** - Match indicators from the Domains master_lookup against Endpoint (Filesystem dataset) events .
* **silent_push_correlate_Domains_indicators_endpoint_services** - Match indicators from the Domains master_lookup against Endpoint (Services dataset) events.
* **silent_push_correlate_Domains_indicators_endpoint_processes** - Match indicators from the Domains master_lookup against Endpoint (Processes dataset) events.
* **silent_push_correlate_Domains_indicators_email** -Match indicators from the Domains master_lookup against Email events.
* **silent_push_correlate_Domains_indicators_compute_inventory** - Match indicators from the Domains master_lookup against Compute_Inventory events .
* **silent_push_correlate_Domains_indicators_network_resolution** -Match indicators from the Domains master_lookup against Network_Resolution events
* **silent_push_correlate_Domains_indicators_updates** - Match indicators from the Domains master_lookup against Updates events.
* **silent_push_correlate_Domains_indicators_web** - Match indicators from the Domains master_lookup against Web events.
* **silent_push_correlate_IPs_indicators_network_traffic_acc** - Match indicators from the IPs master_lookup against accelerated Network_Traffic events.
* **silent_push_correlate_IPs_indicators_malware_acc** - Match indicators from the IPs master_lookup against accelerated Malware events.
* **silent_push_correlate_IPs_indicators_intrusion_detection_acc** - Match indicators from the IPs master_lookup against accelerated Intrusion_Detection events.
* **silent_push_correlate_IPs_indicators_authentication_acc** - Match indicators from the IPs master_lookup against accelerated Authentication events.
* **silent_push_correlate_IPs_indicators_certificates_acc** - Match indicators from the IPs master_lookup against accelerated Certificates events.
* **silent_push_correlate_IPs_indicators_endpoint_filesystem_acc** - Match indicators from the IPs master_lookup against accelerated Endpoint (Filesystem dataset) events.
* **silent_push_correlate_IPs_indicators_endpoint_services_acc** -  Match indicators from the IPs master_lookup against accelerated Endpoint (Services dataset) events.
* **silent_push_correlate_IPs_indicators_endpoint_processes_acc** -  Match indicators from the IPs master_lookup against accelerated Endpoint (Processes dataset) events.
* **silent_push_correlate_IPs_indicators_email_acc** -  Match indicators from the IPs master_lookup against accelerated Email events.
* **silent_push_correlate_IPs_indicators_network_resolution_acc** - Match indicators from the IPs master_lookup against accelerated Network_Resolution events.
* **silent_push_correlate_IPs_indicators_updates_acc** -  Match indicators from the IPs master_lookup against accelerated Updates events.
* **silent_push_correlate_IPs_indicators_web_acc** -  Match indicators from the IPs master_lookup against accelerated Web events.
* **silent_push_correlate_Domains_indicators_network_traffic_acc** - Match indicators from the Domains master_lookup against accelerated Network_Traffic events.
* **silent_push_correlate_Domains_indicators_malware_acc** - Match indicators from the Domains master_lookup against accelerated Malware events.
* **silent_push_correlate_Domains_indicators_intrusion_detection_acc** - Match indicators from the Domains master_lookup against accelerated Intrusion_Detection events.
* **silent_push_correlate_Domains_indicators_authentication_acc** - Match indicators from the Domains master_lookup against accelerated Authentication events.
* **silent_push_correlate_Domains_indicators_certificates_acc** - Match indicators from the Domains master_lookup against accelerated Certificates events.
* **silent_push_correlate_Domains_indicators_endpoint_filesystem_acc** - Match indicators from the Domains master_lookup against accelerated Endpoint (Filesystem dataset) events.
* **silent_push_correlate_Domains_indicators_endpoint_services_acc** - Match indicators from the Domains master_lookup against accelerated Endpoint (Services dataset) events.
* **silent_push_correlate_Domains_indicators_endpoint_processes_acc** - Match indicators from the Domains master_lookup against accelerated Endpoint (Processes dataset) events.
* **silent_push_correlate_Domains_indicators_email_acc** -Match indicators from the Domains master_lookup against accelerated Email events.
* **silent_push_correlate_Domains_indicators_network_resolution_acc** -Match indicators from the Domains master_lookup against accelerated Network_Resolution events.
* **silent_push_correlate_Domains_indicators_updates_acc** - Match indicators from the Domains master_lookup against accelerated Updates events.
* **silent_push_correlate_Domains_indicators_web_acc** - Match indicators from the Domains master_lookup against accelerated Web events.
* **Delete Older Domains from `silent_push_matched_indicators_domain` and `silent_push_indicators_enrichment_domain`.** - Domains older than specified time will be deleted from `silent_push_indicators_enrichment_domain` and `silent_push_matched_indicators_domain` lookups.
* **Delete Older IPs from `silent_push_matched_indicators_ip` and `silent_push_indicators_enrichment_ip`** - IPs older than specified time will be deleted from `silent_push_indicators_enrichment_ip` and `silent_push_matched_indicators_ip` lookups.

## Custom Commands
This application contains the following custom commands:

* **silentpushmatchindicators**
    * Description : This command performs the correlation between Silent Push indicator and provided Splunk events. 
    * Parameters :
        * indicator_type : The type of indicator to be matched.

* **silentpushpadnsdensitylookup**
    * Description : This command provides details of PADNS Density Lookup.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * qtype : Query type.
        * scope : exact or near match results by qtype - for qtype = ipv4: ip - exact match (default when qtype=ipv4) - subnet - summary of subnet for ipv4 - subnet_ips - density for all ips in subnet - asn - summary of asn for ipv4 - asn_subnets - summary for all subnets in asn - for qtype = asn: asn - summary of asn (default when qtype=asn) - asn_subnets - summary for all subnets in asn - for qtype = nssrv or qtype = mxsrv: host - exact match (default when qtype=nssrv or qtype=mxsrv) - domain - match all hosts in this domain (domain extracted from {query}) - subdomain - match all hosts at this subdomain level (i.e. *.{query}).
        * query : Specify a value to lookup - name of NS or MX server - hash of NS or MX server - IPv4 or IPv6 address - AS number.

* **silentpushenrichmentqueries**
    * Description : This command provides details of Indicators.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * indicator : Indicator value/field.
        * explain : Show details of data used to calculate the different scores in the response - 0: do not show details - 1: show underlying data used to calculate scores.
        * scan_data : Show details of data collected from host scanning - 0: do not show details - 1: show collected data.
        * field_flag : If this parameter is set to 1 then the indicator field value will be treated as a field name in transforming command otherwise it will be a value given for indicator.

* **silentpushpadnsforwardlookup**
    * Description : This command provides details of PADNS Forward Lookup.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * qtype : DNS record type.
        * qname : Name or ip address to lookup - wildcards are supported in name string - IPv4 or IPv6.
        * netmask : May be given for qtypes A and AAAA - defaults - A: 32 - AAAA: 128 - minimum - A: 20 - AAAA: 64.
        * subdomains : include or exclude subdomains from qtype a or aaaa results.
        * with_metadata : include metadata object in response.
        * regex : Regular expression match for domain/host - overrides qname parameter - must be valid re2 regular expression.
        * match : limit results to self-hosted infrastructure for qtype mx or ns - strict (default): find all matching results - self: only show results where mx or ns records are in the same domain as qname. 
        * first_seen_before : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * first_seen_after : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * last_seen_before : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * last_seen_after : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * as_of : Only return records where the as_of timestamp equivalent is between the first_seen and the last_seen timestamp - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * sort : Order results in specified order (column/order) - may be repeated with different column names to produce a nested sorting effect - columns: last_seen, first_seen, query, answer - order: asc, desc - separate multiple values with semi-colon (;)
        * limit : Number of results to return.
        * skip : Number of results to skip.

* **silentpushpadnsreverselookup**
    * Description : This command provides details of PADNS Reverse Lookup.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * qtype : DNS record type.
        * qname : Name or ip address to lookup - wildcards are supported in name string - IPv4 or IPv6.
        * netmask : May be given for qtypes A and AAAA - defaults - A: 32 - AAAA: 128 - minimum - A: 20 - AAAA: 64.
        * subdomains : include or exclude subdomains from qtype a or aaaa results.
        * with_metadata : include metadata object in response.
        * regex : Regular expression match for domain/host - overrides qname parameter - must be valid re2 regular expression.
        * first_seen_before : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * first_seen_after : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * last_seen_before : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * last_seen_after : First_seen timestamp must be on or after this time - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * as_of : Only return records where the as_of timestamp equivalent is between the first_seen and the last_seen timestamp - time input options: fixed date: yyyy-mm-dd (2021-07-09), fixed epoch: number (1625834953), relative time seconds ago: negative number (-172800), relative fixed time period ago: negative number with time period (-36h / -5d / -3w / -6m) h: hours, d: days, w: weeks, m: months.
        * sort : Order results in specified order (column/order) - may be repeated with different column names to produce a nested sorting effect - columns: last_seen, first_seen, query, answer - order: asc, desc - separate multiple values with semi-colon (;)
        * limit : Number of results to return.
        * skip : Number of results to skip.

* **silentpushasnsseenfordomain**
    * Description : This command provides details of PADNS ASN's Seen for Domain.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * domain : Domain name.
        * result_format : Return ASN list only, or detailed information, or all A records in an ASN.
        * asnum : Return A records in this ASN, if result_format = records.
        * sort : Order results in specified order (column/order) - may be repeated with different column names to produce a nested sorting effect - columns: last_seen, first_seen, query, answer - order: asc, desc - separate multiple values with semi-colon (;).
        * limit : Number of results to return.
        * skip : Number of results to skip.

* **silentpushasnreputation**
    * Description : This command provides details of ASN Reputation.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * asn : AS number.
        * explain : Show information used to calculate the reputation score{0{uncheck} = (default) do not show and 1{check} = show details}.

* **silentpushasntakedownreputation**
    * Description : This command provides details of ASN Takedown Reputation.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * asn : AS number.
        * explain : Show information used to calculate the reputation score{0{uncheck} = (default) do not show and 1{check} = show details}.

* **silentpushipv4reputation**
    * Description : This command provides details of IPv4 Reputation.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * ipv4 : IPv4 address.
        * explain : Show information used to calculate the reputation score{0{uncheck} = (default) do not show and 1{check} = show details}.

* **silentpushnameserverreputation**
    * Description : This command provides details of Name Server Reputation.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * nameserver : Server name.
        * explain : Show information used to calculate the reputation score{0{uncheck} = (default) do not show and 1{check} = show details}.

* **silentpushsubnetreputation**
    * Description : This command provides details of Subnet Reputation.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * subnet : IPv4 subnet.
        * mask : Subnet Mask.
        * explain : Show information used to calculate the reputation score{0{uncheck} = (default) do not show and 1{check} = show details}.

* **silentpushliveurlscan**
    * Description : This command provides details of Live URL Scan.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * url : Provide URL.
        * platform : Select type of Platform.
        * OS : Select type of OS.
        * browser : Select type of Browser.
        * region : Select type of Region.

* **silentpushwebscandata**
    * Description : This command provides details of provided query.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * query : Provide SPQL query (eg: domain = mandiant.* AND domain != mandiant.com AND scan_date &gt; now-30d).
        * sort : Select the field by which the sorting should be done. Maximum 5 field sorting is allowed.
        * limit : Provide the limit. default value is 100.
        * page : Provide the desired page no. default value is 1.

* **silentpushthreatcheck**
    * Description : This command provides details of Threat Check for provided indicators.
    * Parameters :
        * account_name : Provide configured Silent Push Account Name.
        * indicators : Provide indicator value.
        * data_source : Select type of data source.
        * index_field : Select type of index field.
        * datamodel_field : Select type of datamodel field.


## SEARCHES
* To see ingested data for Silent Push App For Splunk, select the `Search` tab. Search `` `silent_push_indicator_indices` sourcetype=silent_push_*``.

## TROUBLESHOOTING
### General Checks
* To troubleshoot Silent Push App For Splunk, check `$SPLUNK_HOME/var/log/Splunk/ta_silent_push_*.log` or user can search `index="_internal" source=*ta_silent_push_*.log*` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_silent_push_*.log* ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* If you are facing a problem related to ip address, then run the query `| inputlookup silent_push_indicators_enrichment_ip`
* If you are facing a problem related to domain address, then run the query `| inputlookup  silent_push_indicators_enrichment_domain`
* App icons are not showing up: The App does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.


### Data Collection
* If data collection is not working then ensure that the internet is active (On a proxy machine, if proxy is enabled) and also ensure that the kvstore is enabled.
* Check `ta_silent_push*.log*` file for Silent Push App For Splunk data collection for any relevant error messages.

### Correlation
* Note that correlation is field based and it will only match to those Splunk events having value exactly same as values in configured fields on Correlation Page.
* Check `ta_silent_push_correlation_command.log` file for further analysis.

#### Master Lookup
* If it seems that all the data of indicators from the Splunk index is not available in `silent_push_indicators_enrichment_<indicator_type>` lookup, then execute the savedsearch `update_silent_push_enrichment_<indicator_type>_indicator_master_lookup` manually over a larger time range to refill the lookup.

#### Custom Commands

* silentpushmatchindicators
    * Check that indices of the collected Indicators data are stored in `Indicator Indices` parameter of correlation settings.
    * Check that `silent_push_matched_indicators_<indicator_type>` lookup is not empty and also ensure that `silent_push_correlate_<indicator_type>_indicators` savedsearch is enabled.
    * Check `ta_silent_push_correlation_command.log` file for further analysis.
* silentpushenrichmentqueries
    * Check `ta_silent_push_enrichment_queries_custom_command.log` file for further analysis.
* silentpushpadnsdensitylookup
    * Check `ta_silent_push_density_lookup_custom_command.log` file for further analysis.
* silentpushpadnsforwardlookup
    * Check `ta_silent_push_forward_lookup_custom_command.log` file for further analysis.
* silentpushpadnsreverselookup
    * Check `ta_silent_push_reverse_lookup_custom_command.log` file for further analysis.
* silentpushasnsseenfordomain
    * Check `ta_silent_push_asnseen_for_domain_custom_command.log` file for further analysis.
* silentpushasnreputation
    * Check `ta_silent_push_asn_reputation_custom_command.log` file for further analysis.
* silentpushasntakedownreputation
    * Check `ta_silent_push_asn_takedown_reputation_custom_command.log` file for further analysis.
* silentpushipv4reputation
    * Check `ta_silent_push_ipv4_reputation_custom_command.log` file for further analysis.
* silentpushnameserverreputation
    * Check `ta_silent_push_nameserver_reputation_custom_command.log` file for further analysis.
* silentpushsubnetreputation
    * Check `ta_silent_push_subnet_reputation_custom_command.log` file for further analysis.
* silentpushliveurlscan
    * Check `ta_silent_push_live_url_scan_custom_command.log` file for further analysis.
* silentpushwebscandata
    * Check `ta_silent_push_web_scan_data_custom_command.log` file for further analysis.
* silentpushthreatcheck
    * Check `ta_silent_push_threat_check_custom_command.log` file for further analysis.

### Dashboards
* Panel not populating:

1. Indicators Overview Dashboard:
    * If dashboard panels are not populating data, it is possible that App's Saved Searches have not yet encountered newly ingested data on their previous execution. Please check Next Schedule Time in Settings -> Searches, reports and alerts. Most likely the panels will be populated once all saved searches complete their next execution.
    * The Feed and Feed Categories values will be available solely for the enriched data.

2. Correlation Overview Dashboard:
    * If the data is not populated in the above listed panels, then ensure that Indicator data is collected in Splunk and the `silent_push_matched_indicators_<indicator_type>` lookup is filled with the latest data.
    * Also please ensure that savedsearches `silent_push_correlate_<indicator_type>_indicators` or `silent_push_correlate_<indicator_type>_indicators_<datamodel>` savedsearches are enabled.
    * If dashboard panels are not populating data, it is possible that App's Saved Searches have not yet encountered newly ingested data on their previous execution. Please check Next Schedule Time in Settings -> Searches, reports and alerts. Most likely the panels will be populated once all saved searches complete their next execution.
    * In Matched Indicators Details panel there is column `Live investigation` if you click on Live investigation cell it will redirect to Enrichment dashboard with the indicator of that row.
    * In Matched Indicators Details panel there is column `Local investigation` if you click on Local investigation cell it will redirect to Search page with its indicator and index. The icon won't be click if the perticular indicator were matched with the datamodel query.
    * In Matched Indicators Details panel there is column `See Notable Events` if you click on See Notable Events cell it will redirect to Incident Review dashboard of Enterprise Security App with the clicked row indicator value. This cell link will only work if Enterprise Security app is present in the same splunk instance. 

3. Enrichment:
    * Enrichment: Check `ta_silent_push_enrichment_queries_custom_command.log` file for further analysis.

4. Threat Check:
    * If the search is automatically canceled, update the `max_search_time` parameter in limits.conf and the `ui_inactivity_timeout` setting in web.conf.
    * Threat Check: Check `ta_silent_push_threat_check_custom_command.log` file for further analysis.

5. Feed Management:
    * Feed Management: Check `ta_silent_push_feed_management.log` file for further analysis.

6. PADNS:
    * PADNS ASN's Seen for Domain: Check `ta_silent_push_asnseen_for_domain_custom_command.log` file for further analysis.
    * PADNS Density Lookup: Check `ta_silent_push_density_lookup_custom_command.log` file for further analysis.
    * PADNS Forward Lookup: Check `ta_silent_push_forward_lookup_custom_command.log` file for further analysis.
    * PADNS Reverse Lookup: Check `ta_silent_push_reverse_lookup_custom_command.log` file for further analysis.

7. Reputation:
    * ASN Reputation: Check `ta_silent_push_asn_reputation_custom_command.log` file for further analysis.
    * ASN Takedown Reputation: Check `ta_silent_push_asn_takedown_reputation_custom_command.log` file for further analysis.
    * IPv4 Reputation: Check `ta_silent_push_ipv4_reputation_custom_command.log` file for further analysis.
    * Name Server Reputation: Check `ta_silent_push_nameserver_reputation_custom_command.log` file for further analysis.
    * Subnet Reputation: Check `ta_silent_push_subnet_reputation_custom_command.log` file for further analysis.

8. Explore Web Data:
    * Live Scan & Live Screenshot: Check `ta_silent_push_live_url_scan_custom_command.log` file for further analysis.
    * Web Scanner: Check `ta_silent_push_web_scan_data_custom_command` file for further analysis.

9. Account Usage Dashboard:
    * Check `ta_silent_push_account_usage_command.log` file for further analysis.


## BINARY FILE DECLARATION

* md.cpython-39-x86_64-linux-gnu.so - This binary file is provided along with Charset-Normalizer module and source code for the same can be found at https://pypi.org/project/charset-normalizer/

## SUPPORT
* Support Offered: Yes
* Support Details:
    * Email: support@silentpush.com

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/SilentPushAppForSplunk
* Remove $SPLUNK_HOME/var/log/Splunk/ta_silent_push_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

#### SILENT PUSH INC. ©2026
