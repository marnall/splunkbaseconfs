Cherwell Add-on For Splunk
==============================

This is an Add-on powered by the Splunk Add-on Builder.

Overview
------------------------------
Cherwell Add-on for Splunk is an integration module of Cherwell with Splunk. Basically This Add-on serves two purposes. One is data collection via REST API and other is Custom Alert Action feature with Splunk. Additionally, This Add-on provides Bi-directional Integration and Incident Status synchronization between Splunk ITSI and Cherwell Service Management (CSM).

* Author - Cherwell
* Version - 1.0.1
* Build - 1
* Creates Index - False
* Uses Source type - cherwell:bo:<business_object_name_for_which_data_is_collected>
* Uses KV Store - True. This Add-on uses Splunk KV Store for checkpoint mechanism
* Uses Cherwell Rest API version 9.4.0 to collect the data
* Compatible with:
    - Splunk Enterprise version: 6.6.x, 7.0.x and 7.1.x
    - Splunk ITSI version: 3.1.2 onwards.
    - OS: Platform independent
    - Cherwell API version: 9.4.0 onwards


Pre-requisite
------------------------------

In order to setup this Add-on to make REST API calls to Cherwell Server and create Incidents as part of Custom Alert Action, User/Cherwell-Admin first needs to create splunk service account on Cherwell CMDB and generate client-id(key) for the same user.
This user credentials and client-id will be used in next step of Add-on setup.

