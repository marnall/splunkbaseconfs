Salt Security App for Splunk® by Salt Security.
==========
For support, please e-mail support@salt.security

## OVERVIEW

Author: Salt Security 
App Version: 1.0.0
Vendor Products: Salt Security Platform


## Description ############################

The Salt Security App for Splunk leverages the Salt Security Platform to provide insights on security, reliability, and attacker information for API endpoints. This application includes dashboards to facilitate the search and correlation of logs received from the Salt Security Platform.

The Salt Security App for Splunk is compatible with Splunk Enterprise and/or Splunk Cloud 9.x releases and supports single Search Head deployments as well as being deployed on Search Head Clusters.


## Prerequisites and Requirements ############################

1. Salt Security Technology Add-on for Splunk is installed and configured on the Search Head.

2. Salt Security data indexed and available within Splunk with the sourcetypes salt:syslog:attacker, salt:syslog:attacker_data, and salt:syslog:attacker_action.

3. Splunk Enterprise or Splunk Cloud Platform version 9.x



## INSTALLATION AND CONFIGURATION

## Installation steps ############################

1. Ensure the Prerequisites and Requirements documented above are met.

2. Download the Salt Security App for Splunk from Splunkbase.

3. Install the app on your search tier using standard application deployment methods. Information on installing applications and add-ons on the Splunk platform can be found in the Splunk documentation here: https://docs.splunk.com/Documentation/Splunk/latest/Admin/Deployappsandadd-ons

4. The Salt Security App for Splunk is now installed. Enjoy!


## Post-Installation Step ############################

Following installation of the application, the index name where the Salt Security data exists needs to be updated in the pre-packaged macro. Please follow these steps to do so:
	1) Click on the Settings menu in the top right of the Splunk screen
	2) Click on Advanced search
	3) Click on Search macros
	4) Click on the macro named salt_index
	5) Change the value salt to the name of your index with Salt Security data in it.

Once this is updated with the proper index name, the dashboards, event types, tags and all other macros in the app will be updated automatically.


## Release notes ############################
1.0.0 - First application release

