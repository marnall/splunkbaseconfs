TA_greenbone v1.0.2
-------------------
OUTLINE
----------------------
This add-on has been written to work with data from the Greenbone Community Edition vulnerability scanner.  
 
Compliance with Splunk CIM has been adhered to so any data seen by this TA should work fine with CIM datamodels and products like ES.  

TCP INPUT SPECIFIC INFO
---------------------

Setup your input on Splunk as per the example below or in default/inputs.conf.  
Configure Greenbone to send alerts to Splunk and edit any existing scans to send logs about the scans to Splunk.  
See here for Greenbone official docs : https://docs.greenbone.net/GSM-Manual/gos-21.04/en/connecting-other-systems.html?#configuring-a-splunk-alert  

LOG FILE SPECIFIC INFO
---------------------

Use the template in default/inputs.conf as a starting point.  Depending on your OS your logs may live in a different location.


INPUTS.CONF EXAMPLE
--------------------------------------
Replace the index name with whatever index you are using.  
TCP INPUT (for receiving reports from GVM)  


[tcp://IP_OR_FQDN_OF_GREENBONE_SERVER:7680]  
connection_host = dns  
disabled = 1  
index = greenbone  
sourcetype = gvm:reports  

LOG FILE MONITORS  

[monitor:///var/log/gvm/gvmd.log]  
disabled = 1  
index=greenbone  
sourcetype=gvm:gvmd  

[monitor:///var/log/gvm/gsad.log]  
disabled = 1  
index=greenbone  
sourcetype=gvm:gsad  
  
[monitor:///var/log/gvm/notus-scanner.log]  
disabled = 1   
index=greenbone  
sourcetype=gvm:notus  

[monitor:///var/log/gvm/openvas.log]  
disabled = 1  
index=greenbone   
sourcetype=gvm:openvas  

[monitor:///var/log/gvm/ospd-openvas.log]  
disabled = 1  
index=greenbone  
sourcetype=gvm:ospd  

CHANGES
-------   
1.0.1 - Fixed target_hostname field where the field was empty in the data.  Otherwise you would see target_hostname="< /hostname >".  

1.0.2 - Altered severity field on vulnerabilties to make it lower case for CIM compliance

FUTURE RELEASE PLANS
--------------------
TBC  

BUILD NOTES
-----------
This add-on was built on Splunk Enterprise v9.2.0.1 and CIM 5.2.0  
This add-on was configured against a single server running Greenbone Community Edition 22.8