* Also, User/Cherwell-Admin needs to download and install the Splunk Integartion mApp available on mApp Exchange [here](https://www.cherwell.com/mapp-exchange/cherwell-software/m/mapps/1635)
* The Splunk Cherwell Integration guide available [here](https://www.cherwell.com/cfs-filesystemfile/__key/cherwell-mapp-files/a757c8ec_2D00_6489_2D00_48e0_2D00_bf86_2D00_65e3ac9f6317-doco/Cherwell-Splunk-mApp-Installation-Instructions.pdf) gives more information with screenshots about Splunk Service account setup on Cherwell Service Manager instance



Installation
------------------------------
This Add-on is supported on all the tiers of distributed Splunk platform deployment and also on standalone Splunk instance. Below table provides the reference for installing the Add-on on distributed Splunk deployment:

| Splunk instance type | Supported | Required | Comments |
|---|---|---|---|
|Search Heads | Yes | Yes | This Add-on is required on Search Heads as it contains search time extractions. This Add-on also contains alert actions. To use these actions user need to configure the Add-on on Search Head. |
| Indexers | Yes | No | All parsing will be done on heavy forwarder only.|
| Heavy Forwarders | Yes | Yes | This Add-on supports only heavy forwarder for data collection. |

Follow the link mentioned below to install the Add-on based on your deployment:

* [Single-instance Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Singleserverinstall)
* [Distributed Splunk Enterprise](https://docs.splunk.com/Documentation/AddOns/latest/Overview/Distributedinstall)
* [Splunk Cloud](https://docs.splunk.com/Documentation/AddOns/latest/Overview/SplunkCloudinstall)


Setup
------------------------------
Once the installation of the Add-on is done successfully, follow the steps mentioned below to start data collection.

#### Configure Accounts
Follow the steps mentioned below to configure account:

* Login to Splunk Web UI.
* Go to the **Configuration** page of the Add-on by clicking on the Add-on on name from the left navigation panel on the home page.
* Click the **Configuration** menu and in the **Cherwell Account** tab click Add.
* Fill the appropriate details in the dialog. Refer the table below to fill in the details:

  | Input Name | Required | Description |
  |---|---|---|
  | Name | Yes | Unique name for the Cherwell Account. This box will not accept the space in name |
  | IP Address/Host Name  | Yes | IP Address/Host Name of the Cherwell Instance  |
  | Username | Yes | Username of the Cherwell Instance |
  | Password | Yes | Password for the provided Username |
  | Client ID | Yes | Client ID for the provided Cherwell Instance, Username and Password. You can get this from your Cherwell Admin |

**Note:** The Add-on should be configured using credentials of a Splunk service account created on the Cherwell server.


#### Configure Inputs
Follow the steps mentioned below to configure the inputs:

* Login to Splunk Web UI.
* Go to the **Inputs** page of the Add-on by clicking on the the Add-on name from the left navigation panel on the home page and thereafter clicking the **Inputs** menu.
* The Add-on provides 5 pre-configured inputs: change\_request, configuration\_item, incident, problem, and task to collect data for "Change Request", "Configuration Item", "Incident", "Problem", and "Task" business objects of Cherwell Instance. However, to start collecting the data for these inputs, follow the below mentioned steps:
    * Edit the input by clicking on **Action --> Edit**.
    * Select the value for **Cherwell Account** from the drop-down. This value is nothing but the name of the account that you have configured in the **Configuration** page. Data for the business object will be collected using that account details.
    * Edit any other values for the input if desired (for ex: interval) and click **Update**.
    * Once the details are saved,  enable the data input by clicking on **Action --> Enable** .
    * Repeat the above mentioned steps for all the inputs for which you wish to collect the data.
* You can also create new custom input configurations. To do so click the **Inputs** menu and click **Create New Input**. Fill in the appropriate details in the dialog. Refer the table below to fill in the details:

  | Input Name | Required | Description |
  |---|---|---|
  | Name | Yes | Unique name for the data input |
  | Business Object Name | Yes | Name or display name of the business object as in Cherwell |
  | Since Value | No | Date from which the data should be collected in  **%m/%d/%Y %I:%M:%S %p** format. The date should be provided according to the Cherwell instance time zone. Defaults to 01/01/2017 12:00:00 AM |
  | Cherwell Account | Yes | Name of account(from the ones configured in configuration page) using which data should be collected |
  | Interval | Yes | Interval in seconds or a valid cron schedule at which the data should be collected |
  | Index | Yes | Index in which the data should be collected. Defaults to default index |

### Data collection over secure network connection
Please note that This Add-on supports HTTPS connection and SSL check for communication between Splunk and Cherwell out of the box. To collect data through secure network channels (with certificate checks), you first need to get the required certs for the successful SSL verification with your Cherwell Instance. You can get it from your Security Admin\/Cherwell Admin. Alternatively you can follow below steps to get the  required Cert yourself. 

* **Download certificate using Firefox**
    - Copy the URL of Cherwell and paste it to your browser.
    - Click **View Page Info > Security > View Certificate > Details**
    - Click on the root certificate.
    - Export it as a **PEM** file.
Once you get the Cert, you need to copy the content of the PEM file into: $SPLUNK_HOME/etc/apps/TA-cherwell/bin/ta\_cherwell/requests/cacert.pem.

After following above steps, you need to configure Cherwell Account from the UI as mentioned in the Configure Accounts section.

### Data collection over insecure network connection
 If you want to collect the data through unencrypted communication (without certificate checks) you must disable the SSL check flag in ta\_cherwell\_account.conf.

Follow these steps to disable the SSL check flag:

* Create local folder if it is not present under TA-cherwell folder.
* Create/Update the ta\_cherwell\_account.conf and add below stanza to set the data collection over HTTP without using certificate checks.
```  
[<stanza_name>]
verify_ssl = False
url_scheme = http
```
* Restart the Splunk
* Login to Splunk WEB UI.
* Go to the **Configuration** page of the app, by clicking the Add-on on  name from the left navigation panel on the home page.
* Click the **Configuration** menu and click on edit button to edit the same stanza which configured from the backend to store the other information like hostname/IP, password and clientID.
* Save the configuration.

CIM Compatibility
------------------------------

The data collected for Incident, Task, Change Request and Problem has been normalized according to Splunk CIM mapping standard and is compatible with *Ticket Management* CIM data model.

Alert Action
------------------------------
## Custom Alert Action with Core Splunk using Alerts
The Splunk Add-on For Cherwell supports automatic incident creation action with scheduled savedsearch.

* **Create a Cherwell incident using a custom alert action**
  - Write a search string for your alert.
  - Click **Save As --> Alert**.
  - Fill out the Alert form. Give your alert a unique name and indicate whether the alert is a real-time alert or a scheduled alert. See [Getting started with Alerts](https://docs.splunk.com/Documentation/Splunk/7.1.2/Alert/Aboutalert) in the Alerting Manual. 
  - Under Trigger Actions, click **Add Actions**.
  - From the list, select **Create an Incident in Cherwell** to create an Incident on Cherwell Instance and it will open a form.
  - Enter values for the specified fields for your Cherwell Incident.
  - Click **Save**.
  
You can search the businessObject created by the **Create an Incident in Cherwell** custom alert. You can use **index=<index_name> sourcetype="cherwell:alerts:response"** search.
To change the index for the **Create an Incident in Cherwell** custom alert response, follow below steps:
  
  - Create/Update local alert_actions.conf in the local folder under TA-cherwell folder.
  - Add below property under **create_cherwell_incident** stanza in the conf file.
    
```
[create_cherwell_incident]
param.index_name = <index_name>
``` 
  - Restart Splunk

## Custom Alert Action with ITSI using Notable Event Action
The Custom alert action feature, when used with Splunk ITSI app will provide two fold advantage of this integration.This Add-on not only creates Incident and attaches Incident Id with Notable Event group as a Ticket, but it will also enable both ITSI analyst and Cherwell Admin to update status of Incident on any side and get it reflected on the other instance. This additional feature of syncing Notable Event status sync with Cherwell Incident is achieved by additional Alert Action called ** Update Cherwell Incident Status **. You can use ITSI notable event actions dropdown to perform both the alert actions. 

* **Create an incident using ITSI Notable event action**
     - On Notable Events Review dashboard within ITSI app, Click on Notable event group for which you want to create a Cherwell Incident.
     - Click on **Actions --> Create an Incident in Cherwell** and it will open a form.
     - Enter values for the specified fields for your Cherwell Incident.
     - Click **Done**.


   Some Important points to consider for **Create an Incident in Cherwell** Alert action

     - Once this alert action is executed on Notable Event group, user should see the created incident incident under "All Tickets" when selects that Notable event Group again. Clicking on the Ticket Id (Cherwell Incident Id) would take user to the corresponding Incident page on Cherwell Client. 
     - When using this Alert action as Automated Alert Action with Notable Event Aggregation Policy, some extra care needs to be taken. If the Alert Action rule would be configured to trigger this action for all the events in group, This Alert action will create as many Incidents as many notable events generated in that Notable Event Group.
     - Though it is not the best practice to attach multiple tickets with Notable event, it is still subjected to human error. However this alert action feature takes care of a scenario where multiple Incidents are attached with the same Notable event group (see more  on this in next section)

* **Update an incident status using ITSI Notable event action**
     - On Notable Events Review dashboard within ITSI app, Click on Notable event group for which you want to create a Cherwell Incident.
     - Click on **Actions --> Update Cherwell Incident Status**.
     - Select the appropriate **Cherwell Account** from the dropdown.
     - Click **Done**.

  Some Important points to consider for **Update Cherwell Incident Status** Alert action
  
     - Please note that Update Cherwell Incident Status Alert Action must be used with ITSI Notable Event group only.This alert action is not supported with any other Application and also not with core Splunk (custom alert using savedsearch).
     - This alert action will help to **synchronize only the status of Notable event group from ITSI to Splunk**. No other properties will be synchronized between Splunk ITSI and Cherwell.
     - Once the status of any Notable event group changed to "Closed" and updated on Cherwell side, changing Notable event group status to New or any other status would not reflect the status update on cherwell as Cherwell CSm supports only "Reopened" status of Closed Incident.
     - When executed on Notable event group that has multiple incidents attached with it, This Alert Action will change the status of all the attached Incidents on Cherwell Instance.



Refer the table below for the alert Action form Inputs.

* **Create an Incident in Cherwell**

| Parameter | Required | Description |
|---|---|---|
| Cherwell Account | Yes | Select the Cherwell Account through action needs be performed. |
| Short Description | Yes | Provide the short description\/Title for the Incident. |
| Description | Yes | Detailed description for the incident. |
| Priority | Yes | Select Priority from the dropdown for the incident. |
| Splunk URL | No | Provide Splunk URL to navigate from Cherwell to Splunk. |

**Note :** The purpose for providing Splunk URL optional field above is that Splunk user may find it useful sometime to attach Splunk dashboard/report/GlassTable link to the Cherwell Incident. Providing Splunk URL will create a clickable link on Cherwell Incident Page on Cherwell Instance clicking on which Cherwell user can see the attached dashboard/report/GlassTable.

* **Update Cherwell Incident Status**

| Parameter | Required | Description |
|---|---|---|
| Cherwell Account | Yes | Select the Cherwell Account on which you want to perform action.

The table below displays the mapping of ITSI Notable event status and Cherwell Incident

| ITSI Notable Event Status | Cherwell Incident Status |
|---|---|
| 0-Unassigned | New |
| 1-New | New |
| 2-InProgress | IN Progress | 
| 3-Pending | Pending |
| 4-Resolved | Resolved |
| 5-Closed | Closed |

Troubleshooting
------------------------------
* **Authentication Failure**: Verify that Cherwell instance is reachable from the Splunk HF where you have configured the Add-on. Make sure all the provided details are correct.
* **Not Able To Collect Data**: Verify that the configured "User" has all the required permissions to access Cherwell REST API. For more details you can either look into *$SPLUNK_HOME/var/log/splunk/ta\_cherwell\_cherwell.log* file or can execute `index=\_internal source="*ta_cherwell_cherwell.log" Error` query in Splunk.
* **Missing Records**: This Add-on queries the Cherwell instance based on the last modified time of the record, therefore you will be required to provide the value of **"Since Value"** parameter accordingly. Also, verify that the provided value is according to the Cherwell instance time zone.
* **Checkpoint**: At any point in time to know the state of the checkpoint, hit `https://<splunk_instance_ip_or_hostname>:8089/servicesNS/nobody/TA-cherwell/storage/collections/data/TA\_cherwell\_checkpointer` link. To reset the checkpoint, execute `$SPLUNK_HOME/bin/splunk clean kvstore --app TA-cherwell --collection TA_cherwell_checkpointer` command in the terminal on HF. This will reset checkpoint for all the configured data inputs. To delete checkpoint for particular input user can use [KV Store REST API](https://docs.splunk.com/Documentation/Splunk/7.1.2/RESTREF/RESTkvstore).
* **Not Able To Perform Create an Incident in Cherwell Alert Action**: For more details you can either look into *$SPLUNK_HOME/var/log/splunk/create\_cherwell\_incident\_modalert.log*is  file or can execute `index=internal source="*create_cherwell_incident_modalert.log"` query in Splunk.
* **Not Able To Perform Update Cherwell Incident Status Alert Action**: For more details you can either look into *$SPLUNK_HOME/var/log/splunk/update\_cherwell\_incident\_status\_modalert.log* file or can execute `index=_internal source="*update_cherwell_incident_status_modalert.log"` query in Splunk.

Known Limitations 
------------------------------
* Current version of Cherwell API doesn't honor  daylight saving changes in  every possible time fields, because of that during Daylight Savings, Splunk events will get timestamp of 1 hour later than the actual occurrence of event on Cherwell instance. This issue  should be fixed in next release and document will be updated accordingly.




Support 
------------------------------

* Is this Add-on supported ? : Yes
* Support Email : integrations@cherwell.com