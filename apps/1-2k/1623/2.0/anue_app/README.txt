****** Author: Iordache Nicolae, Greg Copeland ****************

The Anue app for Splunk provides basic statistics reporting from the Anue Net Tool Optimizer (NTO) by Ixia,
The app relies of the NTO's WebApi feature that is available starting with the 3.9.0/4.1.0 releases of the NTO. 

Each configured NTO chassis is polled for statistics periodically through a scripted input. The  
the received statistics are indexed into Splunk, and can be visualized from the reporting views. Statistics  for all 
types of ports (tool, network) and dynamic filters can be collected and visualized. Bidirectional ports are treated as
both tool ports & network ones (and will provide both types of statistics)

1) Target Platform . The Anue app is intended to be used with Splunk 5.0.5.or newer.

2) System requirements. This app has been tested with Splunk running on Windows based operating systems. 
   (other OS are possible, but not tested at this time)

3) Installation. Install the app using the Splunk platform; 
   Go to Manager -> Apps -> Install App from File
   - Browse for the "anue_app.spl" file
   - Click Upload 
   - The Splunk Framework detects that it needs to restarts itself
   - Click to Restart Splunk 
   After installation the app label is visible and can be run within the Splunk Platform "App" tab. 
   
4) Configuration.  The app starts with no settings configured. Use the in-app 
   "Setup" tab to add chassis. Input the desired NTO chassis ip address, along with
   the credentials necessary to access it and the WebApi port (leave the default tcp port 8000).
   Then for each added chassis the app allows the possibility to configure what tool/network/bidirectional 
   ports and dynamic filter to poll . Use the "Setup" menu anytime you need to change the current poll configuration.
   
   Note: Within the Splunk Manager->Data Inputs->Script  , do not change the properties 
   for the app's inputed script, that is "...\anue.py"
   
5) Running the Anue app. After at least one port a dynamic filter has been configured for a NTO, the app periodically polls 
   that NTOs and ask statistics for the configured entities . The received statistics are indexed within 
   Splunk, and used to build  visualizations. The available views are grouped into three menu tabs. Tool Port Statistics,
   Network Port Statistics, Dynamic Filters Statistics. 
   Tool Port Statistics menu contains views concerning tool ports only : "Current Utilization", "Current Rate", "Current Drops" 
   and "De-Duplication". The "De-Duplication" view provides visualization only for Advanced Feature Module (AFM) type TOOL ports. 
   Network Port Statistics menu contains views associated only with network ports: "Pass Deny Rate","Current Rate","Current Utililization",
   "De-duplication". Again the "De-Duplication" view provides visualization only for Advanced Feature Module (AFM) type NETWORK ports. 
   The Dynamic Filters Statistics menu groups views related to dynamic filters : "Current Rate in Bits","Current Rate in Packets".
   In each of the available views there is a UI dropdown that allows to select the available NTO from which to visualize statistics.
   Selecting an option from the mentioned dropdown generates an additional dropdown containing the configured entities for the selected NTO
   , if there are any available.  The time range can be selected using the Splunk build-in time range picker.
   
6) Feature list. Currently the following statistics are available for visualization:
   	TOOL Ports : 
   	- tp_current_tx_utilization (Current Utilization view)
	- tp_current_pass_percent_packets (Current Utilization view)	
	- tp_current_tx_rate_bits (Current Rate view)
	- tp_current_drop_rate_packets (Current Drops view)
	- tp_current_tx_rate_packets (Current Drops view)
	- tp_current_insp_rate_packets (Current Drops view)
	- tp_total_dedup_percent_packets (De-Duplication view)
	
	NETWORK Ports :
	- np_current_pass_rate_packets (Pass Deny Rate)
	- np_current_deny_rate_packets (Pass Deny Rate)
	- np_current_rx_rate_bits (Current Rate)
	- np_current_rx_utilization (Current Utililization)
	- np_total_dedup_percent_packets (Deduplication)
	
	DYNAMIC FILTERS :
	- df_current_pass_rate_bits 
	- df_current_insp_rate_bits
	- df_current_deny_rate_bits
	- df_current_pass_rate_packets
	- df_current_insp_rate_packets
	- df_current_deny_rate_packets
	
7) Troubleshooting. If the Anue app does not behave as expected, check the app logs
   for indication of encountered problem. These are located at :
   -[SPLUNK_HOME]\var\log\splunk\"Anue-nto_ip_address".log  for each NTO
   -[SPLUNK_HOME]\var\log\splunk\AnueController.log   
   -[SPLUNK_HOME]\var\log\splunk\AnueChassisSelector.log
   -[SPLUNK_HOME]\var\log\splunk\AnueIdSelector.log
   -[SPLUNK_HOME]\var\log\splunk\AnueConfigParser.log
   If the problem persists, restarting the Splunk Framework is suggested.
   
8) Known issues and limitation.
   - The "Custom time" option in Time Range Picker is not well supported.

    
 

  