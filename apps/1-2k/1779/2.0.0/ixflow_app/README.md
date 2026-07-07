# Ixia IxFlow App for Splunk

## OVERVIEW

The Ixia IxFlow application for Splunk allows Ixia IxFlow Application & Threat Intelligence Processor (ATIP) flow data to be indexed and reported in Splunk.

Author - Ixia – A Keysight Business  
Version - 2.0.0
Build - 37
Creates Index - False  
Splunk Enterprise version: 7.0.x, 7.1.x, 7.2.x  
Splunk Stream: 7.1.2  
Common Information Model: 4.13.0  
OS: Platform independent  
Browsers : Chrome, Firefox, InternetExplorer
Prerequisites: Splunk Stream(https://splunkbase.splunk.com/app/1809/)

## EULA
http://downloads.ixiacom.com/support/warranty/EULA/SPLUNK_APP_SOFTWARE_END_USER_LICENSE_AGREEMENT.pdf

## 3rd PARTY TOOLS:
* Donut - Custom Visualization: https://splunkbase.splunk.com/app/3238/
    * License: https://d38o4gzaohghws.cloudfront.net/static/misc/eula.html

## KNOWN ISSUES:
* Real-time options from the timeframe won't be hidden in Splunk v7.1 or below.(Ref: SPL-76798 https://docs.splunk.com/Documentation/Splunk/7.1.8/ReleaseNotes/KnownIssues)

## RELEASE NOTES

### VERSION 2.0.0
* Changed data collection method using Splunk Stream
* Created new dashboards
    * Overview
    * App Details
    * Web/SSL Traffic
    * DNS Traffic
    * Threat Traffic
* Renamed app's name to Ixia IxFlow
## INSTALLATION

### Standalone Setup without Stream Forwarder
This section provides the steps to install App. If you are going to install Ixia IxFlow App For Splunk, it is mandatory to have the Stream App/Addon installed as well because this app is dependent on Stream App/Addon.

On a standalone Splunk installation, the App can be installed either:
* Through the Splunk user interface from Manage Apps.
* By extracting the compressed file (ixflow_app-Sxx-x.x.x-x.tar.gz) into the $SPLUNK_HOME$/etc/apps folder and restarting Splunk.

#### CONFIGURATION
* Install the Stream App from Splunkbase(https://splunkbase.splunk.com/app/1809/).
* Download Ixia IxFlow App For Splunk from Splunkbase(https://splunkbase.splunk.com/app/1779/.
* Select Collect data from this machine option.
* Select Configuration -> Configure Streams and disable all streams.
* Now search for netflow and enable the netflow stream to collect only neflow data.
* Copy ixia.xml from folder(`$SPLUNK_HOME/etc/apps/ixflow_app/config`) to folder(`$SPLUNK_HOME/etc/apps/splunk_app_stream/default/vocabularies`) and to folder(`$SPLUNK_HOME/etc/apps/Splunk_TA_stream/default/vocabularies`)
* Copy netflow from folder(`$SPLUNK_HOME/etc/apps/ixflow_app/config`) to folder(`$SPLUNK_HOME/etc/apps/splunk_app_stream/default/streams`)
* Copy streamfwd.conf from folder(`$SPLUNK_HOME/etc/apps/ixflow_app/config`) to folder(`$SPLUNK_HOME/etc/apps/Splunk_TA_ stream /local`)
* Now you need to change some of parameter in the config file named streamfwd.conf. Copy HTTP event collector token from settings -> Data Inputs -> HTTP Event Collector -> Copy Token for Name (streamfwd).
* Now Click on Global Settings and enable the HEC and disable SSL
* Change streamfwd.conf like below:
~~~~
    [streamfwd]
    ipAddr = 127.0.0.1
    httpEventCollectorToken = f2060850-973b-4743-8d85-d5e89ccc28fd
    processingThreads = 4
    netflowReceiver.0.ip = 0.0.0.0
    netflowReceiver.0.port = 4739
    netflowReceiver.0.decoder = netflow
~~~~
* Restart Splunk

## UNINSTALLATION

This section provides the steps to uninstall App from a standalone Splunk platform installation.

* (Optional) If you want to remove data from Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
`$SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>`
* Delete the app and its directory. The app and its directory are typically located in the folder`$SPLUNK_HOME/etc/apps/<appname>` or run the following command in the CLI:
`$SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password>`
* You may need to remove user-specific directories created for your app by deleting any files found here: `$SPLUNK_HOME/bin/etc/users/*/<appname>`
* Restart the Splunk platform.You can navigate to Settings -> Server controls and click the restart button in splunk web UI or use the following splunk CLI command to restart splunk :
`$SPLUNK_HOME/bin/splunk  restart`
    
## SPLUNK KNOWLEDGE OBJECTS

### INDEX
* The Ixia IxFlow App for Splunk can populate the panels based on the index that is defined while indexing data into the Splunk using Stream Addon. The data gets indexed into the index, which was selected in the HEC on Splunk. 
* Also, If you want to collect data into different index, you must create the index before starting the data collection.
* If you want to use a different index than main, you should make changes in following places to reduce the scope of search:
    * Use the new index name updating the HEC token named streamfwd.
    * Go to Splunk Stream -> Configuration -> Configure Streams
    * Search for netflow protocol and click on edit
    * You can select the index from the list

### SOURCETYPE
* Source types are the default Splunk fields that categorize and filter the indexed data to narrow down the search results. We are using stream:netflow sourcetype which is created by Splunk Stream.

### DATAMODELS
* The App has a data model called Ixia. We have created this datamodel to improve the performance of dashboards and used this datamodel to build the dashboards.
* To improve the dashboard performance:
* If you want to improve the performance of dashboards, you must need to enable the acceleration of datamodel. Please follow below steps:
    * Go to Settings -> Data Models
    * Search for Ixia
    * In Action tab, Click on Edit and click Edit Acceleration
    * Check Acceleration checkbox and select the appropriate summary range and Save it
* Warning: Acceleration may increase storage and processing costs.

### LOOKUPS
* Flowfix_protocol: It contains the mapping of protocol id and protocol name
* Flowfix_services: It cotains ports and their transport and services

### EVENTYPES
* To exclusively retrieve a specific type of event (based on the constraints added in search query), eventtype searches are defined. Eventtypes are defined in the eventtypes.conf file. These eventtypes are used to map the CIM datamodel.

### PROPS AND TRANSFORMS
* Attributes that are extracted from Stream events and are renamed to map them to fields available under CIM data model. This renaming is termed as field aliasing. Fieldalias for all the extracted fields are provided in the props.conf file.

### TAGS
* For every eventtype, specific tags that are applicable as per the types of events found are defined in the tags.conf file. Tags are keywords that you can include in search queries to retrieve specific event data. For example, if `tag=Network`, all the events with the Network  tag are provided as output.

## TROUBLESHOOTING

### DASHBOARDS NOT POPULATING
* After you complete the installation of the App and followed all the configuration steps, all the dashboards start populating data. If you don’t see data in the dashboards, use following steps for troubleshooting:
    * Confirm that you have configured the correct HEC token in streamfwd.conf file
    * You need to verify the data collection by hitting below search:
        * `index=<your indexname> sourcetype=stream:netflow`

### NO ROUTE TO HOST
* If you are using streamfwd for data collection and in streamfwd.log(`$streamfwd/var/log`) if  you are getting below message:
`2019-04-15 13:01:35 WARN  [140333405312768] (HTTPRequestSender.cpp:1485) stream.SplunkSenderHTTPEventCollector - (#0) TCP connection failed: No route to host`
* You need to add the hostname and IP mapping into etc/hosts.

### UNABLE TO BIND 8889 PORT
* If you are using stramfwd for data collection and in streamfwd.log($streamfwd/var/log) if  you are getting below message:
`2019-04-15 12:51:24 ERROR [140087880816512] (tcp_server.cpp:98) pion.http.server - Unable to bind to port 8889: bind: Cannot assign requested address`
* You need to remove entry(port=8889) from the streamfwd.conf($streamfwd/default).

### GETTING INVALID TOKEN
* If you are using stramfwd for data collection and in streamfwd.log($streamfwd/var/log) if  you are getting below message:
`2019-05-16 11:51:50 ERROR [140342552688384] (HTTPRequestSender.cpp:1408) stream.SplunkSenderHTTPEventCollector - (#9) HTTP request [http://16.2.1.2:8088/services/collector/event?index=_internal&host=ubuntu&source=stream&sourcetype=stream:log] response = 403 Forbidden {"text":"Invalid token","code":4}`
* You need to verify the HEC token is correct or not.

### GETTING 500 ERROR
* If you are using stramfwd for data collection and in streamfwd.log($streamfwd/var/log) if  you are getting below message:
`2019-05-16 11:51:59 ERROR [140525075048256] (CaptureServer.cpp:2210) stream.CaptureServer - Unable to update streams config (sender=76eb7e59-522f-427f-81a4-be84bf8ea157): /en-us/custom/splunk_app_stream/streams/?streamForwarderId=ubuntu status=500`
* You need to disable and enable the Splunk Stream App on Splunk instance.

### ADDITIONAL TROUBLESHOOTING
* You can refer below link for further debugging.
Link: https://docs.splunk.com/Documentation/StreamApp/7.1.3/DeployStreamApp/Troubleshooting

## SUPPORT
Feel free to contact the Ixia for additional information about Ixia AppStack (https://www.ixiacom.com/products/appstack)

(c) Keysight Technologies 2019