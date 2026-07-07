# Cisco Catalyst Add-on for Splunk


## OVERVIEW
Cisco Catalyst Add-on for Splunk collects data for different Cisco Products - **Cisco Identity Services Engine**, **Cisco SD-WAN**, **Cisco Catalyst Center**, and **Cisco Cyber Vision**. The add-on parses the data from these sources and stores them into the Splunk indexes.

* Author - Cisco Systems
* Version - 3.1.0
* Build - 1
* Prerequisites - This application is dependent on **Splunk Add-on for Stream Forwarders**, **Splunk App for Stream** and **Cisco Catalyst Enhanced Netflow Add-on for Splunk** to collect Netflow Data.


## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox & Safari
* OS: Linux, macOS, Windows
* Splunk Enterprise Version: Splunk 9.3.x, Splunk 9.4.x, Splunk 10.0.x
* Supported Splunk Deployment: Standalone, Distributed & Cluster
* Splunk Add-on for Stream Forwarders (Third Party Dependency): 8.1.0 & 8.0.2
* Splunk App for Stream (Third Party Dependency): 8.1.0 & 8.0.2
* Cisco Catalyst Enhanced Netflow Add-on for Splunk (Third Party Dependency): 1.0.0


## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer, and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. **Cisco Catalyst Add-on for Splunk**, which parses collected Syslog, Modular Input and NetFlow data.
    2. **Cisco Enterprise Networking for Splunk Platform**,  which adds dashboards to visualize Syslog, Modular Input and NetFlow data.

* This app can be set up in two ways:
    
**1) Standalone Mode**

* Install the "Cisco Enterprise Networking for Splunk Platform" and "Cisco Catalyst Add-on for Splunk" on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
* The "Cisco Enterprise Networking for Splunk Platform" uses the data parsed by the "Cisco Catalyst Add-on for Splunk" and builds dashboards on it.
  
**2) Distributed Environment**

* Install the "Cisco Enterprise Networking for Splunk Platform" and "Cisco Catalyst Add-on for Splunk" on the search head.
* Install only "Cisco Catalyst Add-on for Splunk" on the heavy forwarder. 
* User needs to manually create an index on the Indexer (No need to install "Cisco Enterprise Networking for Splunk Platform" on Indexer).
* Note: Installation of "Cisco Catalyst Add-on for Splunk" on Indexer is required in case of universal forwarder.


## INSTALLATION
 "Cisco Catalyst Add-On For Splunk" can be installed through : unique name to describe as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/ directory.
 
