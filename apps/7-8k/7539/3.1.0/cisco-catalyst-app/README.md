# Cisco Enterprise Networking for Splunk Platform


## OVERVIEW
The **Cisco Enterprise Networking for Splunk Platform** presents visualizations in dashboards for different Cisco Products - **Cisco Identity Services Engine**, **Cisco SD-WAN**, **Cisco Catalyst Center**, **Cisco Cyber Vision** **Cisco Meraki** **Cisco ThousandEyes** and **Cisco Tenable**. The App uses the data collected by "Cisco Catalyst Add-on for Splunk" , "Cisco Catalyst Enhanced Netflow Add-on for Splunk", "Cisco Meraki Add-on for Splunk", and "Cisco ThousandEyes App for Splunk".

* Author -  Cisco Systems
* Version - 3.1.0
* Build - 1
* Prerequisites - This application is dependent on the **Cisco Catalyst Add-on for Splunk** (TA_cisco_catalyst) and **Cisco Catalyst Enhanced Netflow Add-on for Splunk** (splunk_app_stream_ipfix_cisco_hsl)


## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox & Safari
* OS: Linux, macOS, Windows
* Splunk Enterprise Version: Splunk 9.3.x, Splunk 9.4.x, Splunk 10.0.x
* Supported Splunk Deployment: Standalone, Distributed & Cluster

## RELEASE NOTES

### Version 3.1.0
* Added the dashboards visualizations for Cisco Identity Services Engine, Cisco Catalyst Center. 
* Introduced a new Analytics Reports and Steps Report Section:-
    1. Overview Reports Dashboard
    2. Endpoint Compliance Dashboard
    3. Network Compliance Dashboard
    4. Master Endpoint Record Dashboard
    5. Step 1 Report Dashboard
    6. Step 2 Report Dashboard
    7. Step 3 Report Dashboard
    8. Step 4 Report Dashboard

### Version 3.0.0
* Added the dashboards visualizations for Cisco Meraki, Cisco ThousandEyes.
* Introduced a new Sensors dashboard containing a centralized view for Cisco Meraki Sensors.
* Rebranding of Cisco DNA Center to Cisco Catalyst Center

### Version 2.0.0
* Added the dashboards visualizations for Cisco Identity Services Engine, Cisco Catalyst Center and Cisco SD-WAN product. 
* Modified the index macro from index=* to index IN ("main").

### Version 1.1.0
* Added the dashboards visualizations for Cisco Cyber Vision product.

### Version 1.0.0
* The App has the dashboards visualizing the data for the following products:
    * Cisco Identity Services Engine
    * Cisco SD-WAN
    * Cisco Catalyst Center
    * Cisco Cyber Vision
* Added field extractions for the dashboards

## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer, and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. "Cisco Catalyst Add-on for Splunk", which parses collected Syslog and NetFlow data. Additionally, it also collects and parses data of Catalyst Center through Modular Inputs.
    2. "Cisco Enterprise Networking for Splunk Platform", which adds dashboards to visualize Syslog, Modular Input and NetFlow data.
    3. "Cisco Catalyst Add-on for Splunk", which parses and collects data for Cisco Identity Services Engine, Cisco SD-WAN and Cisco Cyber Vision 
    4. Cisco Meraki Add-on for Splunk, "Cisco ThousandEyes App for Splunk" which parses and collects data for Cisco Meraki and Cisco ThousandEyes.

* This app can be set up in two ways:

    1. Standalone Mode

        * Install the "Cisco Enterprise Networking for Splunk Platform" and "Cisco Catalyst Add-on for Splunk" on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
        * The "Cisco Enterprise Networking for Splunk Platform" uses the data parsed by the "Cisco Catalyst Add-on for Splunk" and builds dashboards on it.

    2. Distributed Environment

        * Install the "Cisco Enterprise Networking for Splunk Platform" and "Cisco Catalyst Add-on for Splunk" on the search head.
        * Install only "Cisco Catalyst Add-on for Splunk" on the heavy forwarder. 
        * User needs to manually create an index on the Indexer (No need to install "Cisco Enterprise Networking for Splunk Platform" on Indexer).
        > Note: Installation of "Cisco Catalyst Add-on for Splunk" on Indexer is required in case of universal forwarder.

