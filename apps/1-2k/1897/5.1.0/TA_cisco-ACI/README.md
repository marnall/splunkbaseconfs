# ABOUT THIS APP

The Cisco ACI Add-on for Splunk Enterprise is used to gather data from Application Policy Infrastructure Controller (APIC) and MSO (Multi-Site Orchestrator), do indexing on it and provide the indexed data to "Cisco ACI App for Splunk Enterprise" app which runs searches on indexed data and build dashboards using it.

# REQUIREMENTS

* Splunk version supported 9.2.x, 9.1.x and 9.0.x
* APIC version supported 5.2 and 6.0
* MSO version supported 3.1
* NDO version supported 4.1 and 4.2
* This main Add-on requires "Cisco ACI App for Splunk Enterprise" version 5.1.0
* The app works for earlier versions as well, but some features may be restricted.
* Admin user ID and password for collecting data from APIC and/or MSO.
* For non-admin user account, provide 'read-all' role privilege to the user in the APIC.
  * **Note:** All the dashboards may not be populated with the non-admin user, refer to the TA's Set-up page, to get further details about APIC Role Privileges for the particular dashboard.


# Recommended System configuration

* Splunk search head system should have 16 GB of RAM and an octa-core CPU to run this app smoothly.

# Topology and Setting up Splunk Environment

     Install the add-on (Cisco ACI Add-on for Splunk Enterprise) and main app (Cisco ACI App for Splunk Enterprise) on a single machine.

     * Here both the app resides on a single machine.
     * The main app uses the data collected by Add-on and build dashboards on it

     Install the add-on and main app on a distributed clustered environment.
     * Install the App on a Search Head or Search Head Cluster.
     * Install and configure the Add-on on a Heavy forwarder or an Indexer. (Heavy forwarder recommended)
	 
# Installation of App

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Restart Splunk.

* Note: If the previous version of the App is already installed, remove the TA_cisco-ACI folder from the Splunk app folder before the installation of a  newer version or the user can upgrade the app from Splunk UI.
 If the user upgrades the app, it should be ensured that index, sourcetype, and interval must be mentioned for each input in local/inputs.conf

# Upgradation of App/Add-on
  Please disable all the scripted inputs before upgrading Add-on(TA_cisco-ACI).
* Download the App package
* From the UI navigate to `Apps-> Manage Apps`
* In the top right corner select "Install app from file"
* Select "Choose File" and select the App package 
* Check Upgrade App
* Select "Upload" and follow the prompts.
  #### OR
* If a newer version is available on splunkbase, then App/Add-on can be updated from UI also.
  * From the UI navigate to `Apps-> Manage Apps` OR click on the gear icon
  * Search for Cisco ACI App/Add-on
  * Click on `'Update to <version>'` under Version Column.

# Post upgradation steps
####  Upgrading the Add-on(TA_cisco-ACI) to v5.1.0 from any version

Please follow the below steps.

* In inputs.conf file under TA_cisco-ACI/local folder, if stanza containing `'-stats'` is present, then perform the following steps.
  * Change following Classes:
    * eqptEgrTotal5min to eqptEgrTotal15min
    * eqptIngrTotal5min to eqptIngrTotal15min
    * procCPU5min to procCPU15min
    * procMem5min to procMem15min
  * Restart Splunk
    ##### OR
  * Remove that whole stanza and save the file.
  * Restart Splunk

* Follow below steps if you are collecting data using `Certificate Based Authentication` in v4.3.0 OR v4.4.0 and Upgrading Add-on to v5.1.0
  * Take Backup of your Private key.
  * You need to convert your Private key to RSA Private key by running the following command in cmd.
    * openssl rsa -in <old_private_key>.key -out <private_key>.key  
      (Keep the name same for newly generated private_key).

* Enable all the scripted inputs.
* Note: If scripts are already enabled then first disable and then re-enable all the scripted inputs.

