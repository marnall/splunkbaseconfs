   ===Trend Micro Deep Discovery App for Splunk ===

   Author: Jia-bing (JB) Cheng

   Version/Date: 1.1.2/Mon Dec  4 07:18:13 UTC 2017

   Supported product(s): Splunk Enterprise 6.1, 6.2, 6.3

   Source type(s): cefevents tmef-* squid

   Input requirements: Trend Micro Deep Discovery Inspector TMEF syslog output format
            (optional) Trend Micro Deep Discovery Analyzor CEF/TMEF syslog output 

   ===Using this app ===

   Configuration: Manual configuration required.

        Go to Configuration > App Setup to specify the indexes and sourcetypes:
        Deep Discovery Event Type: 
            [ e.g., index=ddi_index sourcetype=tmef-* ]
        Web Access Log Event Type:
            [ e.g., index=log_index sourcetype=squid ]

        NOTE: Make sure the Splunk users have access to these indexes.

        Go to Configuration > License to enter a valid Deep Discovery license.
	This is required to make Web Access Log Correlation with information from 
	Trend Micro Smart Protection Network.

   Ports for automatic configuration: TCP port 8080 for input (configurable)

   Scripted input setup: pre-configured 
