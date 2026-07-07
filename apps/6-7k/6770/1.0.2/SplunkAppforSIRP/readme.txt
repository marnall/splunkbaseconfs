*********************************************
*
* Add-On: SIRP SOAR Add-On for Splunk
* Current Version: 1.0
* Last Modified: Jan 2023
* Splunk Version: 8.x
* Author: SIRP Labs
*
*********************************************



**** Overview ****

SIRP SOAR Add-On for Splunk is the technical add-on (TA) developed by SIRP Labs. This add-on enables Splunk Enterprise users to push high-fidelity alerts and incidents from Splunk to SIRP SOAR, in real time.

**** Requirements ****
 - Splunk version 7.x >=
 - This application should be installed on Search Head.

**** Recommended System Configuration **** 
 - Standard Splunk configuration of Search Head.

**** Installation **** 
There are three ways to install SIRP Add-on for Splunk:
 - Install from Splunk web UI. Go to Manage Apps > Browse > More apps > Search "SIRP". Locate the SIRP app then Click "install" button to initiate the installation. Once the process is completed, restart Splunk Service to finish the installation.
 - Download the Add-on file from https://splunkbase.splunk.com/apps and install from Splunk web UI. Go to Manage Apps > Click Install app from file > Locate and Upload the downloaded.spl file (Check the upgrade box). Once the process is completed, restart Splunk Service to finish the installation.
 - Download the Add-on file from https://splunkbase.splunk.com/apps. Upload the downloaded file on your Splunk server and extract the .spl file into $SPLUNK_HOME/etc/apps/ folder.


**** Application Setup **** 
 - Once the add-on is installed and you open the app, a setup page will appear. Enter the following configuration details and then click 'Submit' to save the configuration:
 	SIRP Instance URL
 	SIRP API Key
	Certificate Path - full path to the SSL certificate on the Splunk server. (Note: this is optional but recommended as this certificate is used to make secure API calls to SIRP.

**** New Custom Alert Action **** 
 - Once installed, this add-on will add a new custom alert action named "Push Alerts to SIRP". 


**** How to Use Custom Alert Action ****
 - Click Search and Reporting from the top menu. 
 - Create/write a new search query and press enter. Once you are satisfied with the results, save your search as an alert by clicking on "Save As" button.
 - In the configuration of the new Alert, click "Add Actions" and choose "Push Alerts to SIRP" from the dropdown. 
 - Configure the Incident details to define the field mapping between SIRP and Splunk:
	Subject/Title of the Alert
	Priority
	Severity
	Payload – a comma-separated "key":"value" pairs of custom fields. e.g, {"Subject":"$result.Title$", "Category":"$result.Category$"}
	Artifacts – a comma-separated "key":"value" pairs of artifacts/IOCs e.g. {"Destination IP":"$result.Destination_IP$","Source IP": "$result.Message$"}

Note: $result.field-name$ is a format to define Splunk fields in the "value" against the SIRP fields which are defined as "key".

Once configured successfully, new alerts from Splunk will be pushed to and visible in SIRP's Incident Management module. 



**** Release Notes ****

v1.0: Jan 2023
        - Initial release