# Uninstallation of App

  This section provides the steps to uninstall App from a standalone Splunk platform installation.
  
  * (Optional) If you want to remove data from the Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>
  
  * Delete the app and its directory. The app and its directory are typically located in the folder $SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:
    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password> 
  
  * You may need to remove user-specific directories created for your app by deleting any files found here: $SPLUNK_HOME/bin/etc/users/*/<appname>

  * Restart the Splunk platform. You can navigate to Settings -> Server controls and click the restart button in Splunk web UI or use the following Splunk CLI command to restart Splunk:
    * $SPLUNK_HOME/bin/splunk restart
			
# Configuration of App

  * After installation, navigate to Manage Apps by clicking on the Gear icon next to Apps on the Splunk homepage.
  * Click on the "Setup" button under the Actions section for "Cisco ACI Add-on for Splunk Enterprise"
  * It will open a setup screen which facilitates user to configure APIC and MSO in Splunk.
  * The tabs for the above case is explained below:
    * Configure APIC:
        * This tab provides 3 different modes to collect the APIC data in Splunk. The common fields are APIC Hostname or IP address and APIC Port (optional). 
        * The different modes are:

          * Password Based Authentication
            * The user can configure the app using the default approach i.e. using Password.
            * To setup APIC with Password Based Authentication, follow the below given steps.
              * On the setup screen, enable "Password Based Authentication" checkbox.
              * Enter APIC hostname or IP address of the APIC
              * Enter the port of the APIC. ex:8000(this step is optional)
              * Enter username and password which is used to login to the APIC.
              * Click on the Save button at the bottom of the page.

          * Certificate Based Authentication
            * The user needs to provide Certificate Name (as uploaded on APIC) and Path of RSA Private Key (path to the RSA private key, present on Splunk, of the certificate uploaded on APIC) on the setup page to collect data.
            * The procedure to create and configure a custom certificate for certificate based authentication is given in the below link:
            https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/4-x/basic-configuration/Cisco-APIC-Basic-Configuration-Guide-401/Cisco-APIC-Basic-Configuration-Guide-401_chapter_011.pdf
            * Convert Private key to RSA Private key by running the following command in cmd.
              * openssl rsa -in <private_key>.key -out <rsa_private_key>.key

            * To setup APIC with Certificate based authentication, follow below given steps.
              * On the setup screen, enable "Certificate Based Authentication" checkbox.
              * Enter APIC hostname or IP address of the APIC
              * Enter the port of the APIC. ex:8000 (this step is optional)
              * Enter username to login to the APIC.
              * Enter Name of Certificate.
              * Enter Path of Private Key. ex: /opt/splunk/ACI.key
              * Click on the Save button at the bottom of the page.

          * Remote User Based Authentication
            * The user needs to provide both Password and Domain Name of User specified.

            * To setup APIC with remote user based authentication, follow below given steps.
              * On the setup screen, enable the "Remote User Based Authentication" checkbox.
              * Enter APIC hostname or IP address of the APIC
              * Enter the port of the APIC. ex:8000 (this step is optional)
              * Enter username and password which is used to login to the APIC.
              * Enter the Domain name of the user.
              * Click on the Save button at the bottom of the page.

    * Configure MSO:
        * This tab provides 2 different types of authentication to collect the MSO data in Splunk.
          * Multi-Site Orchestrator
          * Nexus Dashboard
        * For both of these types, the app supports two different modes of authentication. The common fields are MSO Hostname or IP address and MSO Port.
        * The different modes are:

          * Password Based Authentication
            * The user can configure the app using the default approach i.e. using Password.
            * To setup MSO with Password Based Authentication, follow the below given steps.
              * On the setup screen, enable the "Password Based Authentication" checkbox.
              * Enter MSO hostname or IP address of the MSO
              * Enter the port of the MSO. ex:8000(this step is optional)
              * Enter username and password which is used to login to the MSO.
              * Click on the Save button at the bottom of the page.

          * Remote User Based Authentication
            * The user needs to provide both Password and Domain Name of User specified.
            * To setup MSO with Remote User Based authentication, follow below given steps.
              * On the setup screen, enable the "Remote User Based authentication" checkbox.
              * Enter MSO hostname or IP address of the MSO
              * Enter the port of the MSO. ex:8000 (this step is optional)
              * Enter username and password which is used to login to the MSO.
              * Enter the Domain name of the user.
              * Click on the Save button at the bottom of the page.

        * Fetch Sites button:
          * After providing MSO credentials from any of the above two modes, the user can click the Fetch Sites button.
          * It will display sites (i.e. APIC) associated with MSO, so users can directly provide site credentials here to configure in Splunk.
          * After providing credentials, click on the Save button at the bottom of the page.
          * By default SSL verification is enabled. If MSO or APIC Site is configured with Self Signed Certificate refer to SSL Configuration section. 
          
          * Follow the below steps to disable the SSL verification entirely before configuring credentials through the setup page:
          * Copy the file "default/app_setup.conf" to "local/app_setup.conf"
          * Change the value of `verify_ssl` parameter to `False` under stanza [fetch_sites_ssl]
          * Restart Splunk
          * This will disable the SSL verification while configuring credentials through the setup page

Note: Enable all the required scripted inputs if it's not already enabled to collect data.

### SSL Configuration:
* The SSL Connection with APIC/MSO is enabled by default. Users first need to create a custom certificate with the proper Domain name and load the updated certificate for SSL verification.
* The procedure to create a custom certificate for Cisco ACI for HTTPS Access is given in the below link:
     https://www.cisco.com/c/en/us/td/docs/switches/datacenter/aci/apic/sw/kb/b_Configuring_Custom_Certificate_for_ACI_HTTPS_Access.html

* To use the new certificate for connection to APIC/MSO from Splunk, follow the below steps:
  * If your script uses python2.7 for data collection:
    * Navigate to folder $SPLUNK_HOME/lib/python2.7/site-packages/requests.
    * Add your content at the end of the cacert.pem file.

  * If your script uses python3.7 for data collection:
    * Navigate to folder $SPLUNK_HOME/lib/python3.7/site-packages/requests.
    * Add your content at the end of the cacert.pem file.

* Follow the below steps to disable the SSL verification after configuring credentials through the setup page:
  * For Password Based Authentication and Remote User Based Authentication:
    * Provide credentials from setup page.
    * passwords.conf file will be created in TA_cisco-ACI/local folder with sample stanza : [credential:x.x.x.x:<apic/mso/nd_auth>,<port>,<user>,True:].
    * Here, the default value of SSL verification will be True.
    * Change this value from True to False.
    * Restart Splunk.

  * For Certificate Based Authentication:
    * Provide credentials from setup page.
    * cisco_aci_server_setup.conf file will be created in TA_cisco-ACI/local folder with sample stanza : [cisco_aci_server_setup_settings,x.x.x.x].
    * Here, the default value of the cisco_aci_ssl parameter will be True.
    * Change this value from True to False.
    * Restart Splunk.

*  This app supports multiple APIC/MSO entries. Provide more ACI credentials through the setup screen. Configure a maximum of 5 APICs for better performance.
*  For Password Based Authentication and Remote User Based Authentication, Splunk REST API will encrypt the password and store it in the app itself(local/passwords.conf) in encrypted form.

  For Certificate Based Authentication, certificate name, and path to the private key will be stored in the app itself(local/cisco_aci_server_setup.conf). 

  The data collector script will fetch these credentials through the REST API to connect to the APIC.

* APIC Hostname or IP address once configured to any 3 modes of authentication, cannot be configured through the remaining 2 modes of authentication.

* Also, users can setup APIC either using any one of the three modes of authentication or all the three modes one by one but for different APICs.
  * Example: User can either setup only APIC1 using Password/Remote/Certificate Based Authentication.
                          OR
  Users can setup APIC1 for Password Based Authentication, APIC2 for Remote User Based Authentication and APIC3 for Certificate Based Authentication.

* Note: APIC Hostname or IP address once configured to any 3 modes of authentication, cannot be configured through the remaining 2 modes of authentication.

*  Whenever the user wants to change the credentials, he/she needs to remove the current entry from directory TA_cisco-ACI/local/passwords.conf or TA_cisco-ACI/local/cisco_aci_server_setup.conf first.
   Restart Splunk. Provide the credentials through UI.

* MSO Hostname or IP address once configured to any one of the modes of authentication, cannot be configured through the remaining 2 modes of authentication.

* Also, users can setup MSO either using any one of the two modes of authentication or all the two modes one by one but for different MSOs.
  * Example: Users can either setup only MSO1 using Password Based Authentication.
                          OR
  Users can setup MSO1 for Password Based Authentication and MSO2 for Remote User Based Authentication.

*  Whenever the user wants to change the credentials, he/she needs to remove the current entry from directory TA_cisco-ACI/local/passwords.conf first. Restart Splunk. Provide the credentials through UI.

* Note: The hostname configured by APIC, cannot be re-configured for MSO and vice versa.
  * Example: If the user can only configure host1 for APIC and host2 for APIC and not host1 for both APIC and MSO.

*  User also needs to modify "default/inputs.conf" according to the following guidelines.

inputs.conf
===============
This file contains filename paths which are different based on your OS platform. 
The app is configured out of the box to work for Unix/Linux/macOS systems. 

If you are running this app on a Windows system, perform the following steps:
  Copy the file "default/inputs.conf.WINDOWS" to "local/inputs.conf"

* Each entry in default/input.conf contains a field "passAuth" with default value admin. This field can contain any splunk user with admin rights.

# Add More Data to Splunk

* Data Inputs (in inputs.conf) can be added/modified either from the setup page or directly from the backend (as mentioned above)

Setup Page
==============
  Following options are provided on the setup page under the tab "Configure Data Inputs" for modifying data inputs in inputs.conf:
  * Type: Following eight types are allowed in Add-on
    * authentication: To get the authentication information from the ACI environment.
    * classInfo: To get the general information for all the MOs of given APIC classes.
    * cloud: To get the details related objects for all the MOs of given APIC classes.
    * health: To get the health and fault information for all the MOs of given APIC classes.
    * fex: To get the health and fault information for all the MOs of given APIC classes.
    * microsegment: To get the general information for all the MOs of given APIC classes.
    * stats: To get the statistical data for all the MOs of given APIC classes.
    * mso: To get details of various MSO endpoints.
  * Arguments:  Names of APIC classes for which data will be fetched (Names of classes are case-sensitive) or names MSO API endpoints.
  * Interval: Time interval (in seconds) at which data inputs will be scheduled to collect data, once enabled.
  * Enable/Disable: Status representing whether the data input is enabled or not.
  * Actions:
    * Edit:
      * Add/Remove/Modify the existing APIC classes or MSO endpoints.
      * Change time interval of data inputs.
      * Change status of data inputs i.e. enabled/disabled.
      * Click on Add button (under Actions).
    * Delete
      * This button will directly delete data input.
  * Add New Button: It will add new data input in inputs.conf. Again, the user will have the choice for all actions stated above.
  * Click on the Save button after making changes.

  Note- Any change performed by the user will be reflected in default/inputs.conf and local/inputs.conf.

# How to enable collector scripts

* Enable Data collector Scripts. By default Scripts are disabled. Enable through UI (Settings -> Data inputs -> Local inputs-> Scripts).
* Enable the collector scripts labeled under the app name: TA_cisco-ACI
* The user can also enable scripts from Setup Page (as mentioned above)


# Create your own index:

	* The app data defaults to the 'main' index.
	* If you need to specify a particular index for your APIC data, for ex. "apic",create an indexes.conf file [sample shown in ($SPLUNK_HOME/etc/apps/TA_cisco-ACI/default/indexes.conf.sample)]
	* Once you specify your index, edit the inputs.conf file and add a line "index=[yourindex]" under each script stanza.


# The list of Python library packaged
1. Websocket Client Library
	Link: https://pypi.python.org/pypi/websocket-client/
	Author: liris
	Home Page: https://github.com/liris/websocket-client
  Version: 0.35.0
	License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)
	Operating System :: MacOS :: MacOS X
	Operating System :: Microsoft :: Windows
	Operating System :: POSIX
	Programming Language :: Python
	Programming Language :: Python :: 2
	Programming Language :: Python :: 3

	This module depends on
		six
		backports.ssl_match_hostname for Python 2.x

2. RSA Library
	Link: https://pypi.org/project/rsa/
	Author: Sybren A. Stuvel
	Home Page: https://github.com/sybrenstuvel/python-rsa
  Version : 4.0
	License :: OSI Approved :: Apache Software License
	Operating System :: OS Independent
	Programming Language :: Python
	Programming Language :: Python :: 2
	Programming Language :: Python :: 3

# The list of Javascript/CSS libraries used
1. Google Fonts
  Link: https://fonts.googleapis.com/css?family=Roboto|Varela+Round|Open+Sans
  Author: Google
  Home Page:
    Roboto: https://fonts.google.com/specimen/Roboto
    Varela Round: https://fonts.google.com/specimen/Varela+Round
    Open Sans: https://fonts.google.com/specimen/Open+Sans
    Material Icons: https://google.github.io/material-design-icons/
  License:
    Roboto: https://www.apache.org/licenses/LICENSE-2.0
    Varela Round: https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=OFL_web
    Open Sans: https://www.apache.org/licenses/LICENSE-2.0
    Material Icons: https://www.apache.org/licenses/LICENSE-2.0
2. Font Awesome
  Link: https://maxcdn.bootstrapcdn.com/font-awesome/4.7.0/css/font-awesome.min.css
  Author: Dave Gandy
  Home Page: https://fontawesome.com/?from=io
  License: Font: https://scripts.sil.org/cms/scripts/page.php?site_id=nrsi&id=OFL, CSS: https://opensource.org/licenses/MIT
3. Bootstrap
  Link: https://maxcdn.bootstrapcdn.com/bootstrap/3.3.7/js/bootstrap.min.js
  Author: Twitter
  Home Page: https://getbootstrap.com/
  License: https://opensource.org/licenses/MIT

# TEST YOUR INSTALL / TROUBLESHOOTING

The main app dashboard can take some time before the data is returned which will populate some of the panels. A good test to see that you are receiving all of the data we expect is to run this search after several minutes:

    index="<your index>" | stats count by sourcetype

* Troubleshooting APIC configuration:
  * In particular, you should see these sourcetypes:
    * cisco:apic:health
    * cisco:apic:stats
    * cisco:apic:class
    * cisco:apic:authentication
    * cisco:apic:cloud
  * If you don't see these sourcetypes, have a look at the messages output by the scripted input: collect.py. Here is a sample search that will show them:
    index=_internal component="ExecProcessor" collect.py "ACI Error:" | table _time host log_level message

* Troubleshooting MSO configuration:
  * You should see this sourcetype: cisco:mso
  * If you don't see this sourcetype, have a look at the messages output by the scripted input: collect_mso.py. Here is a sample search that will show them:
    index=_internal component="ExecProcessor" collect_mso.py "MSO Error:" | table _time host log_level message

You can also see the $SPLUNK_HOME/var/log/splunk/splunkd.log file to check if any error has occurred.


# ABOUT THE DATA

#### APIC DATA

You can see what each event looks like by going to $SPLUNK_HOME/etc/apps/TA_cisco-ACI/bin and executing collect.py with Splunk Python interpreter. 
Example:
   /opt/splunk/bin/splunk cmd python collect.py -stats fvAp

Each event contains data in the "Field=value" pair. Field names are case sensitive in the Cisco API for APIC. Every event starts with the timestamp and contains the dn(Distinguished Name) field. This field gives a fair idea about the type of information given by the event(health,fault, etc). Like below given dn gives health details for Tenant "abc".

dn="uni/tn-abc/health"

Below are two sample event records. The first one gives health detail for the tenant with the name "common" and the other one gives a fault detail for the same tenant.

1)

2014-04-25 00:38:07     dn=uni/tn-common/health status=created,modified updTs=2014-04-25T04:52:32.274+00:00     chng=0  cur=100 maxSev=cleared  modTs=never     twScore=100     rn=health       prev=100        childAction=    dn=uni/tn-common        lcOwn=local     ownerKey=       name=common     descr=  status=created,modified monPolDn=uni/tn-common/monepg-default   modTs=2014-04-23T22:14:01.702+00:00     ownerTag=       uid=0   rn=tn-common    childAction=    component=fvTenant

2)

2014-04-25 00:38:08     status=created,modified domain=tenant   code=F1228      occur=1 subject=contract        severity=minor  descr=Contract default configuration failed due to filter-not-present   origSeverity=minor      rn=fault-F1228  childAction=    type=config     dn=uni/tn-common/oobbrc-default/fault-F1228     prevSeverity=minor      modTs=never     highestSeverity=minor   lc=raised       changeSet=      created=2014-04-23T22:24:37.274+00:00   ack=no  cause=configuration-failed      rule=vz-abrcp-configuration-failed      lastTransition=2014-04-23T22:26:57.046+00:00    dn=uni/tn-common        lcOwn=local     ownerKey=       name=common descr=  status=created,modified monPolDn=uni/tn-common/monepg-default   modTs=2014-04-23T22:14:01.702+00:00     ownerTag=       uid=0   rn=tn-common    childAction=    component=fvTenant

#### MSO DATA

You can see what each event looks like by going to $SPLUNK_HOME/etc/apps/TA_cisco-ACI/bin and executing collect_mso.py with Splunk Python interpreter. 
Example:
   /opt/splunk/bin/splunk cmd python collect_mso.py -mso policy

Each event contains data in the "Field=value" pair. Field names are case sensitive for the Cisco MSO API. Every event starts with the current_time field which is the machine's current time followed by mso_host (i.e. Hostname of MSO) and mso_api_endpoint (so one can distinguish below various endpoints data). The id field returned in the API call is unique for every event.

Below are two sample event records. The first one provides details for the policy named common_tenant_policy and the other one for the policy named mso_policy

1)

current_time=2020-06-19 16:10:42	mso_host=x.x.x.x	mso_api_endpoint=policyDetails	version=1	provider_epgRef=/schemas/5eccc36d2d0000623d59b228/templates/Template2/anps/common_tenant_AP/epgs/common_tenant_EPG_1	provider_addr=1.2.3.4	provider_l3Ref=	provider_tenantId=0000ffff0000000000000010	provider_externalEpgRef=	tenantId=0000ffff0000000000000010	id=5ed5f8242a1d00df1aabe01b	policySubtype=relay	name=common_tenant_policy	policyType=dhcp

2)

current_time=2020-06-19 16:10:42	mso_host=x.x.x.x	mso_api_endpoint=policyDetails provider_epgRef=/schemas/5eccc36d2d0000623d59b228/templates/Template2/anps/common_tenant_AP/epgs/common_tenant_EPG_1	provider_addr=10.0.1.11	provider_l3Ref=	provider_tenantId=0000ffff0000000000000010	provider_externalEpgRef=	tenantId=5ecca9982d0000453759b150	id=5eec91755c1d0065269c37c6	policySubtype=relay	name=mso_policy	policyType=dhcp


# DATA GENERATOR
This app is provided with sample data that can be used to generate dummy data. To simulate this sample data, first of all, download the Splunk Event generator, which is available at https://github.com/splunk/eventgen, & needs to be installed at $SPLUNK_HOME/etc/apps/. This app generates the dummy data for the ACI environment and populates the dashboards of the main app with the dummy data.

# Support

* This app is supported by Cisco Systems.
* Email support during weekday business hours. Please ask a question or send an email to aci-splunk-app@cisco.com
* Author: Cisco Systems
* Copyright (c) 2024 Cisco Systems, Inc

# Release Notes
* Version 5.1.0:
  * Added information about required APIC Roles on Setup Page
  * Added subtree fvIP for fvCEP class to get the source addr field
  * Added Support for Nexus Dashboard authentication along with MSO authentication

* Version 5.0.0:
  * Added Support for Multi-Site Orchestrator
  * Updated the Setup page

* Version 4.5.0:
  * Added support of Splunk 8.x
  * Made Add-on Python2 and Python3 compatible

* Version 4.4.0:
  * Fixed cloud vetting concerns

* Version 4.3.0:
  * Remote User-based Authentication
  * Certificate-based Authentication
  * Functionality to edit inputs.conf from Setup Page
  * CIM Mapping - Splunk CIM version supported - 4.13.0
  * Bug Fixes