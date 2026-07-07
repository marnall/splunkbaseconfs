# Lansweeper Add-on For Splunk

## OVERVIEW
Lansweeper is an application that gathers hardware and software information of computers and other devices on a computer network for management and compliance and audit purposes. The application also encompasses a ticket-based help desk system and capabilities for software updates on target devices.

* This Add-on can be used to get the IP/MAC related information from Lansweeper either from CIM mapped fields or fields from indexed events into Splunk
* Author - Lansweeper
* Version - 1.2.0

## Compatibility Matrix
* Splunk version: 9.4.x, 9.3.x, 9.2.x, 9.1.x
* Python version: Python3
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome and Firefox

## Requirements
* For proper functioning of correlation searches feature the integration requires Splunk ES installed in the same instance.
* Please refer to the Splunk Document (https://docs.splunk.com/Documentation/ES/latest/Install/DeploymentPlanning) for Splunk ES system requirements

## RELEASE NOTES
### Version: 1.2.0
* Upgraded AOB to latest(4.5.0) version

### Version: 1.1.0
* Upgraded AOB to latest(4.1.1) version

### Version: 1.0.0
* Added correlation search and integrated with the workflow actions to create notable events and find asset data from CIM compliant Splunk events.
* Added Investigation Dashboards.
* Added feature of workflow action to navigate to the Investigation Dashboards on clicking the field.
* Added feature for lsip and lsmac custom commands.

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## INSTALLATION
Lansweeper Add-on For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/ folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `TA-Lansweeper` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## UPGRADATION
Follow the below steps to upgrade the Add-on.

1. Go to Apps > Manage Apps and click on the "Install app from file".
2. Click on "Choose File" and select the TA-Lansweeper installation file.
3. Check the Upgrade app checkbox and click on Upload.
4. Follow the prompt and Restart the Splunk instance if required.

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
This Add-on can be set up in two ways:

1. Standalone Mode
    * Install the Lansweeper Add-on For Splunk.
    * Follow all the steps mentioned in the `Add-on Setup` section to configure the Add-on.
2. Distributed Environment
    * Install the Lansweeper Add-on For Splunk on the Search Head.
    * This add-on has no feature for the collection of data, so no need to install it in the indexer and Heavy Forwarder.
    * Follow all the steps on Search Head mentioned in the `Add-on Setup` section to configure the Add-on.


## CONFIGURATION
Configure Lansweeper Add-on For Splunk:

### Add-on Setup
1. Configure the account from which the assets data needs to be retrieved. Detailed steps and information for Account Configuration can be found in the `Account` section.
2. Users can also configure settings corresponding to the `Proxy` or `Logging` in their respective sections.
3. Configure the settings related to workflow actions in the `Add-on Settings` section.

> **NOTE** :  There might be some delay for the dashboards corresponding to `Investigation` to populate, as these dashboards are based on custom commands.

### Account
To configure the Account,

1. Navigate to the `Configuration`.
2. Provide your Lansweeper credentials and click on `Add`.

| Lansweeper Account parameters   | Mandatory or Optional | Description                                 |
| ------------------------------  | --------------------- | ------------------------------------------- |
|Token                            | Mandatory             | The identity code of the application.       |

### Proxy
To configure the Proxy,

1. Navigate to the `Configuration`.
2. Click on the `Proxy` tab.
3. Provide your Proxy credentials and click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------   |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                 |       Optional           |  To enable or disable the proxy                                                      |
|    Proxy Type             |     Mandatory(If Enable checkbox checked)|  Select proxy type that you want to use from the dropdown (supports HTTP/HTTPS/SOCK4/SOCK5)|
|    Proxy Host             |     Mandatory(If Enable checkbox checked)|  Host or IP of the proxy server                                                        |
|    Proxy Port             |     Mandatory(If Enable checkbox checked)|  Port for proxy server                                                                 |
|  Proxy Username           |     Optional             |  Username of the proxy server |
|  Proxy Password           |     Optional             |  Password of the proxy server |

### Logging
To configure the Logging,

1. Navigate to the `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`.

> **NOTE** : By default value is Info.

### Add-on Settings
To configure the Additional parameter,

1. Navigate to the `Configuration`.
2. Click on the `Add-on Settings` tab.
3. Provide "IP address fields" and "MAC address fields" and click on `Save`.

| Add-on Settings parameters      | Mandatory or Optional | Description                                 |
| ------------------------------  | --------------------- | ------------------------------------------- |
|IP address fields                | Mandatory             | comma-separated fields containing IP addresses for workflow actions.|
|MAC address fields               | Mandatory             | comma-separated fields containing MAC addresses for workflow actions.|


##  CUSTOM COMMANDS
This application contains the following saved searches:

* **lsip** - Get assets data for given IP addresses for given Sites.

| Argument                  |   Mandatory or Optional  |                Description                                                             |
|  ----------------------   |   --------------------   |----------------------------------------------------------------------------------------|
|    site_ids               |       Mandatory          |  The unique key of the Lansweeper workspace from which to fetch data.                  |
|    ips                    |     Mandatory(If field argument not provided)|  The IP address of the asset whose data we are fetching.           |
|    field                  |     Mandatory(If ips argument not provided)|  Field from the search result containing the IP address.             |
|    max_results_per_site   |     Optional             |  Limit of events returned on request  (default : 500)                                  |

i.e. |  lsip site_ids="site_id_123" ips="1.0.0.0"
     index="main" | lsip site_ids="site_id_123" field=ip_addr

* **lsmac** - Get assets data for given MAC addresses for given Sites.

| Argument                  |   Mandatory or Optional  |                Description                                                             |
|  ----------------------   |   --------------------   |----------------------------------------------------------------------------------------|
|    site_ids               |       Mandatory          |  The unique key of the Lansweeper workspace from which to fetch data.                  |
|    macs                   |     Mandatory(If field argument not provided)|  The MAC address of the asset whose data we are fetching.           |
|    field                  |     Mandatory(If macs argument not provided)|  Field from the search result containing the MAC address.             |
|    max_results_per_site   |     Optional             |  Limit of events returned on request  (default : 500)                                  |

i.e. |  lsmac site_ids="site_id_123" macs="2c549188c9e3"
     index="main"| lsmac site_ids="site_id_123" field=mac_addr

> **NOTE** : Both commands support site_ids=`*` which means site_ids for all which are present in lookup.    
             i.e. |  lsip site_ids=`*` ips="190.0.0.8".
             
> **NOTE** : For extracting key-value field extraction please use "| kv" at the end of the custom command.
             i.e. |  lsip site_ids="site_id_123" ips="190.0.0.8" | kv
             
> **NOTE** : Both commands support max_results_per_site=`*` which means fetch all data according to the options given in the custom command.
             i.e. |  lsip site_ids=`*` ips="190.0.0.8" max_results_per_site=`*`


## CORRELATION SEARCHES
This application contains the following correlation searches:

* **Lansweeper investigation by IP** - It generates Notable events every 30 minutes for a given search in Splunk ES and fetches the asset information by IPs obtained from given search results.
* **Lansweeper investigation by MAC** - It generates Notable events every 30 minutes for a given search in Splunk ES and fetches the asset information by MACs obtained from given search results.

Users can view the result of the last execution of savedsearch by clicking on the `View Recent` button for the particular savedsearch on the `Searches, Reports, and Alerts` tab on Splunk

> **NOTE** : To use these correlation searches first enable them from the `Searches, Reports, and Alerts` tab on Splunk.

### STEPS TO EDIT CORRELATION SEARCHES

1. Navigate to Configure> Content > Content Management in Splunk ES.
2. Click the title of the correlation search you want to edit.
3. Edit the Search query field.
4. Expand the Notable present in Adaptive Response Actions.
5. Edit the Title with field name given in Search in between $<field_name>$.
6. Click on Save to apply changes to the correlation search.

> **Note** : Open a new tab and verify the changes in the Incident Review tab with the newly Added field in Title.

## LOOKUPS
* `lansweeper_site_mapping_lookup`: This lookup contains the site ID and site name allowed for provided token value.

Users can check data in lookup by running the following SPL query in Splunk search: `| inputlookup <NAME OF LOOKUP>`

## WORKFLOW ACTION
* **Lansweeper investigate by IP Address** - It redirects to the Investigation dashboard and fetches asset information for the selected IP field value. Workflow actions are applied to the fields configured in the Add-on Settings tab.
* **Lansweeper investigate by MAC Address** - It redirects to the Investigation dashboard and fetches asset information for the selected MAC field value. Workflow actions are applied to the fields configured in the Add-on Settings tab.

## OPEN SOURCE COMPONENTS AND LICENSES
Some of the components included in "Lansweeper Add-on For Splunk" are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* ipaddress version 1.0.23 https://pypi.org/project/ipaddress (LICENSE https://github.com/phihag/ipaddress/blob/master/LICENSE)
* macaddress version 1.1.3 https://pypi.org/project/macaddress (LICENSE https://github.com/mentalisttraceur/python-macaddress/blob/master/LICENSE) 


## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/TA-Lansweeper
* Remove $SPLUNK_HOME/var/log/Splunk/ta_lansweeper_*.log**.
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## KNOWN-ISSUES
* Do not use Real-time time range options when using the two provided custom commands or in the Investigation dashboard.

## TROUBLESHOOTING
### General Checks
* To troubleshoot Lansweeper Add-on For Splunk, check $SPLUNK_HOME/var/log/Splunk/ta_lansweeper*.log or user can search `index="_internal" source=*ta_lansweeper*.log` query to see all the logs in UI. Also, user can use `index="_internal" source=*ta_lansweeper*.log ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this Add-on will be generated in the `$SPLUNK_HOME/var/log/Splunk/` directory.
* App icons are not showing up: The Add-on does not require a restart after the installation for all functionalities to work. However, the icons will be visible after one Splunk restart post-installation.
* After updating fields for workflow actions in the Add-on Settings page, open a new tab or clear the browser cache to reflect the changes.

#### Correlation
* Check that the correlation searches are enabled or not from the `Searches, Reports, and Alerts` tab on Splunk.
* Check that for given search query there is any data for the past 30 minutes.
* Check that the proper Title is given for the correlation search.
#### Lookup
* If it seems that the ``lansweeper_site_mapping_lookup`` lookup is not having any site_id, then check that the newer token is generated or not.
* Check `ta_lansweeper_validators.log` file for further analysis.
#### Custom Command
* Check the newer token is generated for your application, then update the newer one in Configuration -> Account page.
* Check `ta_lansweeper_lsip_command.log` or `ta_lansweeper_lsmac_command.log` file for further analysis.

### Dashboards
* Panel not populating in Investigation dashboard:

    1. Live Investigation mode:
        * If the data is not populated then ensure that the ``lansweeper_site_mapping_lookup`` lookup is filled with Site IDs & Site Names.
        * Check `ta_lansweeper_validators.log` file for lookup filled successfully or not.
        * Another scenario can be the newer token is generated for the same application. In this case, update the new token in Configuration -> Account page.
        * Proxy server can be down, in that case use a working proxy server.

## SUPPORT
* Email: support@lansweeper.com

## BINARY FILE DECLARATION
* markupsafe - MarkupSafe implements a text object that escapes characters so it is safe to use in HTML and XML.https://pypi.org/project/MarkupSafe/

### Copyright (c) 2025 Lansweeper. All rights reserved.
