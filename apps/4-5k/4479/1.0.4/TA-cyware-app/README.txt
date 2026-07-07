# ABOUT THIS APP
The purpose of this app is to enable the integration of CFTR with Splunk Enterprise application. This app can push the triggered alert and notable Events from Splunk to CFTR. Once the app is successfully added and configured to the Splunk platform, analysts can utilize it to perform the configured actions. On receiving the alert, CFTR processes the Event data using default Playbooks available in the application. The actions configured in the Playbook reads the Splunk Event data and links it to the CFTR data fields. Thereafter, CFTR creates an Incident using the mapped field data that can be utilized for further Incident Response operations.

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
* Once the app is installed successfully, users must configure the app. To configure the CFTR app in Splunk, the following parameters must be added as received from the CFTR application.
1) CFTR URL: This is a mandatory parameter and denotes the DNS address of the CFTR.
2) CFTR access key: This is a mandatory parameter and is required to access the CFTR API
3) CFTR secret key: This is a mandatory parameter and is required to access the CFTR API
4) Verify TLS Certificate: This is a mandatory parameter. You can choose to either verify or skip the TLS certificate verification.
5) No Proxy: This is a mandatory parameter. You can choose to apply the no_proxy configuration or use the system configured proxy configuration.

#Finish installation
After finishing the configuration, users can Trigger Actions for Alerts or Send Notable Events to CFTR from the Splunk platform.

# Troubleshooting
* Environment variable SPLUNK_HOME must be configured
* If the app settings are changed multiple times, Splunk application must be restarted for the new changes to take effect.

# Support
Clients can file issues by sending an email at support@cyware.com.
