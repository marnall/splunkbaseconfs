
Thank you for downloading the Splunk add-on for WeavingThings.

WeavingThings is an IOT integration and operations platform that enables the 
creation of IOT services with a deployed ecosystem of many IOT devices and
sensors. 

WeavingThings allows code free integraion with any industrial equipment
using any protocol (like MODBUS, S7, NETCONF, OPC-UA etc). This add-on enables 
real-time connection of IOT data into Splunk for monitoring or any other 
purpose.

This add-on supports two methods for feeding events into Splunk:

(1) REST API - WeavingThings supports a restful-api interface in order to extract
    information about networks, devices and services allocated in your
    network. To enable this interface:
    
    (*) Select the WeavingThings add-on in the apps menu or the righ task bar
    (*) The add-on is pre-configured with 3 input source types:
         services - collect information about services in the network.
                    This input source type is typically disabled by default, 
                    since the same information is collected through the 
                    more efficient real-time collector data interace (see below).
         devices  - Collect information about devices in the network.
                    Pre-configured to poll the WeavingThings server every
                    500 seconds.  
         networks`- Collect information about your networks.
                    Pre-configured to poll the WeavingThings server every
                    500 seconds.  

        If you need to change any value (like enabling or disabling a source
        type or changing the polling frequency, use the 'add new' option
        to define new source types.

        Events collected from each of the source types can be searched by
        using the relevant source type. For example to get all information 
        collected about networks use:

           sourcetype = wt_networks

    (*) Select add-on configuration/add-on setting. You will need to 
        provide the WeavingThings application key and name. See below instructions
        how to get an application key and/or token.

(2) WebSokcets - This interface allows pushing data into Splunk with 
    a very low latency. Whenever am event occurs in the network, like 
    a new device added or a new value reading from a sensor, an event
    is created within Splunk.
    To enable this interface:

    (*) In the 'Data Input' page select 'HTTP event collector'
    (*) Select 'new token' and define the following:
        Name:       WeavingThings event collector
        Source:     WT_events
        SourceType: Structured/_json
    (*) Locate the directory 'weaving_realtime' under 
             ${SPLUNK_HOME}/etc/apps/TA-weavingthings/bin/
    (*) Run the script start.sh:
             sudo ./start.sh
        You will need to:
        -. Run the script with super-user priviliges
        -. Provide Splunk admin authentication   
        -. Provide WeavingThings authentication
        -. This startup script will authomatically extract the tokens from 
           the Splunk and WeavingThings servers.  
        
Getting WeavingThings application key:

    (*) If you already have a user name/password into the WeavingThings developers
        site, login into the site. In main site page there is a section called application 
	API keys. You should use one of the application name/key pairs for integrating data into 
	splunk. 

	If you do not see an existing key, use the 'create' button to create a new application 
	key/name pair. By pressing the 'create' button a new application key will be assigned.
	Define the application name for which you want to use this key. For example: mySplunk.  
        you will see your application key and name pair. Copy to clipboard and paste it into the add-on
        configuration field in the Splunk add-on.

    (*) If you need a user name/password to the WeavingThings developers site, you can register
	at the WeavingThings site. In case of any difficulty, please contact info@weavingthings.com

Support:

	If you have any question or require help, please contact us at:
            
           info@weavingthings.com


