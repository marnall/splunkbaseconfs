# ABOUT THIS APP
The purpose of the Cyware Orchestration app is to enable the integration of Cyware Products with Splunk Enterprise application. This app can push the triggered alert and notable Events from Splunk to Cyware Orchestration. Once the app is successfully added and configured to the Splunk platform, analysts can utilize it to perform the configured actions. On receiving the alert, CSOL processes the Event data using default Playbooks available in the application. The actions configured in the Playbook reads the Splunk Event data and links it to the Cyware Orchestration app data fields. Thereafter, Cyware Orchestration app creates an Incident using the mapped field data that can be utilized for further Incident Response operations.

# REQUIREMENTS
* Splunk Enterprise 7.0 or above

# Recommended System configuration
* Standard Splunk Enterprise configuration.

# Installation in Splunk Cloud
* Same as an on-premise setup.

# Installation of App
* This app can be installed from the UI using "Manage Apps" or using the following command in the command line tool.

$SPLUNK_HOME/bin/splunk install app $PATH_TO_TGZ/CywareApp.tgz
* Users can directly extract the app's tgz file into “$SPLUNK_HOME/etc/apps/” folder in order to install the app.

# Application Setup
* Once the app is installed successfully, users must configure the app. To configure the Cyware Orchestration app in Splunk, the following parameters must be added as received from the Cyware Orchestration application.
1) Cyware URL: This is a mandatory parameter and denotes the DNS address of the Cyware Orchestration.
2) Cyware Access Key: This is a mandatory parameter and is required to access the Cyware Orchestration API
3) Cyware Secret Key: This is a mandatory parameter and is required to access the Cyware Orchestration API
4) Verify TLS Certificate: This is a mandatory parameter. You can choose to either verify or skip the TLS certificate verification.
5) No Proxy: This is a mandatory parameter. You can choose to apply the no_proxy configuration or use the system configured proxy configuration.

#Finish installation
After finishing the configuration, users can Trigger Actions for Alerts or Send Notable Events to Cyware Orchestration from the Splunk platform.

# Troubleshooting
* Environment variable SPLUNK_HOME must be configured
* If the app settings are changed multiple times, Splunk application must be restarted for the new changes to take effect.

# Support
Clients can file issues by sending an email at support@cyware.com.