1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install the app from file`.
3. Click `Choose file` and select the `TA_cisco_catalyst` installation file.
4. Click on `Upload`.
5. Restart Splunk 


## UPGRADE

### General upgrade steps:
* Log in to Splunk Web and navigate to Cisco Catalyst Add-on for Splunk -> Inputs.
* Here disable all configured Inputs.
* Navigate to Apps -> Manage Apps on Splunk menu bar.
* Click Install app from file.
* Click Choose file and select the Cisco Catalyst Add-on for Splunk installation file.
* Check the Upgrade checkbox.
* Click on Upload.
* Restart Splunk.

### Upgrade to v3.1.0 
* Follow the General upgrade steps section.

### Upgrade to v3.0.0
* **NOTE:** 
    - If upgrading from any version onward v2.0.0, you can directly upgrade to this version.
    - If upgrading from any version prior to v2.0.0, you must first follow the upgrade notes in the v2.0.0 section below before proceeding with this upgrade.
* Follow the General upgrade steps section

### Upgrade to v2.1.0
* **NOTE:** 
    - If upgrading from v2.0.0, you can directly upgrade to this version.
    - If upgrading from any version prior to v2.0.0, you must first follow the upgrade notes in the v2.0.0 section below before proceeding with this upgrade.
* Follow the General upgrade steps section.

### Upgrade to v2.0.0
* **NOTE:** 
    - Upgrade is not supported for DNA center as `hostname` field is moved from Inputs to Configuration.
    - For DNA Center, edit the previous account and inputs and reconfigure them with the required details once upgraded.
* Follow the General upgrade steps section.

### Upgrade to v1.1.2
* Follow the General upgrade steps section.

### Upgrade to v1.1.1
* Follow the General upgrade steps section.


## Application Setup

### Configure Inputs on Splunk for Modular Inputs Data
To add Data Inputs follow the steps below:
* From the Splunk Home Page, click on `Cisco Catalyst Add-on for Splunk`.

#### For Catalyst Center
1. Go to `Configure Application` in Catalyst Center tile.
2. Configure a Cisco Catalyst Center User Account from `Configuration` tab.
    - Account Name: Unique name to describe the user account.
    - Cisco Catalyst Center Host: Host of the Cisco Catalyst Center in format https://<host>.
    - Username: Username of this Cisco Catalyst Center account.
    - Password: Password of this Cisco Catalyst Center account.
    - Use Custom CA Certificate: Enable or disable use of Custom CA Certification for this account.
    - Custom CA Certificate: Custom CA Certificate for this account.
3. Configure Data Inputs:
    - Input Type: Type of data that needs to be collected.
    - Name: Unique name to describe the data input.
    - Interval: Time interval to request the data from Cisco Catalyst Center.
    - Index: Splunk index.
    - Cisco Catalyst Center Account: Account configured in Step 2.
    - Logging Level: Logging level for messages written to input logs in $SPLUNK_HOME/var/log/splunk/TA_cisco_catalyst/
    - For Reports Input -> Device Inventory Report Name: Collect events for Inventory Report.
        - **Note**: 
            - Only CSV format is supported for compliance and inventory Reports type.
            - Device Name, IP Address, and Device Type fields are used to parse headers for Compliance and Inventory Reports input.
    - For Reports Input -> Device Compliance Report Name: Collect events for Compliance Report.
4. Repeat step 2 or 3 for every combination of user account and data inputs as needed.

#### For Cyber Vision
1. Go to `Configure Application` in Cyber Vision tile.
2. Configure a Cisco Cyber Vision Account from `Configuration` tab.
    - Account Name: Unique name to describe the user account.
    - IP Address/Domain: IP Address of the Cisco Cyber Vision portal (Use https).
    - API Token: API Token generated from Cyber Vision for the above account.
    - Use Custom CA Certificate: Enable or disable use of Custom CA Certification for this account.
    - Custom CA Certificate: Custom CA Certificate for this account.
    - Enable Proxy: Enable or disable use of Proxy for this account.
    - Proxy Type: Proxy protocol.
    - Proxy URL: Server Address of Proxy Host.
    - Proxy Port: Port of the proxy server.
    - Proxy Username: Username of the proxy server if it exists.
    - Proxy Password: Password of the proxy server if it exists.
3. Configure Data Inputs:
    - Input Type: Type of data that needs to be collected.
    - Name: Unique name to describe the data input.
    - Interval: Time interval to request the data from Cisco Cyber Vision.
    - Index: Splunk index.
    - Cyber Vision Account: Cisco Cyber Vision user account.
    - Start Date: Start Time and Date from where data needs to be collected (format: YYYY-MM-DDTHH:MM:SSZ).
    - Logging Level: Logging level for messages written to input logs in $SPLUNK_HOME/var/log/splunk/TA_cisco_catalyst/
4. Configure Syslog Input:
    - Input Type: Type of Protocol to use for data collection (TCP or UDP).
    - Port: Port for this input.
    - Only accept connection from: example: 10.1.2.3, !badhost.splunk.com, *.splunk.com (If not set, accepts connections from all hosts).
    - Input Source Type: Source type for your input.
    - Index: Splunk index.
5. Repeat step 2, 3 or 4 for every combination of user account, start date and data inputs as needed.

#### For SDWAN
1. Go to `Configure Application` in SDWAN tile.
2. Configure a SDWAN Account from `Configuration` tab.
    - Account Name: Unique name to describe the user account.
    - IP Address/Hostname: IP Address of the Cisco SDWAN portal (Use https).
    - Username: Username of this Cisco SDWAN account.
    - Password: Password of this Cisco SDWAN account.
    - Use Custom CA Certificate: Enable or disable use of Custom CA Certification for this account.
    - Custom CA Certificate: Custom CA Certificate for this account.
    - Enable Proxy: Enable or disable use of Proxy for this account.
    - Proxy Type: Proxy protocol.
    - Proxy URL: Server Address of Proxy Host.
    - Proxy Port: Port of the proxy server.
    - Proxy Username: Username of the proxy server if it exists.
    - Proxy Password: Password of the proxy server if it exists.
3. Configure Data Inputs:
    - Input Type: Type of data that needs to be collected.
    - Name: Unique name to describe the data input.
    - Interval: Time interval to request the data from Cisco SDWAN.
    - Index: Splunk index.
    - Cisco SDWAN Account: Cisco SDWAN user account.
    - Logging Level: Logging level for messages written to input logs in $SPLUNK_HOME/var/log/splunk/TA_cisco_catalyst/
    - Health Type: Select data type that needs to be collected.
4. Configure Syslog Input:
    - Input Type: Type of Protocol to use for data collection (TCP or UDP).
    - Port: Port for this input.
    - Only accept connection from: example: 10.1.2.3, !badhost.splunk.com, *.splunk.com (If not set, accepts connections from all hosts).
    - Input Source Type: Source type for your input.
    - Index: Splunk index.
5. Repeat step 2, 3 or 4 for every combination of user account and data inputs as needed.

#### For Identity Services Engine (ISE)
1. Go to `Configure Application` in Identity Services Engine (ISE) tile.
2. Configure a Identity Services Engine (ISE) Account from `Configuration` tab.
    - Account Type: Select the account type (Administrative or Analytics Reports).
    
    **For Administrative Account Type:**
    - Account Name: Unique name to describe the user account.
    - IP Address/Hostname: IP Address of the Cisco ISE portal (Use https).
    - Username: Username of this Cisco ISE account.
    - Password: Password of this Cisco ISE account.
    - pxGrid Hostname: Hostname of the pxGrid in format https://<host-name>
    - pxGrid Client Username: pxGrid client username. This client will be created in the ISE UI upon successful account creation.
    - pxGrid Certificate-Based Authentication: Enable or disable use of pxGrid Certification for this account. 
    - Client Certificate: pxGrid Client Certificate for this account.
    - Client Secret Key: pxGrid Client Secret Key for this account.
    - Use Custom CA Certificate: Enable or disable use of Custom CA Certification for this account.
    - Custom CA Certificate: Custom CA Certificate for this account. For pxGrid certificate based authentication, append the pxGrid root cert to Custom CA Certificate.
    - Enable Proxy: Enable or disable use of Proxy for this account.
    - Proxy Type: Proxy protocol.
    - Proxy URL: Server Address of Proxy Host.
    - Proxy Port: Port of the proxy server.
    - Proxy Username: Username of the proxy server if it exists.
    - Proxy Password: Password of the proxy server if it exists.
    
    **For Analytics Reports Account Type:**
    - Account Name: Unique name to describe the user account.
    - IP Address/Hostname: IP Address of the ISE CLI.
    - Username: ISE SSH Username.
    - ISE SSH Password: Password for ISE SSH access.
    - ISE SSH Port: Port for ISE SSH connection (default: 22).
    - Repository Address: SFTP repository address.
    - Repository User: SFTP repository user.
    - Repository User Password: Password for the SFTP repository user.
    - Repository SCP/SFTP Port: Port for SCP/SFTP repository connection (default: 22).
3. Configure Data Inputs:
    - Name: Unique name to describe the data input.
    - Interval: Time interval to request the data from Cisco ISE.
    - Index: Splunk index.
    - Cisco ISE Account: Cisco ISE user account.
    - Fetch Cisco ISE Environment Data: Select the type of data that needs to be collected
    - Logging Level: Logging level for messages written to input logs in $SPLUNK_HOME/var/log/splunk/TA_cisco_catalyst/
    - For ISE Analytics Reports -> Cisco ISE Disk Repository Name: Enter the ISE disk repository name.
    - For ISE Analytics Reports -> Cisco ISE SFTP Repository Name: Enter the ISE SFTP repository name.
4. Configure the settings in the Additional Settings Tab if you want to fetch the `Security Group Tags` from Cisco ISE server. For "Security Group Tags" data will be populated in KVstore lookup instead of Splunk index. 
    - Environment Type: Environment type for storing lookups.
    - Splunk Management Port: Management Port of the Splunk Environment.
    - Below details are not needed if Environment Type is `Local Instance`
        - Splunk Management Host: Management URL of the Splunk Environment. This should be the hostname or IP address of the search head instance where the KVstore lookup should be stored.
        - Splunk Management Username: Username to access the Splunk Environment.
        - Splunk Management Password: Password to access the Splunk Environment.
5. Configure Syslog Input:
    - Input Type: Type of Protocol to use for data collection (TCP or UDP).
    - Port: Port for this input.
    - Only accept connection from: example: 10.1.2.3, !badhost.splunk.com, *.splunk.com (If not set, accepts connections from all hosts).
    - Input Source Type: Source type for your input.
    - Index: Splunk index.
6. Repeat step 2, 3, 4 or 5 for every combination of user account and data inputs as needed.

### SSL Configuration 
1. By default, the API calls from the Cisco Catalyst Add-on for Splunk would be verified by SSL. The configurations are present in $SPLUNK_HOME/etc/apps/TA_cisco_catalyst/default/ta_cisco_catalyst_settings.conf file:
    ```
    [additional_parameters]
    verify_ssl = True
    ```
2. In order to make unverified calls, change the SSL verification to False. To do that, navigate to $SPLUNK_HOME/etc/apps/TA_cisco_catalyst/local/ta_cisco_catalyst_settings.conf file and change the verify_ssl parameter value to False under additional_parameters stanza. Create a stanza if its not present already.
3. To add a custom SSL certificate to the certificate chain, use the option available in the user interface while configuring the account.
4. Restart the Splunk in order for the changes to take effect.


**Notes**

* If you have any existing TCP/UDP inputs created for the Cisco ISE, Cisco SD-WAN, Cisco Cyber Vision and Cisco Network Data Add-Ons, ensure that you disable those inputs as well and create a new TCP/UDP input as mentioned above.

### Configure Inputs on Splunk for Netflow Data

* Prerequisite to collect Netflow data into Splunk
* Install the following apps in the Splunk instance to collect and parse the NetFlow (v9) data:

    | App | Search Head | Heavy Forwarder | Indexer |
    | --- | ----------- | --------------- | ------- |
    | [Splunk App for Stream](https://splunkbase.splunk.com/app/1809/) | No | Yes | No |
    | [Splunk Add-on for Stream Forwarders](https://splunkbase.splunk.com/app/5238/) | No | Yes | No |
    | [Cisco Catalyst Enhanced Netflow Add-on for Splunk](https://splunkbase.splunk.com/app/6872) | No | Yes | No |

*  Make sure that the receiver UDP port (Ex. 4739) is open and bypass the firewall traffic.


### Configure Inputs on Splunk for Cisco IOS Devices

* Create a syslog input in SDWAN with sourcetype set to `cisco:catalyst:syslog`. A regex match will be performed to rewrite the events to the `cisco:ios` sourcetype.
* Supported Cisco Devices:
    * Any Cisco Catalyst switch or router. Specific examples below:
    * Cisco Catalyst series switches (1000, 1200, 1300, 2960, 3650, 3750, 4500, 6500, 6800, 7600, 9000 etc.)
    * Cisco ASR - Aggregation Services Routers (900, 1000, 5000, 9000 etc.)
    * Cisco ISR - Integrated Services Routers (800, 1900, 2900, 3900, 4451 etc.)
    * Cisco Nexus Data Center switches (1000V, 2000, 3000, 4000, 5000, 6000, 7000, 9000 etc.)
    * Cisco Carrier Routing System
    * Other Cisco IOS based devices (Metro Ethernet, Industrial Ethernet, Blade Switches, Connected Grid etc.)
    * Cisco Access Points
    * Cisco WLC - WLAN Controller

## Configure Cisco ISE to send logs to Splunk Enterprise for the Splunk Add-on for Cisco ISE

To enable to Splunk Enterprise to receive data from your Cisco ISE remote system logging, complete these steps:

- Create a remote logging target.
- Add the target to the appropriate logging categories.

The following sections provide detailed configuration instructions.

For more information, see the Logging section of the Cisco ISE Administrator Guide provided by Cisco.

#### Steps to follow

* Once the "Splunk App for Stream", "Splunk Add-on for Stream Forwarders" and "Cisco Catalyst Enhanced Netflow Add-on for Splunk" are installed in the desired Splunk Instance.
* Open "Splunk App for Stream" > Click on "Configuration" > Click on "Configure Streams"
* In the "Search" filter search for the keyword "netflow" and Update the "Mode" to "Disabled".
* In the "Search" filter search for the keyword "cisco_hsl_cisco_hsl_netflow".
* For "cisco_hsl_cisco_hsl_netflow" stream > Goto "Action" > "Edit"
* Update the "Mode" to "Enabled" & select the desired index, by default "main" will be selected.
* Click on Save.
* SSH into the Destination VM example VM: X.X.X.X  (should be replaced with the VM in which data is been collected) 
* Goto Location: $SPLUNK_HOME/etc/apps/Splunk_TA_stream/local
* Create a "streamfwd.conf" in the "local" folder
  * Sample format of 'streamfwd.conf' as below:
    ```
      [streamfwd]
      netflowReceiver.<N>.ip = <ip_address>
      netflowReceiver.<N>.port = <port_number>
      netflowReceiver.<N>.decoder = <flow_protocol>
    ```
  * Below is an example file for the ip x.x.x.x and port 4739:
    ```
      [streamfwd]
      netflowReceiver.0.ip = x.x.x.x
      netflowReceiver.0.port = 4739 
      netflowReceiver.0.decoder = netflow
    ```
* Save the changes.
* All the NetFlow events will get ingested in the Destination VM: X.X.X.X  (should be replaced with the VM in which data is been collected) 
* Verify the ingestion of events by using the following query from the "Destination VM: X.X.X.X"  (should be replaced with the VM in which data is been collected) 
    * index="<desired index name>" sourcetype="stream*"

Note: Refer to the [documentation](https://www.splunk.com/en_us/blog/tips-and-tricks/splunking-netflow-with-splunk-stream-part-1-getting-netflow-data-into-splunk.html#:~:text=Step%201%3A%20Setup%20new%20NetFlow%20stream%20at%20Stream%20app) for setting up a new Netflow stream.

## Create remote logging target
1. In Cisco ISE, choose **Administration** > **System** > **Logging** > **Remote Logging Targets**.
2. Click **Add**.
3. Configure the following fields:

    | Field | Value | Description |
    |----------|----------|----------|
    | Name    | Splunk   | Target name, also used below in the category|
    | IP Address | 1.1.1.2 (for example) | IP address of the Splunk Enterprise system |
    | Port   | 514 (for example)  | Port that you are using on the Splunk Enterprise system or port configured for TCP or UDP input on Splunk Connect for Syslog (SC4S) or syslog aggregator (for example, rsyslog, syslog-ng) as a network input.|
    | Target Type | UDP | Best practice. NOT the default. |
    | Maximum Length | 8192 | Events will be broken if you use a smaller value. |

4. Tune all other fields at your discretion.
5. Add the new port(s) in order to enable receiving logs into Splunk
    - Configure the Syslog Input from Identity Services Engine (ISE) tile inside the Application Setup Page.
6. Go to the **Remote Logging Targets** page and verify the creation of the new target.

### Add the new target to your desired logging categories
1. Choose **Administration** > **System** > **Logging** > **Logging Categories**.
2. Click the radio button next to the category that you want to edit, then click **Edit**.
3. Add the Splunk target that you created to the following categories. These are default log collection settings and can be tuned at your discretion:
    - AAA Audit
    - Failed Attempts
    - Passed Authentications
    - AAA Diagnostics
    - Accounting
    - RADIUS Accounting
    - Administrative and Operational Audit
    - Posture and Client Provisioning Audit
    - Posture and Client Provisioning Diagnostics
    - MDM
    - Profiler
    - System Diagnostics
    - System Statistics
4. Click **Save**.
5. Go to the **Logging Categories** page and verify the configuration changes that were made to the specific categories.

## Confirm your installation and setup

To confirm that events are showing up correctly, run the following search over the last 15 minutes:

`sourcetype=cisco:ise:syslog`

If the search returns events from your ISE server, then you have successfully configured the add-on.


### Configure Event Types on Splunk Search Head Instance

To use the CIM mapped fields, a user first needs to configure the event type to provide the index in which the data is being collected. To configure event type:

* Navigate to Settings > Event types.
* Select "Cisco Catalyst Add-on for Splunk" from the App dropdown.
* Click on "cisco_sdwan_index".
* Update "()" with "index=<your_configured_index>" in the existing definition to use your configured index.
* Click Save.


**NOTE**

* Make sure that the user enables forwarding on a configured port from the Cisco SDWAN, Cisco Identity Services Engine after performing the above steps.
* $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk


## RELEASE NOTES

### Version 3.1.0
* Migrated Analytics Report Inputs.
* Added compliance and inventory Reports input for Cisco Catalyst Center.
* Added ISE Analytics Report input for Cisco Identity Services Engine(ISE).

### Version 3.0.0
* Introduced a Resource Utilization Dashboard for improved monitoring.
* Migrated extractions of Networks TA to support the syslogs from Cisco IOS devices.
* Rebranded DNA Center to Catalyst Center.
* Upgraded UCC version to v6.0.1.

### Version 2.1.0
* Added Site Topology input for Catalyst Center.

### Version 2.0.0
* Introduced a new, user-friendly custom interface for the Application Setup of the Add-On.
* Added Client and Audit Logs inputs for Catalyst Center.
* Added support for configuring Syslog inputs directly from the Add-on UI.
* Added support for data collection for the following Cisco SD-WAN types:
    - Unified Threat Defence/Link Details
        - Unified Threat Defense Health
        - Link Health
    - Site/Tunnel Health
        - Site Health
        - Tunnel Health
        - SSE Tunnels
* Added support for data collection for the following Cisco Identity Services Engine (ISE) types:
    - Security Group Tags
    - Authz Policy Hit
    - ISE TACACS Rule Hit
    - IP-SGT Bindings

### Version 1.1.2
* Removed timestamp parameters from client-health and network-health endpoints for Cisco Catalyst Center.
* Enhanced device-health endpoint to include data for the last 15 minutes for Cisco Catalyst Center.

### Version 1.1.1
* Fixed indextime extractions for Cisco Catalyst Center.

### Version 1.1.0
* Added support for the data collection of Cisco Cyber Vision.

### Version 1.0.0
* The Add-On supports the data collection for the following products:
    - Cisco Identity Services Engine
    - Cisco SD-WAN
    - Cisco Catalyst Center
* Added support for the additional log sources for Cisco SD-WAN:
    - ACL
    - SGACL
    - Audit


## Lookups
* **cisco_ise_message_catalog_420.csv**: Maps `MESSAGE_CODE` to `MESSAGE_CLASS`, `MESSAGE_TEXT`
* **cisco_ise_service.csv**: Maps `MESSAGE_CODE` to `SERVICE`
* **cisco_ise_change_message_code_420.csv**: Maps `MESSAGE_CODE` to `change_type`, `command`, `object`, `object_attrs`, `object_category`, `result`
* **cisco_ise_message_catalog_2024.csv**: Maps `MESSAGE_CODE` to `MESSAGE_CLASS`, `MESSAGE_TEXT`, `dataset_name`, `action`, `type`
* **cisco_cybervision_asset_site_system_mappings**: Maps `host` with `asset_system` and `site_id`
* **cisco_cybervision_severity_lookup**: Maps `severity_id` with `severity`
* **ta_cisco_catalyst_security_group_tag_mapping**: Maps `ise_host` with `ise_server`, `security_group_tag` and `security_group_name`


## TROUBLESHOOTING

#### Verifying Fields Extracted for Syslog Data:
* Run `index=<your_index_name> sourcetype IN ("cisco:sdwan*", "cisco:ise:syslog")` in Splunk in verbose mode.
* Ensure `"cisco:catalyst:syslog"` is set as the sourcetype when configuring the Syslog input. 

#### Verifying Fields Extracted for Netflow Data:
* Run `index=<your_index_name> sourcetype="stream*"` in Splunk in verbose mode.

#### Troubleshooting Cisco Catalyst Center Data Collection Issues:
* Use the query `index="_internal" source=*TA_cisco_catalyst_dnac*` in the Search.
* To verify data collected for Cisco Catalyst Center, run `index=<your_index_name> sourcetype=cisco:dnac*` in Verbose mode.
* Try disabling and re-enabling the inputs.
* For detailed logs, edit the Input change Logging Level to `DEBUG`.

#### Troubleshooting Cisco Cyber Vision Data Collection Issues:
* Use the query `index="_internal" source=*TA_cisco_catalyst_cybervision*` in the search.
* To verify data collected for Cisco Cyber Vision, run `index=<your_index_name> sourcetype=cisco:cybervision*` in Verbose mode.
* Try disabling and re-enabling the inputs.
* For detailed logs, edit the Input change Logging Level to `DEBUG`.

#### Troubleshooting Cisco SDWAN Data Collection Issues:
* Use the query `index="_internal" source=*TA_cisco_catalyst_sdwan*` in the search.
* To verify data collected for Cisco SDWAN, run `index=<your_index_name> sourcetype=cisco:sdwan*` in Verbose mode.
* Try disabling and re-enabling the inputs.
* For detailed logs, edit the Input change Logging Level to `DEBUG`.

#### Troubleshooting Cisco ISE Data Collection Issues:
* Use the query `index="_internal" source=*TA_cisco_catalyst_ise*` in the search.
* To verify data collected for Cisco ISE, run `index=<your_index_name> sourcetype=cisco:ise*` in Verbose mode.
* Try disabling and re-enabling the inputs.
* For detailed logs, edit the Input change Logging Level to `DEBUG`.

#### Getting "Please enable ERS on the provided account or configure a new account with ERS enabled to use Security Group Tags or IP SGT Bindings input." error while configuring ISE input.
* Verify that ERS is enabled for the account on the Cisco ISE.

#### Getting 401 status code while configuring ISE input for IP SGT Bindings.
* Confirm whether the account still exists and is not deleted from the Cisco ISE UI.
* If the pxGrid client is disabled from the Cisco ISE UI, please enable it to resume the data collection for IP-SGT Bindings

#### Status column remains blank for an input in Application Setup page.
* If an input has been disabled for more than 7 days, the Status for that input will not be displayed.
* The Status field will remain blank if the input was created as a Syslog (TCP/UDP) type.

#### Sourcetype and Timestamp Extraction Issues
* If you are forwarding the syslog data from various products like Cisco ISE, Cisco SD-WAN and IOS devices to a single port with sourcetype value as `cisco:catalyst:syslog`, and experiencing sourcetype or timestamp extraction issues, separate the syslog data types onto different ports. 
  - Example: 
    - Use port 514 for Cisco SD-WAN data with `cisco:firewall:logs` sourcetype.
    - Use port 515 for Cisco ISE data with `cisco:ise:syslog` sourcetype.
    - Use port 516 for IOS devices data with `cisco:ios` sourcetype.

## Known Issues

- CPU and Memory Utilization charts under the Splunk Resource Utilization dashboard are not populated on Windows OS due to a Splunk platform limitation.

## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA_cisco_catalyst
* To reflect the cleanup changes in UI, Restart the Splunk Enterprise instance


## BINARY FILE DECLARATION

* md.cpython-37m-x86_64-linux-gnu.so - This file is generated from nested lib dependency.
* md__mypyc.cpython-37m-x86_64-linux-gnu.so - This file is generated from nested lib dependency.



## SUPPORT
* Support Offered: Yes
* Support Email: ciscosdwan-splunk-support@external.cisco.com
  
### Copyright (c) 2026 Cisco Systems, Inc. All rights reserved.
