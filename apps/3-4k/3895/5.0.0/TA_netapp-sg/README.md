# NetApp StorageGrid Add-on for Splunk

## Overview

The NetApp StorageGRID Add-on for Splunk is used to gather data from NetApp StorageGRID environment, do indexing on it and provide the indexed data to "NetApp StorageGRID App for Splunk" which runs searches on indexed data and build dashboards using it. The NetApp StorageGRID App for Splunk can be downloaded from [here](https://splunkbase.splunk.com/app/3898/).


## Compatibility Matrix

* Splunk version: 9.3.x, 9.2.x, and 9.1.x
* NetApp StorageGRID 11.x.
* OS Support: Linux (Centos, Ubuntu) and Windows
* Browser Support: Chrome and Firefox
* If using a forwarder, it must be a HEAVY forwarder (we use the HEAVY forwarder because the universal forwarder does not include python).
* The forwarder system must have network access (HTTPS) to the StorageGRID system.
* User account with appropriate privileges for collecting data from StorageGRID system.

## Recommended System configuration

* Splunk forwarder system should have 4 GB of RAM and a quad-core CPU to run this app smoothly.

## Topology and Setting up Splunk Environment

1. Install NetApp StorageGRID Add-on for Splunk, which runs collector scripts and gathers data from StorageGRID, does indexing and parsing on collected data.

* This Add-on is supported on all the tiers of distributed Splunk platform deployment and also on standalone Splunk instance. Below table provides the reference for installing the Add-on on distributed Splunk deployment:

    | Splunk instance type  | Supported  | Required | Comments |
    | --------------------- | ---------- | --------- | -------- |
    | Search Heads          | Yes | Yes | This Add-on is required on Search Heads as it contains search time extractions. This Add-on also contains alert actions. To use these actions user need to configure the Add-on on Search Head.|
    |Indexers               | Yes | No | All parsing will be done on heavy forwarder only.|
    | Heavy Forwarders      | Yes | Yes | This Add-on supports only heavy forwarder for data collection.| 


## Installation

Follow the link mentioned below to install the App based on your deployment:

* [Single-instance Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Singleserverinstall)
* [Distributed Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Distributedinstall)
* [Splunk Cloud](https://docs.splunk.com/Documentation/AddOns/latest/Overview/SplunkCloudinstall)

## Upgrade the Add-on

If there is already older version of Add-on in your Splunk instance and then you can upgrade add-on by following two ways:

* Note: Disable all the inputs from the Inputs page of NetApp StorageGRID Add-on for Splunk.

1. Using the latest version available on Splunkbase.
     * From the Splunk Web home screen, click the gear icon next to Apps. 
     * There will be option to update the Add-on to the latest version in column name as - "Version".
     * Click on "Update to [version]"
     * Follow the installation steps to update the Add-on.

2. You can download latest version of Add-on from Splunkbase and you can upload it into Splunk by navigating to 
     * From the Splunk Web home screen, click the gear icon next to Apps. 
     * Click on, Install app from file -> Choose File 
     * Choose the location of Add-on's build downloaded and make sure you have checked checkbox of "Upgrade app."
     * And then click on Upload
     * Restart the Splunk


## Upgrading to v5.0.0 from versions < 5.0.0

* Disable and Delete the existing Inputs and Delete Accounts
* to Upgrade the Add-on follow steps of "Upgrade the Add-on"
* After upgrading to v5.0.0, Reconfigure Accounts and Inputs


## Configuration of Add-on

### 1) Configuring REST API
 
* User can configure the Add-on by following below mentioned steps.
    1. Navigate to NetApp StorageGRID Add-on for Splunk -> Configuration -> Add-on Settings.
    2. Fill the appropriate details in the dialog-box. Refer the table below to fill in the details
    
        | Input Name | Required | Description |
        | ---------- | -------- | ----------- |
        | Authentication Method | Yes | Authentication Method of Account |
        | IP/URL | Yes | IP or URL of StorageGrid|
        | Username | Yes | The Username for Account|
        | Password | Yes | The Password for Account |
        | Confirm Password  | Yes | Re-enter the same Password |

    3. This configuration will be saved in conf file for data collection. Now to start data collection user will have to create an input and keep that input as enabled.
    4. To create an input navigate to NetApp StorageGRID Add-on for Splunk -> Inputs -> Create New Input.
    5. Fill the appropriate details in the dialog-box. Refer the table below to fill in the details

        | Input Name | Required | Description |
        | ---------- | -------- | ----------- |
        | Name | Yes | Unique name to identify input |
        | Interval | Yes | Time after that interval of time input will be executed (Integer - Keep the time interval between 60 to 86400 seconds) |
        | Index | Yes | Select an Index from the dropdown (defaults to main index). |
        | Source Name  | No | Unique name to identify source from different inputs defaults it will be storagegrid_api_input |
        
    6. Splunk REST API will encrypt the password and store it in Add-on's folder itself in encrypted form, REST modular script will fetch these credentials through REST API to connect to the StorageGRID.
* Note:- User with splunk admin role can configure and access the app-on configuration. If user is not able to view the add-on configuration page then please provide the admin role to the user from Settings -> Access controls -> Users -> Select a User -> Provide admin role -> Save.

#### Configuring the REST API over secure network connection

Please note that This Add-on supports HTTPS connection and SSL check for communication between Splunk and Netapp StorageGrid out of the box. If the StorageGrid has a self-signed certificate, then to collect data through a secure network channel (with certificate checks), you first need to get the required certs for the successful SSL verification with your StorageGrid. You need to copy the content of the PEM file into: $SPLUNK_HOME/etc/apps/TA_netapp-sg/bin/ta_netapp_sg/certifi/cacert.pem. Once the certificate is copied to the mentioned location, you need to configure the StorageGrid from the UI as mentioned above in the Configuring REST API section.

#### Configuring the REST API over insecure network connection

If you want to configure the StorageGrid and collect the data through unencrypted communication (without certificate checks) you must disable the SSL check flag in ta_netapp_sg_settings.conf from local directory.

Follow these steps to disable the SSL check flag:

 1. Create local folder if it is not present under TA_netapp-sg folder.
 2. Create/Update the ta_netapp_sg_settings.conf and add cert_verify parameter under additional_parameters stanza to set the data collection over HTTP without using certificate checks.

        [additional_parameters]
        cert_verify = 0

 3. Restart the Splunk.
 4. Configure the StorageGrid from the UI as mentioned above in the Configuring REST API section.

### 2) Configuring StorageGRID AuditLogs**
   
    **2.1) On the StorageGRID System:**

    Configure the Audit Client for NFS  (Source: StorageGRID Administrator Guide(Pg. 185) https://library.netapp.com/ecm/ecm_download_file/ECMLP2753104).

    1.  Start the NFS configuration utility.
            Enter: config_nfs.rb 


    2.  Add the audit client(To be done for the first time only): 
        a) Enter: add-audit-share. 
		   (If you get 'Cannot add share, an audit share already exists.' message then move to step 3. from here.)
        b) When prompted, enter the Splunk IP Address range. IP address ranges must be expressed using a subnet mask in CIDR notation (that is, in a form such as 192.168.110.0/24). 
        c) When prompted, press <Enter>. The NFS configuration utility appears and the default audit share is added. 


    3.  If more than one Splunk Server is permitted to access the audit share, add the IP address of the server:
        a) Enter: add-ip-to-share. A numbered list of the audit shares configured on the Admin Node is displayed. The audit share is named /var/local/audit/export. 
        b)  Enter the number of the audit share. Enter: <audit_share_number> 
        c)  When prompted, enter the Splunk Server's IP address or IP Address range for the audit share. Enter: <Splunk_Server_IP> . IP address ranges must be expressed using a subnet mask in CIDR notation(that is, in a form such as 192.168.110.0/24). 
        d)  When prompted, press <Enter>. The NFS configuration utility is displayed.  
        e)  For each additional Splunk Server that should have access to the audit share, repeat the above step 3. 


    4. Optionally, verify your configuration.
        a) Enter: "validate-config"
            - The services are checked and displayed.
        b) When prompted, press <Enter>. The NFS configuration utility is displayed. 


    5. Close the NFS configuration utility. 
        Enter: exit

