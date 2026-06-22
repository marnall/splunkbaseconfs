# Censys for Splunk Platform

## OVERVIEW
* The Censys for Splunk Platform integrates with the Censys platform to provide enrichment capabilities for hosts, web properties, and certificates. It enables security teams to enhance their threat detection and response workflows with Censys's comprehensive internet intelligence data.

## COMPATIBILITY MATRIX
* Splunk version: 10.2.x, 10.0.x, 9.4.x and 9.3.x
* Python version: Python3
* OS Support: Independent
* Browser Support: Independent

## RELEASE NOTES

### Version 1.0.0
* Initial release of Censys for Splunk Platform
* Added data enrichment capabilities for hosts, web properties, and certificates
* Implemented adaptive responses for Splunk Enterprise Security integration
* Implemented saved searches for Splunk Enterprise Security integration
* Added workflow actions, custom commands for alert enrichment, rescanning, and history retrieval
* Included SOC dashboard for visualizing enriched data

## INSTALLATION
Censys for Splunk Platform can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/folder.

1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install app from file`.
3. Click `Choose file` and select the `Censys for Splunk Platform` installation file.
4. Click on `Upload`.
5. Restart Splunk if prompted.

## CONFIGURATION

### App Setup
1. Configure the account from which the data needs to be collected. Detailed steps and information for Account Configuration can be found in `Account` section.
2. Users can also configure settings corresponding to the `Proxy`, `Logging` or `Splunk ES Finding Enrichment` in their respective sections.
3. After the configuration of `Account`, `Proxy`, `Logging` and `Splunk ES Finding Enrichment`, users can utilize the app's enrichment capabilities.

### Account
To configure the Account:

1. Navigate to the `Configuration`.
2. Provide your Censys API ID, API Secret, and Account Name and click on `Add`.

| Censys Account parameters | Mandatory or Optional | Description                                 |
| ------------------------- | --------------------- | ------------------------------------------- |
| Name                      | Mandatory             | Enter a unique name for this account.       |
| Organization ID           | Mandatory             | Enter the Organization ID for this account. |
| API Key                   | Mandatory             | Enter the API Key for this account.         |

### Proxy
To configure the Proxy:

1. Navigate to the `Configuration`.
2. Click on the `Proxy` tab. 
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters    | Mandatory or Optional | Description                                                       |
| ------------------- | --------------------- | ----------------------------------------------------------------- |
| Enable              | Optional              | To enable the proxy                                               |
| Host                | Optional              | Host or IP of the proxy server                                    |
| Port                | Optional              | Port for proxy server                                             |
| Username            | Optional              | Username of the proxy server                                      |
| Password            | Optional              | Password of the proxy server                                      |

### Logging
To configure the Logging:

1. Navigate to the `Configuration`.
2. Click on the `Logging` tab.
3. Select the log level from the dropdown and click on `Save`. By default the log level is set to 'INFO'.

### Splunk ES Finding Enrichment
The Censys for Splunk Platform integrates with Splunk Enterprise Security to provide automatic enrichment for notable events. By default, enrichment is applied to all findings.

1. Navigate to the `Configuration`.
2. Click on the `Splunk ES Finding Enrichment` tab.
3. Enable and provide the account name.
4. Select the frequency of the enrichment and click on `Save`.
5. If required, update the saved searches in the app to automatically enrich notable events with Censys data.
6. This will enable the `censys_notable_index_host_enrichment`, `censys_notable_index_web_property_enrichment` and `censys_notable_index_certificate_enrichment` saved searches.

## SAVED SEARCHES
This application contains the following saved searches:

* **censys_notable_index_host_enrichment**: Periodically enriches hosts from notables with Censys API every 30 minutes.
* **censys_notable_index_web_property_enrichment**: Periodically enriches web properties from notables with Censys API every 30 minutes.
* **censys_notable_index_certificate_enrichment**: Periodically enriches certificate from notables with Censys API every 30 minutes.
* **censys_purge_host_enrichment_lookup**: Periodically removes entries older than 30 days from censys_host_enrichment_lookup.
* **censys_purge_web_property_enrichment_lookup**: Periodically removes entries older than 30 days from censys_web_property_enrichment_lookup.
* **censys_purge_certificate_enrichment_lookup**: Periodically removes entries older than 30 days from censys_certificate_enrichment_lookup.
* **censys_purge_host_event_history_lookup**: Periodically removes entries older than 30 days from censys_host_event_history_lookup.

**NOTE**: If User wants to update or enable/disable Saved Searches:
1. Click on Settings > Searches, reports, and alerts
2. Then select App as 'Censys for Splunk Platform' and type the name in the filter section to find the saved search.
3. Click on the Edit button, it will display the enable/disable button.
4. All saved searches are disabled by default.

## MACROS
* **censys_splunk_account_name**:
    * This macro is used in all the saved searches. Default value is param.global_account=acc_name.
    * User can update the macro from `Splunk ES Finding Enrichment` tab.
    * User can update the macro manually by following these steps:
        * On Splunk's menu bar, Click on Settings -> "Advanced search" -> "Search Macros".
        * Search "censys_splunk_account_name" macro
        * Click on the "censys_splunk_account_name" macro and specify the account name. Please see the sample below.
            * param.global_account="your_account_name"
        * Click on the Save Button.

## ALERT ACTIONS
This application contains the following alert actions:

* **censys_proactive_alert_enrichment_triage**
    * Description: Retrieve information about a host, web property or certificate.
    * Parameters:
        * global_account: Censys account to use for the enrichment.
        * indicator_type: Type of indicator (host, web_property, certificate).
        * indicator_field: Field containing the indicator value.
        * indicator_port_field: Field containing the port for web property enrichment.

* **censys_reactive_alert_enrichment_triage_es**
    * Description: Splunk ES integration for retrieving information about a host, web property or certificate.
    * Parameters:
        * global_account: Censys account to use for the enrichment.
        * field_name: Field containing the indicator value.
        * indicator_type: Type of indicator (host, web_property, certificate).
        * indicator_port_field: Field containing the port for web property enrichment.
        * scan_type: Type of scan (manual or automatic).

* **censys_reactive_alert_enrichment_ir_rescan_es**
    * Description: Splunk ES integration for initiating a rescan for a known host service.
    * Parameters:
        * global_account: Censys account to use for the rescan.
        * indicator_type: Type of indicator.
        * service_ip_field: Field containing the service IP.
        * service_port_field: Field containing the service port.
        * service_protocol_field: Field containing the service protocol.
        * service_transport_protocol_field: Field containing the service transport protocol.
        * web_origin_hostname_field: Field containing the web origin hostname.
        * web_origin_port_field: Field containing the web origin port.

* **censys_reactive_alert_enrichment_ir_history_es**
    * Description: Splunk ES integration for retrieving event history for a host.
    * Parameters:
        * global_account: Censys account to use for the history retrieval.
        * host_ip_field: Field containing the host IP.
        * start_time: Start time for the history retrieval.
        * end_time: End time for the history retrieval.

## ADAPTIVE RESPONSE
The Censys for Splunk Platform integrates with Splunk Enterprise Security's Adaptive Response framework to provide the following actions:

* **Censys Enrichment**: Enrich notable events with Censys data about hosts, web properties, or certificates.
* **Censys Rescan**: Initiate a rescan of a host or web property to get the latest information.
* **Censys Host History**: Retrieve historical information about a host.

## CUSTOM COMMANDS
This application contains the following custom commands:

* **censysalertenrichmenttriage**
    * Description: This command retrieves enrichment data for hosts, web properties, or certificates.
    * Parameters:
        * account_name: The configured Censys account name.
        * indicator_type: Type of indicator (host, web_property, certificate).
        * indicator_value: Value of the indicator to enrich.
        * indicator_port: Port for web property enrichment (optional).
        * at_time: Time to retrieve the enrichment data for (optional).

* **censysalertenrichmentrescan**
    * Description: This command initiates a rescan for a known host service.
    * Parameters:
        * account_name: The configured Censys account name.
        * indicator_type: Type of indicator.
        * service_ip: IP of the service to rescan.
        * service_port: Port of the service to rescan.
        * service_protocol: Protocol of the service to rescan.
        * service_transport_protocol: Transport protocol of the service to rescan.
        * web_origin_hostname: Hostname of the web origin to rescan.
        * web_origin_port: Port of the web origin to rescan.

* **censysalertenrichmenthistory**
    * Description: This command retrieves event history for a host.
    * Parameters:
        * account_name: The configured Censys account name.
        * host_ip: IP of the host to retrieve history for.
        * start_time: Start time for the history retrieval.
        * end_time: End time for the history retrieval.

## LOOKUPS
* `censys_host_enrichment_lookup`: This lookup contains enrichment data for hosts.
* `censys_web_property_enrichment_lookup`: This lookup contains enrichment data for web properties.
* `censys_certificate_enrichment_lookup`: This lookup contains enrichment data for certificates.
* `censys_host_event_history_lookup`: This lookup contains event history for hosts.

User can check data in lookup by running following SPL query in Splunk search: `| inputlookup <NAME OF LOOKUP>`

## DASHBOARDS
The Censys for Splunk Platform includes the following dashboards:

1. **Censys SOC Dashboard**:

    * Overview of enriched hosts, web properties, and certificates
    * Statistics on manual and automatic enrichments
    * Ability to filter and view detailed information about enriched entities
    * Option to get the latest information for specific entities

2. **Censys Enrichment**:

    * View enrichment data for hosts, web properties, and certificates
    * Analyze enrichment results
    * Visualize enrichment data for better understanding

3. **Censys Rescan**:

    * Initiate rescans for hosts and web properties
    * View rescan results
    * Visualize enrichment data for better understanding

4. **Censys Host History**:

    * View historical data for hosts
    * Analyze changes over time
    * Identify potential security issues

## TROUBLESHOOTING

### General Checks
* To troubleshoot Censys for Splunk Platform, check `$SPLUNK_HOME/var/log/Splunk/censys_*.log` or user can search `index="_internal" source=*censys_*.log*` query to see all the logs in UI. Also, user can use `index="_internal" source=*censys_*.log* ERROR` query to see ERROR logs in the Splunk UI.
* Note that all log files of this App will be generated in `$SPLUNK_HOME/var/log/Splunk/` directory.
* App icons are not showing up: The App does not require restart after the installation in order for all functionalities to work. However, the icons will be visible after one Splunk restart post installation.

### Data Enrichment
* If data enrichment is not working, ensure that:
    * The Censys account is properly configured with valid API credentials
    * The internet is active (On a proxy machine, if proxy is enabled)
* Check `censys_*.log*` files for any relevant error messages

### Custom Commands
* If custom commands are not working, ensure that:
    * The user has sufficient permissions to run the commands
    * The Censys account is properly configured
    * The parameters are correctly specified
* Check the specific log files for each custom command for further analysis

### Dashboards
* Panel not populating:
    * Ensure that the Censys account is properly configured
    * Check that the lookups contain data
    * Check the log files for any errors

## UNINSTALL & CLEANUP STEPS
* Remove $SPLUNK_HOME/etc/apps/censys-splunk-platform
* Remove $SPLUNK_HOME/var/log/Splunk/censys_*.log*
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## SUPPORT
* Support Details:
    * Email: support@censys.com

## COPYRIGHT
#### Copyright © 2026 Censys