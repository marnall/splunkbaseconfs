# ABOUT THIS APP

The Cisco ACI App for Splunk Enterprise is used to build dashboards on indexed data provided by the "Cisco ACI Add-on for Splunk Enterprise" app.

This app delivers centralized, real-time visibility for applications and ACI infrastructures across the bare metal and virtualized environments.

# REQUIREMENTS

* Splunk version supported 9.2.x, 9.1.x and 9.0.x
* This main App requires "Cisco ACI Add-on for Splunk Enterprise" version 5.1.0

# Recommended System configuration

* Splunk search head system should have 16 GB of RAM and an octa-core CPU to run this app smoothly.


# Topology and Setting up Splunk Environment
  
  Install the main app (Cisco ACI App for Splunk Enterprise) and Add-on (Cisco ACI Add-on for Splunk Enterprise) on a single machine.
* Here both the app resides on a single machine.
* The main app uses the data collected by the Add-on and build dashboards on it.

# Installation of App

* This app can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Restart Splunk.
* Login to Splunk: http://<your_splunk_host:port>
* Open browser: http://<your_splunk_host:port>/en-US/debug/refresh. Click "Refresh"
* Open browser: http://<your_splunk_host:port>/en-US/_bump 
    (To pull all updated web resources from the server to the browser, to modify the cached items such as js, cookies, images etc..)
* Restart Splunk

* Note: 
  1) If a previous version of the App is already installed, remove the cisco-app-ACI folder from the Splunk app folder before the installation of a newer version or the user can upgrade the app from Splunk UI.
  2) If in case cleaned Splunk eventdata, please make sure to delete the files ending with _LastTransactionTime.txt from TA_cisco-ACI/bin/ folder.
         These files are saving timestamp to get only incremental data from APIC or MSO.

# Installation of Add-on
* This Add-on can be installed through UI using "Manage Apps" or extract zip file directly into /opt/splunk/etc/apps/ folder.
* Ref documentation provided by "Cisco ACI Add-on for Splunk Enterprise" for Configuration of Add-on