NFS audit Splunk Servers are granted access to an audit share based on their IP address. 
Grant access to the audit share to a new NFS Splunk Server by adding its IP address to the share, or remove an existing Splunk Server by removing its IP address. 

    **2.2) On the Splunk Server:**
    Linux:
    ------
    NFS Mount the audit share directory using the below syntax for Splunk to read from local:

        mount -t nfs -o proto=tcp,port=2049 StorageGRID_System_IP:Path_to_audit_share local_path_to_mount
        
    Eg. mount -t nfs -o proto=tcp,port=2049 <GRID_IP>:/var/local/audit/export  /usr/local/src/temp/ 

    Windows:
    -------
    1. To install 'Client Services for NFS', go to the Add/Remove Software wizard in the Control Panel.
    Click on Turn Windows features on or off.
    
    OR 
    
    => In windows server 2008 r2
    Click Start, point to Administrative Tools, and then click Server Manager.
            - In the left pane, click Roles.
            - Under Roles Summary in the right pane, click Add Roles. The Add Roles Wizard appears. Click Next.
            - Select the File Services check box to install this role on the server, and then click Next.
            - Select the Services for Network File System check box, and then click Next.
            - Confirm your selection, and then click Install.
            - When the installation completes, the installation results appear. Click Close.

    => In command line, 

        mount //StorageGrid_system_ip/audit_share_path [Drive_letter]

    Eg. mount [options] //<GRID_IP>:/var/local/audit/export H:

    => In windows server 2008 r2:

        mount \\GRID_IP\var\local\audit\export [drive letter]

### Configure StorageGRID Syslog Data:

Please follow below steps to configure TCP/UDP connection for syslog:

