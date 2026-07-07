Proofpoint Digital Risk TA for Splunk
==========================

# OVERVIEW
The Proofpoint Digital Risk TA for Splunk is used to get data from Proofpoint Digital Risk platform .

* Author - Nazneen-PFPT
* Version - 1.2.0
* Creates Index - False
* Prerequisites - Proofpoint Digital Risk Access token.
* Compatible with:
    * Splunk Enterprise version: 9.2.x, 9.1.x, and 9.0.x
    * OS: Platform independent
    * Browser: Safari, Chrome, Firefox, and Microsoft Edge


# RELEASE NOTES 

## VERSION 1.2.0
* Upgraded the app using Splunk Add-on Builder v4.2.0 to eliminate security vulnerabilities.

## VERSION 1.1.0
* Upgraded the app using Splunk Add-on Builder v4.0.0 to eliminate security vulnerabilities.
* Added proxy support.
* Added support for multiple accounts.

# TOPOLOGY AND SETTING UP SPLUNK ENVIRONMENT
* This app can be set up in two ways:
    
    1. **Standalone Mode**:
        * Install the Proofpoint Digital Risk TA for Splunk.
    2. **Distributed Environment**:
        * Install the Proofpoint Digital Risk TA for Splunk on the search head. User does not need to configure an account or create an input in Proofpoint Digital Risk TA for Splunk on search head.
        * Install only Proofpoint Digital Risk TA for Splunk on the heavy forwarder. User needs to configure account and needs to create data input to collect data from Proofpoint Digital Risk platform.
        * User needs to manually create an index on the indexer (No need to install Proofpoint Digital Risk TA for Splunk on indexer).

# INSTALLATION
Proofpoint Digital Risk TA for Splunk can be installed through UI using "Manage Apps" > "Install app from file" or by extracting tarball directly into $SPLUNK_HOME/etc/apps/ folder.

# CONFIGURATION
* Users will be required to have admin_all_objects capability in order to configure Proofpoint Digital Risk TA for Splunk. This App allows a user to configure multiple accounts of Proofpoint Digital Risk Instance. In case a user is using the integration in search head cluster environment, configuration on all the search cluster nodes will be overwritten as and when a user changes some configuration on any one of the search head cluster members. Hence a user should configure the integration on only one of the search head cluster members. Once the installation is done successfully, follow the below steps to configure.

## 1. Add Proofpoint Digital Risk Account
To configure Proofpoint Digital Risk account, navigate to Proofpoint Digital Risk TA for Splunk, click on "Configuration", go to "Accounts" tab, click on "Add" button and fill in the details asked and click "Add". Field descriptions are as below:

| Field Name                 | Field Description                             |
| -------------------------- | --------------------------------------------- |
| Account Name               | Unique name for your account                  |
| Access Token               | Access token from DR team.                    |


## 2. Configure Proxy (Required only if the requests should go via proxy server)
Navigate to Proofpoint Digital Risk TA for Splunk, click on "Configuration", go to the "Proxy" tab, fill in the details asked and click "Save". Field descriptions are as below:

| Field Name            | Field Description                                                              |
| -------------------   | ------------------------------------------------------------------------------ |
| Enable                | Enable/Disable proxy                                                           |
| Proxy Type            | Type of proxy                                                                  |
| Host                  | Hostname/IP Address of the proxy                                               |
| Port                  | Port of proxy                                                                  |
| Username              | Username for proxy authentication (Username and Password are inclusive fields) |
| Password              | Password for proxy authentication (Username and Password are inclusive fields) |


After enabling proxy, re-visit the "Account" tab, edit/create a new account and save it to verify if the proxy is working.

## 3. Configure Logging (Optional)
Navigate to Proofpoint Digital Risk TA for Splunk, click on "Configuration", go to the "Logging" tab, select the preferred "Log level" value from the dropdown and click "Save".

## 4. Create Data Inputs
This App allows a user to configure multiple inputs to collect data from Proofpoint Digital Risk instance. To create an input, navigate to Proofpoint Digital Risk TA for Splunk, click on "Inputs" tab, and click on "Create New Input". Fill in the details asked and click "Add". 

Field descriptions are as below:

| Field Name       | Field Description                                                                   | Default Value       |
| ---------------- | ----------------------------------------------------------------------------------- | ------------------- |
| Name             | Unique name of your data input.                                                     | None                |
| Interval         | Time interval of input in seconds.                                                  | 86400               |
| Index            | Splunk index you wants to index your data into.                                     | default             |
| Global Account   | Account to be used for data collection.                                             | None                |

# UPGRADE
Upgrade from Proofpoint Digital Risk TA for Splunk v1.0.x to v1.1.0 or above is NOT supported. Still one can install v1.1.0 or above version of Proofpoint Digital Risk TA for Splunk by following the steps mentioned below:

* Disable all the existing inputs.
* Delete all the existing inputs.
* Install the Proofpoint Digital Risk TA for Splunk v1.1.0 or above.
* Restart the Splunk if prompt.
* Navigate to Proofpoint Digital Risk TA for Splunk and perform the Configuration as mentioned in above section.

# TROUBLESHOOTING
* Authentication Failure: Check the network connectivity and verify that the configuration details provided are correct.
* For any other unknown failure, please check the $SPLUNK_HOME/var/log/ta_proofpoint_digital_risk_app_for_splunk_*.log files to get more details on the issue. Same logs can be viewed in Search using `index=_internal  sourcetype="taproofpointdigitalriskappforsplunk:log"`

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# UNINSTALL & CLEANUP STEPS

* Remove $SPLUNK_HOME/etc/apps/TA-proofpoint-digital-risk-app-for-splunk/
* Remove $SPLUNK_HOME/var/log/ta_proofpoint_digital_risk_app_for_splunk_*.log
* To reflect the cleanup changes in UI, restart Splunk instance. Refer https://docs.splunk.com/Documentation/Splunk/latest/Admin/StartSplunk documentation to get information on how to restart Splunk.

**Note**: $SPLUNK_HOME denotes the path where Splunk is installed. Ex: /opt/splunk

# SUPPORT
* Support Offered: Yes
* Please create a support request in case of any issues on https://nexgate.zendesk.com/hc/en-us

# Binary file declaration

* _yaml.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with yaml module and the source code for the same can be found at https://pypi.org/project/yaml/
* _speedups.cpython-37m-x86_64-linux-gnu.so - This binary file is provided along with GRPC module and the source code for the same can be found at https://pypi.org/project/MarkupSafe/

# COPYRIGHT
Copyright (c) 2024. All rights reserved.