## INSTALLATION
 `Cisco Enterprise Networking for Splunk Platform` can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/ directory.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install the app from file`.
3. Click `Choose file` and select the `cisco-catalyst-app` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted. (In case of Adding .tar or .spl extracted files to directly into $SPLUNK_HOME/etc/apps/ directory, restart is required)

# UPGRADE
## General Upgrade Steps
* Go to Apps > Manage Apps and click on the "Install app from file".
*  Click on "Choose File" and select the 'Cisco Enterprise Networking for Splunk Platform' installation file.
* Check the Upgrade app checkbox and click on Upload.
* Restart the Splunk instance.
## Upgrade to v3.1.0
* Follow the General upgrade steps section.

## Upgrade to v3.0.0
* Follow the General upgrade steps section.

##  Upgrade to v2.0.0
* Upgrade the index to main
* Follow the General upgrade steps section  

##  Upgrade to v1.1.0
* Follow the General upgrade steps section.

## OPEN SOURCE COMPONENTS AND LICENSES

* Some of the components included in the "Cisco Enterprise Networking for Splunk Platform" are licensed under free or open source licenses. We wish to thank the contributors to those projects.

* jQuery
    * version: 3.5.0
    * URL: https://jquery.com
    * LICENSE: https://github.com/jquery/jquery/blob/main/LICENSE.txt

* Underscore JS
    * version: 1.6.0
    * URL: http://underscorejs.org
    * LICENSE: https://github.com/jashkenas/underscore/blob/master/LICENSE

* JQuery-ui
    * version: 1.12.1
    * URL: https://jqueryui.com
    * LICENSE:  https://github.com/jquery/jquery-ui/blob/main/LICENSE.txt

## CONFIGURATION

### Configure Index Macro
    
If the user has selected a default index  (**Note**: By default, Splunk considers the `main` index as the default index) while configuring inputs for Syslog and NetFlow data, then no need to perform this step. But if the user has given any other index, then perform the following steps:

1. Go to "Settings" > "Advanced search" > "Search macros".
2. Select "Cisco Enterprise Networking for Splunk Platform" in the "App" context dropdown.
3. Click on the `cisco_catalyst_app_index` macro from the shown table.
4. In the macro definition default value will be `()`. Update the definition with the custom index you used for data collection. For example: `index="<your_index_name>"`.

### Role-Based Access Control for Dashboards

The application implements role-based access control (RBAC) to restrict access to specific dashboards based on user roles. This ensures that step reporting dashboards are only accessible to authorized users.

#### Dashboard Access Overview

**Restricted Dashboards (Role-Based Access Required)**
* The following Step Reports dashboards require the `cisco_catalyst_step_reports` role for read access:
    * Step 1 Report Dashboard
    * Step 2 Report Dashboard
    * Step 3 Report Dashboard
    * Step 4 Report Dashboard

#### Configuring Role-Based Access

To grant users access to the Step Reports dashboards, you need to assign them the `cisco_catalyst_step_reports` role:

1. Log in to Splunk Web as an administrator.
2. Navigate to **Settings** > **Roles**.
3. Either create a new role or edit an existing role that you want to grant access to the Step Reports.
4. In the role configuration, ensure the role has the necessary capabilities to access the app.
5. The role will automatically inherit read access to the Step Reports dashboards based on the metadata configuration.

**Note**
* Ensure that the user is assigned the cisco_catalyst_step_reports role to access these dashboards.
* Users with `admin`, `sc_admin`, or `power` roles automatically have write access to all dashboards, including the Step Reports. Users with the `cisco_catalyst_step_reports` role have both read and write access to the Step Reports dashboards.

#### Troubleshooting Role-Based Access

* If users cannot see the Step Reports dashboards in the navigation menu:
    * Verify that the user has been assigned the `cisco_catalyst_step_reports` role.
    * Ensure the user has logged out and log in after role assignment.

* If users can see the dashboards but cannot access them:
    * Check that the role name matches exactly: `cisco_catalyst_step_reports`.

## MACROS

* cisco_catalyst_app_index
    * If you are using a custom index in Add-on for data collection then kindly update the "cisco_catalyst_app_index" macro in the app.
* summariesonly
    * If you want to visualize only accelerated data then change this macro to "summariesonly=true".
    * Default value of the macro is "summariesonly=false".
## DATA MODEL

* The app consists of one data model "Cisco Catalyst" for Cisco Identity Services Engine, Cisco SD-WAN, Cisco Catalyst Center and Cisco Cyber Vision data:
    * Cisco_Catalyst_App - Maps Cisco Identity Services Engine, Cisco SD-WAN, Cisco Catalyst Center and Cisco Cyber Vision data based on different log types.
* The acceleration for the data model is disabled by default.
* If you want to improve the performance of dashboards, you just need to enable the acceleration of the data model. Please follow the below steps:
    * On the Splunk menu bar, Click on "Settings > Data models"
    * Select "Cisco Enterprise Networking for Splunk Platform" in the "App" context dropdown.
    * In the "Actions" column, click on Edit and click Edit Acceleration for the "Cisco Catalyst" Data model. This will display the pop-up menu for Edit Acceleration.
    * Check or uncheck Accelerate checkbox to "Enable" or "Disable" data model acceleration respectively.
    * If acceleration is enabled, select the summary range to specify the acceleration period. The recommended acceleration period is 7 days. The acceleration period can be changed as per user convenience.
    * To save acceleration changes click on the Save button.
* **Warning**: The accelerated data models help in improving the performance of the dashboard but it increases the disk usage on the Indexer.


## REBUILDING DATA MODEL

* In case there is no need to use the already indexed accelerated Data Model, the Data Model can be configured to rebuild from scratch for the specified acceleration period. Data Model can be rebuilt by the following steps:
    * On the Splunk menu bar, Click on Settings -> Data models.
    * Select "Cisco Enterprise Networking for Splunk Platform" in the "App" context dropdown.
    * From the list of Data models, expand the row by clicking the ">" arrow in the first column of the row for the "Cisco Catalyst" data model. This will display extra Data Model information in the "Acceleration" section.
    * From the "Acceleration" section click on the "Rebuild" link.
    * Monitor the status of "Rebuild" in the field "Status" of the "Acceleration" section. Reload the page to get the latest rebuild status.

## SAVEDSEARCHES
This application contains the following saved searches

* "cisco_catalyst_sdwan_netflow" - Update the lookup cisco_catalyst_sdwan_application_tag from configured index that maps the app with app_tag for Netflow data.
* "cisco_catalyst_location" - Update the lookup cisco_catalyst_ise_location from configured index that appends authentication and device locations for ISE.
* "cisco_catalyst_sdwan_policy" - Update the lookup cisco_catalyst_sdwan_policy_mapping from configured index that maps policy with policy_rule for Netflow data.
* "cisco_catalyst_meraki_organization_mapping" - Update the lookup meraki_org_id_name_lookup from configured index that maps organization id with organization name for Meraki Events.
* "cisco_catalyst_meraki_devices_serial_mapping" - Update the lookup cisco_catalyst_meraki_device_serial_mapping from configured index that maps Meraki Serial with Meraki Devices for Meraki Events.
* "cisco_catalyst_all_macAddresses" - Gets all MAC Addresses from both ISE and Tenable Logs as starting point for MER.
* "cisco_catalyst_ise_passed_authn_v3" - ISE Passed Authentications.
* "cisco_catalyst_ise_hardware_report_v1" - Cisco ISE Analytics Hardware Inventory Report.
* "cisco_catalyst_ise_accounting_v2" - ISE Accounting Updates.
* "cisco_catalyst_ise_posture_report_v2" - ISE Posture Reports.
* "cisco_catalyst_profiler_summary_v4" - ISE Profiler Summary from ISE Analytics Reports.
* "cisco_catalyst_windows_os_details_v2" - OS details pulled from Tenable for Windows systems.
* "cisco_catalyst_windows_disk_details_v2" - Disk details pulled from Tenable for Windows systems.
* "cisco_catalyst_windows_hardware_details_v2" - Hardware details pulled from Tenable for Windows systems.
* "cisco_catalyst_windows_interface_details_v2" - Interface details pulled from Tenable for Windows systems.
* "cisco_catalyst_windows_memory_details_v2" - Memory details pulled from Tenable for Windows systems.
* "cisco_catalyst_windows_processors_details_v2" - Processor details pulled from Tenable for Windows systems.
* "cisco_catalyst_tpm_details_v2" - TPM details pulled from Tenable for Windows systems.
* "cisco_catalyst_other_os_details_v2" - OS details pulled from Tenable for non-Windows systems.
* "cisco_catalyst_other_arch_details_v2" - Architecture details pulled from Tenable for non-Windows systems.
* "cisco_catalyst_other_disk_details_v2" - Disk details pulled from Tenable for non-Windows systems.
* "cisco_catalyst_other_hardware_details_v2" - Hardware details pulled from Tenable for non-Windows systems.
* "cisco_catalyst_other_interface_details_v2" - Interface details pulled from Tenable for non-Windows systems.
* "cisco_catalyst_other_memory_details_v2" - Memory details pulled from Tenable for non-Windows systems.
* "cisco_catalyst_other_processor_details_v2" - Processor details pulled from Tenable for non-Windows systems.
* "cisco_catalyst_coams_by_device" - Reports COAMS attributes by device.
* "cisco_catalyst_step_4_report_all" - Consolidated Step 4 report combining connections, access levels, ICAM attributes, and authentication details.
* "cisco_catalyst_step_4_connections" - Reports wired, wireless, and VPN connections by device.
* "cisco_catalyst_step_4_access_levels" - Reports access levels (full access, remediation, unknown) by device.
* "cisco_catalyst_step_4_icam_attributes" - Reports ICAM user and device certificate attributes.
* "cisco_catalyst_step_4_authentication_details" - Reports authentication details including EAP types and 802.1X status.
* "cisco_catalyst_step_3_remediation_attempt_records" - Reports ISE posture remediation attempt records.
* "cisco_catalyst_reports_lookup" - Master analytics report that consolidates all device information and outputs to cisco_catalyst_analytics_reports.csv.
* "cisco_catalyst_010_reporting_uscybercom_device_category_step_1" - Report Count by CYBERCOM Categories.
* "cisco_catalyst_011_reporting_operating_system_summary_step_1" - Report Count by Operating System.
* "cisco_catalyst_0200_reporting_total_discovered_endpoints_step_2" - Reports total discovered endpoints.
* "cisco_catalyst_0201_reporting_total_manageable_endpoints_step_2" - Reports total manageable endpoints.
* "cisco_catalyst_0202_reporting_total_managed_endpoints_step_2" - Reports total managed endpoints.
* "cisco_catalyst_0203_reporting_total_non_managed_endpoints_step_2" - Reports total non-managed endpoints.
* "cisco_catalyst_0204_reporting_total_8021X_endpoints_step_2" - Reports total 802.1X endpoints.
* "cisco_catalyst_0205_reporting_total_mab_endpoints_step_2" - Reports total MAB endpoints.
* "cisco_catalyst_0208_reporting_total_authenticated_other_step_2" - Reports total authenticated other endpoints.
* "cisco_catalyst_0209_reporting_non_svr_wkstn_managed_devices_step_2" - Reports non-server/workstation managed devices.
* "cisco_catalyst_0210_reporting_non_svr_wkstn_non_managed_devices_step_2" - Reports non-server/workstation non-managed devices.
* "cisco_catalyst_0211_13_reporting_svr_wkstn_managed_and_non_managed_devices_step_2" - Reports server/workstation managed and non-managed devices.
* "cisco_catalyst_0206_7_14_24_reporting_step_2" - Reports profiled/unprofiled endpoints and posture compliance metrics.
* "cisco_catalyst_report_all_step_2" - Consolidated  Step 2 report with all metrics.

## LOOKUPS
* `cisco_catalyst_sdwan_application_tag`: This lookup contains the mapping between the app and app_tag for Netflow data.
* `cisco_catalyst_location`: This lookup contains the location of authentication and device for ISE.
* `cisco_catalyst_sdwan_policy_mapping`: This lookup contains the mapping between the policy and policy_rule for Netflow data.
* `ta_cisco_catalyst_security_group_tag_mapping`: This lookup contains the mapping between ise_host,ise_server,security_group_name and security_group_tag
* `meraki_org_id_name_lookup`: The lookup contains the mapping of meraki organization name and organization id.
* `cisco_catalyst_meraki_device_serial_mapping`: The lookup contains the mapping of meraki devices and Serial.
* `cisco_catalyst_analytics_reports`: This lookup contains comprehensive master endpoint record (MER) data that consolidates device information from multiple sources including ISE, Tenable, and other data sources. It includes MAC addresses, hardware details, OS information, authentication details, COAMS attributes, Step 4 reports, and other endpoint analytics.
* `cisco_catalyst_ise_location_mapping`: This lookup contains the mapping of ISE Network Device Group (NDG) locations to geographic coordinates (latitude and longitude) for geolocation visualization in dashboards.
**Note**:- Add latitude and longitude with respect to Location in cisco_catalyst_ise_location_mapping.csv file

## TROUBLESHOOTING

* If dashboards are not getting populated or found data discrepancy between the panel search result and drilldown search result:
    * Check whether you have correctly configured the index in the `cisco_catalyst_app_index` macro. 
    * Also you can verify if the data is there in the index by running the search query: 
        * `index="<your_index_name>"`
    * Try expanding Time Range.

* If for Users And Applications Dashboard, "Application Usage" Panel is not getting populated run the savedsearch as per the given steps:
    * Go to Settings -> Searches, reports, and alerts
    * Select "Cisco Enterprise Networking for Splunk Platform" in the "App" context dropdown and "All" in the "Owner" dropdown.
    * Run the "cisco_catalyst_sdwan_netflow" savedsearch with "All time" time range.  

* If for Overview Dashboard, "Top Policy Hits for SD-WAN" or in Security Insights Dashboard, "Dropped FW Flows" or "Inspected FW Flows" Panels are not getting populated run the savedsearch as per the given steps:
    * Go to Settings -> Searches, reports, and alerts
    * Select "Cisco Enterprise Networking for Splunk Platform" in the "App" context dropdown and "All" in the "Owner" dropdown.
    * Run the "cisco_catalyst_sdwan_policy" savedsearch with "All time" time range.

* If for Device Dashboard, "Unknown Endpoints Details" or in Users And Applications Dashboard, "Guest Authentication Details" or "Authentication Details" Panels are not getting populated run the savedsearch as per the given steps:
    * Go to Settings -> Searches, reports, and alerts
    * Select "Cisco Enterprise Networking for Splunk Platform" in the "App" context dropdown and "All" in the "Owner" dropdown.
    * Run the "cisco_catalyst_sdwan_policy" savedsearch with "All time" time range.

* "Search is waiting for input" or "Waiting for data" or “waiting for queued job to start“ These messages typically indicate delays in the backend search processing, often due to large datasets, inefficient searches, or unaccelerated data models. It’s recommended to accelerate the data model for faster results retrieval and efficiently search the data for huge datasets.

    * On the Splunk menu bar, Click on Settings -> Data models.
    * Select "Cisco Enterprise Networking for Splunk Platform" in the "App" context dropdown.
    * From the list of Data models, expand the row by clicking the ">" arrow in the first column of the row for the "Cisco Catalyst" data model. This will display extra Data Model information in the "Acceleration" section.
    * From the "Acceleration" section click on the "Accelerate" Checkbox and click Save.


## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/cisco-catalyst-app
* To reflect the cleanup changes in UI, Restart the Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Email: ciscosdwan-splunk-support@external.cisco.com
  
### Copyright (c) 2026 Cisco Systems, Inc. All rights reserved.
