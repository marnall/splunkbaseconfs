App_greenbone
----------------
OUTLINE
----------------------
This app provides visualisations for the companion add-on TA_greenbone.  
Dashboards created in Dashboard Studio.  
Dashboards are a mix of Datmodel data and log data.  

 
REQUIREMENTS
---------------------
TA_greenbone should be installed and working.  This app relies on the fields created by that app and the CIM normalisations for the Datamodels.  

MACROS
---------------------
This app utilises a few macros which may need adjustment for your environment:  

`gvm_index` --- Configure this to point to the index where you store your Greenbone logs  
`dm_gvm_only` --- Used to limit data from the Vulnerabilities datamodel to Greenbone data only  
`dm_auth_gvm_only` --- User to limit data from the Authentication datamodel to Greenbone data only  

CHANGES IN THIS VERSION  
-----------------------   
Removed filter from Vulnerability Trend timeline on Management Overview dashboard.  
Re-labelled the App to show Visualisations for Greenbone Community Edition as the name.  
Fixed Authentication timeline on Greenbone Management dashboard.  
Added new panel to Mangement Overview to monitor scan target changes.  
Added new dashboard "Vulnerability Dashboard" to take a look at what information there is around detected vulnerabilities.  

FUTURE RELEASE PLANS
--------------------
TBC  

BUILD NOTES
-----------
This app was built on Splunk Enterprise v9.1.1 with CIM version 5.2.0  
This app was configured against a single server running Greenbone Community Edition 22.8
