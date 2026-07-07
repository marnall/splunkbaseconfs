
Gigamon Adaptive Response Application for Splunk


====================================================

### Overview

Splunk Adaptive Response helps organizations better combat advanced attacks through a unified defense by leveraging end-to-end context and automated responses to events. Advanced cyber adversaries are continuously leveraging new attack methods that span multiple domains, launching devastating attacks that often leave enterprises vulnerable. Despite advancements in security technologies, most solutions are not designed to work together out-of-the-box, making it challenging to coordinate a response. By leveraging adaptive security architecture, the Adaptive Response framework in Splunk Enterprise Security Suite provides end-to-end context and automated response across many of the world’s leading security technologies – enabling customers to quickly detect threats and execute response.

Gigamon Adaptive Response Application for Splunk provides Splunk administrators with Alert Actions to be taken on Gigamon Visibility nodes via GigaVUE® Fabric Manager (GigaVUE-FM). These actions can be bound to correlation searches on Splunk Enterprise Security for automated response or executed on an ad-hoc basis with Notable events. It leverages Splunk's Adaptive Response Framework and uses RESTful API to integrate with GigaVUE-FM® to perform response actions on Gigamon Visibility nodes.

### Requirement

*   Splunk Enterprise version 6.5 or later
*   Splunk Enterprise Security (ES) Suite
*   CIM version 4.8 or higher
*   GigaVUE Visibility Node running GigaVUE OS 5.0 or later
*   GigaVUE Fabric Manager (GigaVUE-FM) 5.0 or later

### Operational Flow

The overall onboarding and provisioning process includes several steps. This guide assumes that the customer has already a functional installation of Splunk Enterprise Security Suite (Splunk ES). The steps to follow are:

1.  Download and install the Gigamon Adaptive Response Application for Splunk
2.  Configure the Gigamon Adaptive Response Application for Splunk
3.  Bind Gigamon Adaptive Response actions to searches in Splunk ES

The next sections will guide you through each step.

### Download and install the Gigamon Adaptive Response Application for Splunk

Prior to installing the Gigamon Adaptive Response Application for Splunk, ensure that both Splunk Enterprise and Enterprise Security Suite are installed and configured properly. Also, verify the data ingestion method either Splunk Stream or other chosen method is configured properly and ensure data is being indexed on Splunk.