* Note: If a previous version of the Add-on is already installed, remove the TA_cisco-ACI folder from the Splunk app folder before installation of a newer version or the user can upgrade the app from Splunk UI.
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
  
  * (Optional) If you want to remove data from Splunk database, you can use the below Splunk CLI clean command to remove indexed data from an app before deleting the app.
    * $SPLUNK_HOME/bin/splunk clean eventdata -index <index_name>
  
  * Delete the app and its directory. The app and its directory are typically located in the folder$SPLUNK_HOME/etc/apps/<appname> or run the following command in the CLI:
    * $SPLUNK_HOME/bin/splunk remove app [appname] -auth <splunk username>:<splunk password> 
  
  * You may need to remove user-specific directories created for your app by deleting any files found here: $SPLUNK_HOME/bin/etc/users/*/<appname>

  * Restart the Splunk platform. You can navigate to Settings -> Server controls and click the restart button in Splunk web UI or use the following Splunk CLI command to restart Splunk:
    * $SPLUNK_HOME/bin/splunk restart

# TEST YOUR INSTALL

* Once the Add-on is configured to receive data from ACI, The main app dashboard can take some time before the data is populated in all panels. A good test to see that you are receiving all of the data is to run this search after several minutes:

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

You can also see $SPLUNK_HOME/var/log/splunk/splunkd.log file to check if any error has occurred.



# ABOUT THE DATA

#### APIC DATA

Below are two sample event records. The first one gives health detail for a tenant with the name "common" and the other one gives a fault detail for the same tenant.

1)

2014-04-25 00:38:07     dn=uni/tn-common/health status=created,modified updTs=2014-04-25T04:52:32.274+00:00     chng=0  cur=100 maxSev=cleared  modTs=never     twScore=100     rn=health       prev=100        childAction=    dn=uni/tn-common        lcOwn=local     ownerKey=       name=common     descr=  status=created,modified monPolDn=uni/tn-common/monepg-default   modTs=2014-04-23T22:14:01.702+00:00     ownerTag=       uid=0   rn=tn-common    childAction=    component=fvTenant

2)

2014-04-25 00:38:08     status=created,modified domain=tenant   code=F1228      occur=1 subject=contract        severity=minor  descr=Contract default configuration failed due to filter-not-present   origSeverity=minor      rn=fault-F1228  childAction=    type=config     dn=uni/tn-common/oobbrc-default/fault-F1228     prevSeverity=minor      modTs=never     highestSeverity=minor   lc=raised       changeSet=      created=2014-04-23T22:24:37.274+00:00   ack=no  cause=configuration-failed      rule=vz-abrcp-configuration-failed      lastTransition=2014-04-23T22:26:57.046+00:00    dn=uni/tn-common        lcOwn=local     ownerKey=       name=common descr=  status=created,modified monPolDn=uni/tn-common/monepg-default   modTs=2014-04-23T22:14:01.702+00:00     ownerTag=       uid=0   rn=tn-common    childAction=    component=fvTenant

#### MSO DATA

Below are two sample event records. The first one gives policy detail for a policy named common_tenant_policy and the other one for mso_policy.

1)

current_time=2020-06-19 16:10:42	mso_host=x.x.x.x	mso_api_endpoint=policyDetails	version=1	provider_epgRef=/schemas/5eccc36d2d0000623d59b228/templates/Template2/anps/common_tenant_AP/epgs/common_tenant_EPG_1	provider_addr=1.2.3.4	provider_l3Ref=	provider_tenantId=0000ffff0000000000000010	provider_externalEpgRef=	tenantId=0000ffff0000000000000010	id=5ed5f8242a1d00df1aabe01b	policySubtype=relay	name=common_tenant_policy	policyType=dhcp

2)

current_time=2020-06-19 16:10:42	mso_host=x.x.x.x	mso_api_endpoint=policyDetails	provider_epgRef=/schemas/5eccc36d2d0000623d59b228/templates/Template2/anps/common_tenant_AP/epgs/common_tenant_EPG_1	provider_addr=10.0.1.11	provider_l3Ref=	provider_tenantId=0000ffff0000000000000010	provider_externalEpgRef=	tenantId=5ecca9982d0000453759b150	id=5eec91755c1d0065269c37c6	policySubtype=relay	name=mso_policy	policyType=dhcp


# Data Model

This app stores the indexed data in accelerated datamodels and build dashboards by fetching data from datamodels. Below is the list of datamodels that have been created in the app.

* Auth - Maps authentication details from the ACI Environment.
* Health - Maps health and fault information for all the MOs of given classes.
* Fault - Maps to defects or faults present on APIC.
* Systems - Maps to general information for all the MOs of given classes.
* Counters - Maps to general information for all the MOs of given classes.
* Statistics - Maps to statistical data for all the MOs of given classes.
* Events - Maps to general information for all the MOs of class=eventrecord.

* If you want to improve the performance of dashboards, you must need to enable the acceleration of datamodel. Please follow the below steps:
  * Go to Settings -> Data Models
  * Filter with Cisco ACI App For Splunk Enterprise
  * In Action tab, Click on Edit and click Edit Acceleration
  * Check Acceleration checkbox and select the appropriate summary range and Save it
* Warning: Acceleration may increase storage and processing costs.

# Saved Searches

This app provides savedsearches that generate lookup files or send email alerts.

* savedsearches which generates lookup files
  * APICFabricLookup - generates APICNodeLookup.csv file
  * APICCEPLookup - generates APICVMLookup.csv file
  * MSO Sites Lookups - generates mso_site_details.csv file
* savedsearches which generates alerts
  * ACI Monitoring Threshold: Tenant Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: Tenant Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: Tenant Exceeds Max Threshold Limit
  * ACI Monitoring Threshold: EPG Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: EPG Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: EPG Exceeds Max Threshold Limit
  * ACI Monitoring Threshold: Contracts Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: Contracts Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: Contracts Exceeds Max Threshold Limit
  * ACI Monitoring Threshold: Filters Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: Filters Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: Filters Exceeds Max Threshold Limit
  * ACI Monitoring Threshold: BD Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: BD Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: BD Exceeds Max Threshold Limit
  * ACI Monitoring Threshold: L3Out Networks Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: L3Out Networks Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: L3Out Networks Exceeds Max Threshold Limit
  * ACI Monitoring Threshold: TCAM Percentage Utilized Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: TCAM Percentage Utilized Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: Egress Port Utilization for Leafs/Spines Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: Egress Port Utilization for Leafs/Spines Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: Ingress Port Utilization for Leafs/Spines Exceeds Warning Threshold Limit
  * ACI Monitoring Threshold: Ingress Port Utilization for Leafs/Spines Exceeds Critical Threshold Limit
  * ACI Monitoring Threshold: VLAN Pool Exceeds Max Thresh
  old Limit
  * ACI Monitoring Threshold: VLAN Pool Exceeds Critical Threshold Limit

# Additional Features

In addition to out-of-the-box reporting and analytics capabilities for your ACI environment, the app includes a set of pre-defined dashboards for specific user roles:

* Helpdesk admin: Enables Help desk operator to analyze various faults in the system and escalate them to tenant or fabric admin accordingly. He will have access to only "Home", "Authentication" and "Helpdesk" dashboards.

* Tenant admin:  Enables Tenant admin to analyze and drill down faults and health related issues to a particular tenant. He can drill down into Applications, EPGs, and VM endpoints to identify a single point of failure within the admin. He will have access to only "Home", "Authentication" and "Tenants" Dashboards.  

* Fabric admin: Enables Fabric Admin to analyze physical network related issues. It gives visibility into fabric components of networks e.g. leaf, spine and it's physical components like chassis, ports, fan tray, line card, etc.

* Tenant user: Enables Tenant User to manage a specific tenant and all of its components like Application, EPGs, and VMs. To create a Tenant user for tenant "ABC", follow the steps given below.

1) Create a role with the name "tenant_ABC". In search criteria put "dn=uni/tn-ABC/*".
2) Create a new user with the name user-ABC and apply the role of "tenant_ABC" to this user.
3) Edit the permission of Tenant Dashboard to provide read access to a user with the role "tenant_ABC".

* vmware admin: This app has been integrated with the Splunk App for VMware to get the VM details of your datacenter as a client endpoint of APIC. A separate dashboard is provided which can be accessed by splunk_vmware_admin and splunk_vmware_user. Both of these roles are configured with the Splunk App for VMware. You can get a VMware app at https://apps.splunk.com/app/725/ and its documentation https://docs.splunk.com/Documentation/VMW/3.0.1/Install/SplunkforVMwareArchitecture.

The app also includes a set of MSO dashboards for specific use cases:

# New Dashboards

* Sites: Information about sites associated with MSO and the fault count of various severity levels. Drill-downs are provided in Site Information, Site Health graph, and panels consisting of fault counts, so users can get a detailed view of the same.

* Schemas: Information about schemas configured with MSO. Drill down into No. of Schemas Associated With MSO single pane visualization will show schema details, drill-down on Application Profiles, Bridge Domain, External EPGs, and VRF single pane visualization to get insights about particular health and fault details and drill-down on contracts will show contracts health details.

* Tenants: Graphical representation of tenants associated with sites, schemas, and users. Drill down on table showing Tenant Details for a particular site will re-direct to Tenant Details dashboard giving more description about the selected tenant. 

* Users: Information about MSO users and their roles. More details about user and roles are given by drill down on the Users and Roles panel.

* Policy: Information about policies configured in MSO. Drill down on Policy SubType Breakdown panel will show details of specific subtype.

All the MSO dashboards have Audit Logs panel showing Audit Logs of a particular type, for example, schemas dashboard have audit logs only of type schema.

# Troubleshooting

* If any warning displayed in dashboards of the app stating excessive memory usage of mvexpand command like: `output will be truncated at xxx results due to excessive memory usage...` , user can manually increase the memory limit in limits.conf
* Default value of max_mem_usage_mb parameter is 500 MB. to increase the limit follow the below steps.
  * create limits.conf file under $SPLUNK_HOME/etc/apps/cisco-app-ACI/local
  * Add below stanza:
    [mvexpand]
    max_mem_usage_mb = <non-negative integer in MB>


# The list of open source components used in developing the App
* Waypoints and prettify 
	Splunk Web Framework Toolkit - Version 2.0
	Built by Splunk.
	https://splunkbase.splunk.com/app/1613/

# Support

* This app is supported by Cisco Systems.
* Email support during weekday business hours. Please ask a question or send an email to aci-splunk-app@cisco.com
* Author: Cisco Systems
* Copyright (c) 2024 Cisco Systems, Inc

# Release Notes
* Version 5.1.0:
  * Removed information about APIC Roles from all dashboards.
  * Updated setup guide
  * Bug Fixes

* Version 5.0.0:
  * Added MSO Overview, Sites, Schemas, Tenants, Users, and Policy Dashboards for Multi-Site Orchestrator.
  * Updated setup guide  

* Version 4.4.0:
  * Updated setup guide
  * Added support of Splunk 8.x

* Version 4.3.0:
  * Added 3 Dashboards of Cloud APIC
  * Changed savedsearches - APICFabricLookup, APICCEPLookup
  * Bug Fixes