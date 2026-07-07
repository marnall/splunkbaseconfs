## Template Table of Contents

### OVERVIEW

- About the WALLIX Bastion
- Release notes
- Support and resources

### INSTALLATION AND CONFIGURATION

- Hardware and software requirements
- Installation steps
- Deploy to single server instance
- Deploy to distributed deployment
- Deploy to distributed deployment with Search Head Pooling
- Deploy to distributed deployment with Search Head Clustering
- Deploy to Splunk Cloud 
- Configure WALLIX Bastion

### USER GUIDE

- Data types
- Lookups

---
### OVERVIEW

#### About the WALLIX Bastion

| Author | WALLIX |
| --- | --- |
| App Version | 1.0.3 |
| Vendor Products | WALLIX Bastion |
| Has index-time operations | false |
| Create an index | false |
| Implements summarization | false |

The WALLIX Bastion allows a Splunk® Enterprise administrator to help with analytics and security within your network.

##### Scripts and binaries

Include a list of scripts and binaries that exist in the add-on and the purpose of each.

#### Release notes

##### About this release

Version <1.0.3> of the WALLIX Bastion is compatible with:

| Splunk Enterprise versions | 6.6.1 |
| --- | --- |
| CIM |  |
| Platforms |  |
| Vendor Products |  |
| Lookup file changes |  |

##### New features

WALLIX Bastion includes the following new features:

- <new features>
- <new features>


## INSTALLATION AND CONFIGURATION

####Exporting the Bastion logs

To export the Bastion logs into Splunk you need to go to System/SIEM_Integration in the GUI of the Bastion,
then add the ip address of the Splunk instance, and specify the tcp port 2242.
The logs will soon be available in the Splunk instance under the sourcetype: "WB:syslog".

####Parsing of the Bastion's logs

The logs af the Bastion are already parsed for you in the Splunk instance. Here is a list of all the fields:
WB_Account      the target account
WB_Action	type of action in the Bastion's GUI
WB_Client_Ip	the ip adress of the machine connecting to the Bastion
WB_Device       the name of the target
WB_Event	type of event triggered (Audit, SSH, RDP...)
WB_Infos	additional information in the log
WB_Service	Which service is in use (ssh, rdp)
WB_Session_Id	the session id of the primary account
WB_Status	the status of connection (success, failure)
WB_Target_Ip	the ip adress of the distant machine
WB_Type		the type of event triggered (ex: SESION_ESTABLISHED_SUCCESSFULLY)
WB_User         the primary account

####Dashboards

The WALLIX Bastion add-on comes with 3 natively integrated dashboards:
WALLIX Bastion Connections Dashboard ---- Provides general information about the Bastion
Bastion Target Trail ---- Provides Information about a specific target
Bastion User Trail ---- Provides information about a specific user

####API calls

The WALLIX Bastion add-on comes with an alert action that can call the Bastion's API to terminate a session.
It is called "kill_session" and requires two parameters to work: the session id and the reason.
In order to make the alert action work you first have to go to the Configuration tab situated in the add-on and
inquire both the Bastion's Ip adress and its API key that can be generated in the GUI.
The alert action is now ready to be used.

# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-WALLIX_Bastion/bin/ta_wallix_bastion/markupsafe/_speedups.so: this file does not require any source code
# Binary File Declaration
/opt/splunk/var/data/tabuilder/package/TA-WALLIX_Bastion/bin/ta_wallix_bastion/markupsafe/_speedups.so: this file does not require any source code
