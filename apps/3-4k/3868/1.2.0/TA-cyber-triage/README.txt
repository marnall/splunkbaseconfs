This add-on integrates Cyber Triage (http://www.cybertriage.com) to allow you to collect endpoint investigation data and import analysis results. 

Cyber Triage allows you to perform a mini-forensic investigation on an endpoint. It pushes a collection tool to the remote endpoint to collect volatile and file system data and analyzes the data.  You can start a collection from within Splunk and import the Cyber Triage results. 


STARTING A COLLECTION

To start a collection of a remote endpoint, you’ll need to have the Team version of Cyber Triage (and not the standalone desktop version).  You will also need to configure the app to define things like the Cyber Triage Server hostname and API key. 

You can start the collection by adding Cyber Triage as a “Trigger Action” for an Alert.  You will need to specify the hostname or IP of the target endpoint. 

If you configured Cyber Triage so that it uses your own SSL certificate instead of the default one, then change the verify server cert property in the Splunk app to True and place your PEM formatted cert into %SPLUNK_HOME%\etc\auth as cybertriage.pem.


IMPORTING DATA

You can also import your Cyber Triage results back into Splunk so that you can later do searches and correlations.  You can do this with the Standard (desktop) and Team versions of Cyber Triage.  

You first need to generate a JSON Report from the Cyber Triage dashboard. Next, import it into Splunk with the “Add Data” feature.  Pick the JSON and and specify the Application/cybertriage  source type.  This will map Cyber Triage data to the following CIM data models:

 - Authentication/Failed_Authentication
 - Authentication/Successfull_Authentication
 - Application_State/All_Application_State/Ports
 - Application_State/All_Application_State/Processes
 - Application_State/All_Application_State/Services
 - Change_Analysis/Account_Management/Accounts_Created
 - Network_Traffic/All_Traffic
 - Malware
 - Web


SUPPORT

If you have any problems or need an evaluation copy of Cyber Triage, then please email support@cybertriage.com.