**It is highly recommended that you remove the previous version of the app before installing the current version.** You may refer to [Splunk docs](https://docs.splunk.com/Documentation/Splunk/latest/Admin/Managingappobjects#Uninstall_an_app_or_add-on) to remove an app.

Download and install the Gigamon Adaptive Response Application for Splunk from Splunkbase. Refer to the below guides for installing the app on a single server or distributed installation.

*   [https://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall](https://docs.splunk.com/Documentation/AddOns/released/Overview/Singleserverinstall)
*   [https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall](https://docs.splunk.com/Documentation/AddOns/released/Overview/Distributedinstall)

To download and install the app, you will need an active Splunk account. When you click on Install on Splunkbase, a login splash screen will request you to enter the Splunk account credentials and ask you to accept the Splunk terms to proceed. A restart of Splunk service would be required post installation of the application.

### Configure the Gigamon Adaptive Response Application for Splunk

Upon successful completion of installation, the Gigamon Adaptive Response Application for Splunk icon should be visible on the Splunk main page. Click on the icon to access the app. Since this is the first time we’re launching it, an App configuration page opens. Click on the "Continue to app setup page" and you should be presented with the Gigamon's End User License Agreement (EULA). Read the terms and acknowledge by checking the box in bottom of the page. By clicking Save you agree to be bound by EULA terms.

Upon acceptance of EULA, you would be navigated to the Action Setup page of Gigamon Adaptive Response Application. **First time users need to to save the GigaVUE-FM® credentials for alert actions in the GigaVUE Fabric Manager Credentials section under Configuration tab.** You may optionally check on Verbose to enable debug message logging. Click on Save to continue. This step needs to be repeated ONLY when the GigaVUE-FM® credentials are updated. Before proceeding ensure the GigaVUE-FM® instance is reachable from the Splunk instance.

### Defining Alert Actions

The Adaptive Response Application allows the Splunk administrators to place a PASS or a DROP rule in an existing byRule map. An action in the context of this application defines a set of maps present on a single node/cluster that would be updated with a single pass or drop rule. Each action is identified by a unique action identifier which would be tied up to the correlation searches in Splunk ES. Below are few actions for illustration purposes.

|Action Identifier|GigaVUE Fabric Manager IP|Cluster ID|FlowMap Alias|Response Action|
|--- |--- |--- |--- |--- |
|TestRule01|10.10.10.10|10.10.10.11|Splunk_Test_FlowMap1|drop|
|TestRule02|10.10.10.10|10.10.10.11|Splunk_Test_FlowMap2|pass|
|TestRule03|10.10.10.10|10.10.10.12|Splunk_Test_FlowMap3|drop|
|TestRule04|10.10.10.10|10.10.10.12|Splunk_Test_FlowMap4|pass|
|TestRule05|10.10.10.10|10.10.10.11|Splunk_Test_FlowMap1Splunk_Test_FlowMap2|pass|
|TestRule05|10.10.10.10|10.10.10.12|Splunk_Test_FlowMap3Splunk_Test_FlowMap4|drop| 
  

**NOTE:** While you can club multiple maps into a single action, these maps should be present on same cluster/node. To take an action on maps located on different clusters/nodes, you may define two different actions and club both the action identifiers in the alert actions on Splunk ES. Specifying multiple action identifiers on Splunk ES will be discussed in further sections.

#### To define a new action,

*   Go to Setup Actions tab found under the Response Actions menu
*   In the Action Setup page, enter the GigaVUE-FM® IP address and credentials
*   Click on Submit to connect to GigaVUE-FM® and load the cluster/node list
*   From the table displaying the cluster/nodes, select the cluster by clicking on it
*   From the table displaying the maps on the selected cluster/node, select the map(s) by clicking on them
*   Enter a unique ID for the Action Identifier and select the action to be tied up from the drop-down menu
*   Click on Add Action to add an entry into the actions database

You can continue to add more actions by repeating the above steps or choose to view the actions configured by navigating to the View Actions tab under the Response Actions menu.

#### To view the actions,

*   Go to View Actions tab found under the Response Actions menu
*   The Current Action List section will display all the actions that have been configured

#### To delete an action,

*   Go to View Actions tab found under the Response Actions menu
*   Select the action you wish to delete from the Current Action List
*   Under the Delete Actions, enter the Action Identifier and click on Delete Record
*   Review the current actions list to ensure the action is successfully deleted

**NOTE:** You will need to manually clean up action identifier entries from the Splunk ES correlation searches. The delete action would only remove entries from the actions database.

### Bind Gigamon Adaptive Response actions to searches in Splunk ES

Gigamon Adaptive Response actions can be bound to any correlation search that leverages Gigamon's IPFIX metadata as the source. To bind the alert action on Splunk ES follow the below instructions.

*   On the Splunk Enterprise Security menu bar, click Configure > Content Management
*   Click an existing correlation search, or create one by clicking Create New > Correlation Search
*   Scroll down to Adaptive Response Action, click Add New Response Action and select “Gigamon Adaptive Response Actions”
*   Enter the Action Identifier. You may specify more than one identifier by separating them with a comma
*   Select the Action Field from the drop-down list
*   Click Save to save all changes to the correlation search.

For more information on setting up adaptive response actions on Splunk ES, [click here](http://docs.splunk.com/Documentation/ES/latest/Admin/Setupadaptiveresponse)

#### Using the Action Field

The rules added to maps on the GigaVUE node by response actions can be made more specific by using the Action Field parameter. Below is the list of options available in the application.

*   Source IP address
    *   The source IP will be picked from the Splunk event and a rule will be added to the node to drop or send a copy of the specified traffic to the desired tool
    *   For instance, a client querying a malicious URL can be blocked or activity from the client can be monitored and analyzed.
*   Destination IP address
    *   The destination IP will be picked from the Splunk event and a rule will be added to the node to drop or send a copy of the specified traffic to the desired tool
    *   For instance, a C2 server identified can be blocked or activity from that server can be monitored and analyzed.
*   Destination service
    *   The destination IP + PORT will be picked from the Splunk event and a rule will be added to the node to drop or send a copy of the specified traffic to the desired tool
    *   For instance, a rogue DNS service identified can be blocked or activity from that server can be monitored and analyzed.
*   Flow/Transaction
    *   Source IP + Destination IP + Destination PORT will be picked from the Splunk event and a rule will be added to the node to drop or send a copy of the specified traffic to the desired tool
    *   For instance, a DNS tunneling attempt can be blocked or traffic can be sent to tool for further analysis

**Selecting the Action Field** NetFlow/IPFIX are unidirectional flow records which means you would see two flows for each session. To ensure actions are taken on appropriate action field, the app would use the source and destination port numbers to try and identify the actual source of the request and the destination responding back to it. For instance, if an alert action is triggered based on DNS response flow record and if the administrator has selected destination service as action_field, the response action would flip the source and destination information and take action on the DNS service (IP + Port) even though the actual IPFIX record will have DNS server information mentioned as source.

### Support

In case of issues, bugs or queries, drop us a mail to App.Splunk@gigamon.com with all the details and "Gigamon Adaptive Response Application for Splunk" in the subject.

### End User License Agreement

Installation and use of this app signifies acceptance of the [Gigamon End User License Agreement(EULA)](/static/app/TA-GigamonARForSplunk/html/Gigamon-EULA.pdf) inclusive of any future updates.

### Credits

This is an add-on powered by the Splunk Add-on Builder
