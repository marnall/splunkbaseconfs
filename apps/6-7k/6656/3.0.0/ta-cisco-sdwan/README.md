# Cisco SD-WAN Add-on for Splunk


## OVERVIEW
Cisco SD-WAN Add-on for Splunk collects different types of Syslog Data and Netflow Data and stores them into Splunk indexes.

* Author - Cisco Systems, Inc
* Version - 3.0.0
* Build - 1
* Prerequisites - This application is dependent on "Splunk Add-on for Stream Forwarders", "Splunk App for Stream" and "Cisco SD-WAN HSL Add-on for Splunk" to collect Netflow Data.

## COMPATIBILITY MATRIX
* Browser: Google Chrome, Mozilla Firefox & Safari
* OS: Linux, macOS, Windows
* Splunk Enterprise Version: Splunk 9.0.x, Splunk 8.2.x
* Supported Splunk Deployment: Standalone, Distributed & Cluster
* Splunk Add-on for Stream Forwarders (Third Party Dependency): 8.1.0 & 8.0.2
* Splunk App for Stream (Third Party Dependency): 8.1.0 & 8.0.2
* Cisco SD-WAN HSL Add-on for Splunk (Third Party Dependency): 1.0.0


## RECOMMENDED SYSTEM CONFIGURATION
* Standard Splunk Enterprise configuration of [Search Head, Indexer, and Forwarder](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements).

## TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app has been distributed in two parts.
    
    1. **Cisco SD-WAN Add-on for Splunk**, which parses collected Syslog and NetFlow data.
    2. **Cisco SD-WAN App for Splunk**,  which adds dashboards to visualize Syslog and NetFlow data.

* This app can be set up in two ways:
    
**1) Standalone Mode**:

* Install the "Cisco SD-WAN App for Splunk" and "Cisco SD-WAN Add-on for Splunk" on a single machine. This single machine would serve as a Search Head + Indexer + Heavy Forwarder for this setup.
* The "Cisco SD-WAN App for Splunk" uses the data parsed by the "Cisco SD-WAN Add-on for Splunk" and builds dashboards on it.
  
**2) Distributed Environment**:

* Install the "Cisco SD-WAN App for Splunk" and "Cisco SD-WAN Add-on for Splunk" on the search head.
* Install only "Cisco SD-WAN Add-on for Splunk" on the heavy forwarder. 
* User needs to manually create an index on the Indexer (No need to install "Cisco SD-WAN App for Splunk" on Indexer).
* Note: Installation of "Cisco SD-WAN Add-on for Splunk" on Indexer is required in case of universal forwarder


## INSTALLATION
 Cisco SD-WAN App For Splunk can be installed through UI as shown below. Alternatively, `.tar` or `.spl` file can also be extracted directly into $SPLUNK_HOME/etc/apps/ folder.
 
1. Log in to Splunk Web and navigate to Apps > Manage Apps.
2. Click `Install the app from file`.
3. Click `Choose file` and select the `ta-cisco-sdwan` installation file.
4. Click on `Upload`.
5. Restart Splunk 

## CONFIGURATION

### Configure Inputs on Splunk for Syslog Data:

The "Cisco SD-WAN Add-on for Splunk" manages inputs through TCP/UDP inputs provided by Splunk. To configure inputs:

* Login to Splunk WEB UI.
* Navigate to Settings > Data inputs.
* Choose TCP or UDP and click New.
* In the left pane, click TCP / UDP to add an input.
* Click the TCP or UDP button to choose between a TCP or UDP input.
* In the Port field, enter a port number on which you are forwarding the logs from Cisco SD-WAN.
* In the Source name override field, enter a new source name to override the default source value, if necessary.
* Click Next to continue to the Input Settings page.
* Set the sourcetype as `cisco:firewall:logs`.
* Set App context to Cisco SD-WAN Add-on.
* Set the Index that Splunk Enterprise should send data to for this input.
* Click Review.
* Click Submit once you have ensured everything is correct.

Once the input is configured, execute the following query to see if Syslog events are being received.
* index=<configured_index> sourcetype="cisco:sdwan*" 


### Configure Inputs on Splunk for Netflow Data:

* Prerequisite to collect Netflow data into Splunk:
* Install the following apps in the Splunk instance to collect and parse the NetFlow (v9) data:

    | App | Search Head | Heavy Forwarder | Indexer |
    | --- | ----------- | --------------- | ------- |
    | [Splunk App for Stream](https://splunkbase.splunk.com/app/1809/) | No | Yes | No |
    | [Splunk Add-on for Stream Forwarders](https://splunkbase.splunk.com/app/5238/) | No | Yes | No |
    | [Cisco SD-WAN HSL Add-on for Splunk](https://splunkbase.splunk.com/app/6872) | No | Yes | No |

*  Make sure that the receiver UDP port (Ex. 4739) is open and bypass the firewall traffic.

#### Steps to follow:

* Once the "Splunk App for Stream", "Splunk Add-on for Stream Forwarders" and "Cisco SD-WAN HSL Add-on for Splunk" are installed in the desired Splunk Instance.
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

### Configure Event Types on Splunk Search Head Instance:

To use the CIM mapped fields, a user first needs to configure the event type to provide the index in which the data is being collected. To configure event type:

* Navigate to Settings > Event types.
* Select "Cisco SD-WAN Add-on for Splunk" from the App dropdown.
* Click on "cisco_sdwan_index".
* Update "()" with "index=<your_configured_index>" in the existing definition to use your configured index.
* Click Save.


## UPGRADE

### From v2.0.0 to v3.0.0
* No additional steps are required.

### From 1.0.1 to 2.0.0
* [Non-NetFlow data users] No additional steps are required.
* [NetFlow Data Users] Disable the existing "netflow" stream and enable the "cisco_hsl_cisco_hsl_netflow" stream in the "Splunk App for Stream". Refer "Configure Inputs on Splunk for Netflow Data" section for more details.

### From v1.0.0 to v1.0.1
* No additional steps are required.

## RELEASE NOTES

### Version 3.0.0
* Added extractions for additional fields.

### Version 2.0.0
* Added extractions for additional fields.

### Version 1.0.1
* Added Splunk Classic Cloud compatibility.

## TROUBLESHOOTING

* To check the fields extracted for Syslog data by the Cisco SDWAN Add-on for Splunk:
  *  `index=<your_index_name> sourcetype="cisco:sdwan*"` in Splunk in verbose mode.
  *  "cisco:firewall:logs" must be selected as sourcetype while configuring the Syslog input. 
* To check the fields extracted for Netflow data by the Cisco SDWAN Add-on for Splunk:
    *  `index=<your_index_name> sourcetype="stream*"` in Splunk in verbose mode.


  
**NOTE:**

* Make sure that the user enables forwarding on a configured port from the Cisco SDWAN after performing the above steps.
* $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk


## UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/ta-cisco-sdwan
* To reflect the cleanup changes in UI, Restart the Splunk Enterprise instance

## SUPPORT
* Support Offered: Yes
* Support Email: tac@cisco.com
  
### Copyright (c) 2023 Cisco Systems, Inc. All rights reserved.