* Login to Splunk WEB UI.
* Navigate to Settings > Data inputs.
* Choose TCP or UDP and click New.
* In the left pane, click TCP / UDP to add an input.
* Click the TCP or UDP button to choose between a TCP or UDP input.
* In the Port field, enter a port number on which you are forwarding the logs from StorageGrid instance.
* In the Source name override field, enter a new source name to override the default source value, if necessary.
* Click Next to continue to the Input Settings page.
* Set the sourcetype as `grid:auditlog`.
* Set App context to NetApp StorageGRID Add-on for Splunk.
* Set the Index that Splunk Enterprise should send data to for this input.
* Click Review.
* Click Submit once you have ensured everything is correct.

Once the input is configured, execute the following query to see if Syslog events are being received.

    index=<configured_index> sourcetype="grid:auditlog"

### Monitor audit logs:

* To ingest audit log files directly into Splunk follow below mentioned steps:
    1. Navigate to Settings -> Data Inputs -> Files & Directories -> New Local File & Directory.
    2. Select path to the directory mounted above(eg. For linux : /usr/local/src/temp and for windows : \\<GRID_IP>\var\local\audit\export) and Select "Index once" option then click Next.
    3. Search for "grid:auditlog" from the dropdown of Source type
		* If found then select it and click Next
		* If not found, then click Save As and fill the details in the form which are given below and click on save :
            | Field Name | Field Value |
            | ---------- | -------- |
            | Name | grid:auditlog |
            | Description | To store data from audit logs |
            | Category | Custom |
            | App  | NetApp StorageGRID Add-on for Splunk |
	4. Click Next and select Index = main
	5. Click Review
	6. Submit
* Now you can start searching and monitoring data in app.

## List of Sourcetypes

The NetApp StorageGrid Add-on for Splunk provides the search knowledge objects for StorageGrid data in the following formats

| Data Source | Sourcetype | Source | CIM Models |
| ----------- | ---------- | --- | ---------- |
| Rest API    | grid:rest:api | 1. Management APIs <br> 2. Prometheus endpoints | - |
| Audit Logs | grid:auditlog | Audit logs of the Storagegrid | - |


## Uninstall the Add-on
To uninstall add-on, user can follow below steps:
* SSH to the Splunk instance
* Go to folder apps($SPLUNK_HOME/etc/apps)
* Remove the TA_netapp-sg folder from apps directory
* Restart Splunk

## Release Notes

### V5.0.0

* Added Multiple account support.
* Upgraded AOB to 4.3.0
* Upgraded splunktaucclib to 6.4.0
* Upgraded splunklib to 2.0.2

### V4.0.0

* Added support of Azure SSO authentication type in data collection.
* Upgraded AOB to 4.1.4

### V3.3.0

* Upgraded AOB to 4.1.1

### V3.2.1

* Updated the Copyright information.

### V3.2.0

* Added support for StorageGRID v11.5.
* Added Server validation in Add-on configuration.

### V3.1.0

* Added support for Alerts data for NetApp StorageGRID v11.4 onwards.
* Added support for Splunk v8.1.x

### V3.0.2

* Split events into multiple events for Health_topology_depth_component and Health_topology_depth_node endpoints to support large topologies in StorageGRID.
* Compatibility with StorageGRID App for Splunk v3.0.1.

### V3.0.1

* Default support for Python 3

### V3.0.0

* Added the endpoints to fetch correct data for all newly added panels.
* Removed Certificate Verification check from the Add-on configuration page. By default, all the communication will be done through a secure channel.
* Provided functionality to dynamically use StorageGrid's latest REST API version in the Add-on. 
* Changed the static time attached to some of the Prometheus REST endpoints from the inventory to the interval time of the input.
* Migrated the Add-on to make it Python 2 & 3 compatible.


## Troubleshooting

**The system and input configuration pages are not loaded of the add-on**

1. Check log file for possible errors/warnings: $SPLUNK_HOME/var/log/splunk/splunkd.log


**Data is not being collected**

The following search query can be used to verify that the data is being collected or not

    search `get_sg_index` | stats count by sourcetype

In particular, you should see these sourcetypes:
 1. grid:rest:api
 2. grid:auditlog

If you don't see these sourcetypes
1. Verify the configurations provided in the Add-on i.e. URL, username and password.
2. Verify the parameters provided for the input i.e. index, source and interval and that the input is enabled.
3. If proxy is enabled, verify the details of proxy server provided in the add-on and that the proxy server is working properly.
4. If The StorageGrid instance has a self signed SSL certificate then the entry for that SSL certificate might be missing from your operating system's certificate store. In this case, you would encounter an SSLHandshakeError. Resolve the issue by adding the certificate to your operating system's trust list. Please refer to "Configuring the REST API over secure network connection" section.
5. If your data collection is over unencrypted communication, you must disable the SSL check flag in the Add-on. Please refer to "Configuring the REST API over insecure network connection"  
6. Search for any possible error messages logged by data collection script while trying to fetch REST API data. Here is a sample search that will show them:

        index=_internal sourcetype="tanetapp:sg:log" ERROR 

**Fields are not being extracted**

1. Verify that the add-on is installed in the Splunk environment
2. Verify that the source & sourcetype of the data is according to the list of sourcetype mentioned.

# Binary file declaration

* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with Splunk's Add-on Builder module.

## Support

* Support Information: Community Supported

### Copyright (c) 2024 NetApp, Inc., All Rights Reserved
