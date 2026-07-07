# Carbon Black EDR Splunk App

Current Version: 2.2.0

## Overview

The VMware Carbon Black EDR App for Splunk lets administrators leverage the industry's leading EDR solution to detect and take action on endpoint activity directly from within Splunk.

### Dashboards

Builtin dashboards provide you with a quick health check on your Carbon Black EDR server, the status of your Carbon Black EDR deployment, and an overview of detected threats on your network. Eight example dashboards are distributed with this app; not all of these are populated with data, depending on what events are being forwarded to Splunk via the [Carbon Black Event Forwarder](https://developer.carbonblack.com/reference/enterprise-response/event-forwarder/).

- **Overview**: Provides a quick overview, including the number of sensors reporting alerts and the top feed and watchlist hits across the enterprise.
- **Binary Search**: Searches the Carbon Black EDR binary holdings via the binarysearch custom command.
- **Process Search**: Searches the processes that are tracked by Carbon Black EDR via the processsearch custom command.
- **Process Timeline**: Produces a simple timeline of events based on a Carbon Black EDR process GUID.
- **Sensor Search**: Searches endpoints that are tracked by Carbon Black EDR via the sensorsearch custom command.
- **Carbon Black EDR Endpoint Status**: Displays information about the total number of reported sensors, OS, and Carbon Black EDR agent version distribution across all endpoints.
- **Carbon Black EDR Network Overview**: Visualizes incoming and outgoing network connections that are recorded by Carbon Black EDR. This view is only populated if netconn events are forwarded via the Carbon Black Event Forwarder.
- **Carbon Black EDR Binary Status**: Displays information about attempts to execute banned processes, and new executables and shared libraries that are discovered by Carbon Black EDR.

### Custom Commands

You can use custom commands in your Splunk pipeline to access Splunk's visualization and searching capability on Carbon Black EDR data, without ingesting all of the raw endpoint data into Splunk.

- **sensorsearch**: Search for sensors by IP address or hostname.
- **processsearch**: Search for processes in your Carbon Black EDR server.
- **binarysearch**: Search for binaries in your Carbon Black EDR server.

### Adaptive Response Alert Actions

The Carbon Black EDR Splunk app currently includes three Adaptive Response Alert Actions that allow you to take action directly from the Splunk console. The actions occur as either a result of automated correlation searches or on an ad-hoc basis through the Splunk Enterprise Security Incident Review page.

- **Kill Process**: Kill a given process that is actively running on an endpoint that is running the Carbon Black EDR sensor. The process must be identified by a Carbon Black EDR event ID. Killing processes allow the security analyst to quickly respond to attackers who are using tools that cannot otherwise be banned by hash (for example, reusing a legitimate administrative tool for malicious purposes).
- **Ban MD5 Hash**: Ban a given MD5 hash from executing on any host that is running the Carbon Black EDR sensor. The MD5 hash can be specified by a custom hash field. This feature allows incident responders to quickly react to evolving threats by keeping attackers’ tools from executing while the threat is properly remediated and the attacker is expelled from the network. 
- **Isolate Sensor**: Isolate an endpoint from the network. The endpoint can be specified by a custom IP address field or a sensor ID that’s provided in Carbon Black EDR events in Splunk. Isolation is useful when malware is active on an endpoint. It lets you perform investigative tasks (for example, retrieving files or killing processes through Carbon Black Live Response) from your management console while preventing any connections to active command and control or exfiltration of sensitive data.

### Saved Searches

Included in this release are 58 saved searches to jump-start Threat Hunting from within the Splunk environment. These are all disabled by default. Some dashboards will throw an error for "Saved Search doesn't exist" if the search is not enabled. Simply enabling the stated saved search will enable the dashboard to work correctly. 

The list below are the primary dashboard searches.
1. ``CbResponse Alert Activity``
1. ``CbResponse New Binaries``

### Workflow Actions

This app includes workflow actions to provide additional context from Carbon Black EDR on events that originated from any product that pushes data to your Splunk server. These context menu items include the following:

- **Deep links**: Deep links into the Carbon Black EDR server for any event that originated from a Carbon Black EDR sensor. This allows you to access the Process Tree and other Carbon Black EDR data from a single link inside Splunk.
- **Process search by IP, MD5**: Search the Carbon Black EDR server for processes that are associated with a given IP address or MD5 hash from any event in Splunk.
- **Sensor info by IP**: Search the Carbon Black EDR server for detailed endpoint information that is associated with a given IP address from any event in Splunk.

## Requirements

This app requires a functional Carbon Black EDR server, version 5.1 or above, and Splunk version 6.4 or above. The app works with Carbon Black EDR clusters. The Carbon Black EDR Unified View (Federated) server is not currently supported.


## Getting Started

After the Carbon Black EDR app for Splunk is installed, you must configure it to connect to your Carbon Black EDR server by using the Carbon Black EDR REST API. For more information on the Carbon Black EDR REST API and how to generate an API key, see the [Carbon Black Developer Network](https://developer.carbonblack.com/reference/enterprise-response/).

The Carbon Black EDR app for Splunk uses a Carbon Black EDR API key to do the following:

1. Power the ``sensorsearch``, ``processsearch``, and ``binarysearch`` custom commands by performing searches via the Carbon Black EDR API.
2. Enable the **Endpoint Isolation** Adaptive Response Action by requesting endpoint isolation through the Carbon Black EDR API.
3. Enable the **Ban Hash** Adaptive Response Action by using the Carbon Black EDR API to add an MD5 hash to the list of banned hashes.
4. Enable the **Kill Process** Adaptive Response Action by using the Carbon Black EDR Live Response API to kill a process on a remote endpoint. Live Response must be enabled on the Carbon Black EDR server for this action to function; see the _VMware Carbon Black EDR User Guide_ for more information about Live Response.

To configure the Carbon Black EDR app for Splunk to connect to your Carbon Black EDR server:

1. Click the **Apps** dropdown next to the Splunk icon at the top of the Splunk dashboard.
1. Click the **Manage Apps** menu item.
1. Click the **Set Up** action to the right of the Carbon Black EDR app.
1. Retrieve an API key for a Global Administrator user on the Carbon Black EDR server. See the authentication instructions at the [Carbon Black Developer Network](https://developer.carbonblack.com/reference/enterprise-response/authentication).
1. Return to the Splunk configuration page and do the following:
    1. Paste the API token into the ``apikey`` field.
    1. Enter the URL for your Carbon Black EDR server instance in the ``URL`` field. For example, enter: ``https://cbserver.mycompany.com``.
1. Click *Setup* to save the new configuration.
 
 ______
**Note**: SSL validation is enabled by default. 

To disable SSL Validation, create ``$SPLUNK_HOME/etc/apps/DA-ESS-CbResponse/local/DA-ESS-CbResponse_Settings.conf`` with the following content:

```
[ssl_info]
ssl_verify=false
```
 ___

The Carbon Black EDR app for Splunk uses Splunk’s encrypted credential storage facility to securely store the API token for your Carbon Black EDR server.

To change the API key or Carbon Black EDR server URL after the Splunk app has been set up, visit the setup page at  ``https://<SPLUNK_SERVER>/en-US/app/DA-ESS-CbResponse/setup_page``.

## Using the VMware Carbon Black EDR App for Splunk

After the app is installed, a new icon showing the VMware Carbon Black EDR logo appears on the left-hand side of the Splunk front page. Clicking the logo brings you to the default dashboard of the Carbon Black EDR for the Splunk app. Additional dashboards include an overview of endpoint status, including a breakdown of OS and sensor versions, as well as data on the latest new binaries seen in the environment. 

The **Process**, **Binary**, and **Sensor Search** dashboards allow you to perform Carbon Black searches directly from within Splunk. These dashboards use the respective custom commands to perform the search through the REST API without ingesting the data into Splunk. The results are displayed on the same screen. You can also use Carbon Black search features using custom search commands.

Examples:
- ``processsearch query="process_name:cmd.exe"``
- ``binarysearch query="md5:fd3cee0bbc4e55838e65911ff19ef6f5"``
- ``sensorsearch query=”ip:172.22.5.141”`` 

### Using Custom Commands
The Splunk app includes three custom commands to perform searches on the Carbon Black datastore from Splunk: ``binarysearch``, ``processsearch``, and ``sensorsearch``. These three commands have corresponding views in the Carbon Black app: **Binary Search**, **Process Search**, and **Sensor Search**.

To use the custom commands in your Splunk searches, first make sure that you’re using the Carbon Black EDR context by invoking the search through the **Splunk > Search** menu in the Carbon Black EDR app. You can use any of the search commands by appending the Carbon Black EDR query as a “query” parameter. For example:

    | sensorsearch query=”ip:172.22.5.141” 

sends an API request to Carbon Black EDR to query for all sensors that have reported an IP address of 172.22.5.141. The result of this query can be piped through to other Splunk commands for aggregation, visualization, and correlation.

To update the base EDR index for macros and eventtypes, change `[edr_base_index]` in ``eventtypes.conf``.

### Using Saved Searches
Several example reports and saved searches are included in this app release. You can find a full list of these searches in **Settings > Searches, Reports, and Alerts** menu item from the Carbon Black EDR app. None of these are run or scheduled to run by default, and some will not return any data unless certain data types (netconns, procstarts, etc.) are forwarded via the Carbon Black Event Forwarder into Splunk.

## Using Adaptive Response Alert Actions
The Carbon Black EDR app for Splunk now integrates with Splunk’s Adaptive Response framework and provides three Adaptive Response Alert Actions:

- Isolate Endpoint
- Ban MD5 Hash
- Kill Process

Each of these Actions can be performed either on an ad-hoc basis on a notable event surfaced in Enterprise Security, or on an automated basis as part of a Splunk Correlation Search. In addition, the Isolate Endpoint and Ban MD5 Hash actions can be invoked based on search results from any Splunk search, as long as a field is present that provides an IP address (for Isolate Endpoint) or an MD5 hash (for Ban Hash). Currently, only events that are surfaced via the Carbon Black Event Forwarder can be used as input for the Kill Process alert action.

### Using Workflow Actions 
Workflow Actions allow you to pivot into Carbon Black searches from standardized fields.
The Carbon Black EDR app for Splunk includes Workflow Actions with context about events in any Splunk view, including Enterprise Security’s Notable Event table. 

To Perform a workflow action, drilldown into an event and click the **Event Actions** button.
The available workflow actions from this app are displayed. You can pivot directly from a field if a workflow action is available for that field.

The following Workflow Actions are included:

- **Sensor Information by IP**: find detailed information about a Carbon Black EDR sensor given an IP address field.
- **Binary Search by MD5 hash**: retrieve context around a binary that has a specific MD5 file hash.
- **Search for Processes contacting IP**: retrieve a list of processes from Carbon Black EDR that have made a connection to or received a connection from the given IP address.
- **Search for Processes related to MD5 hash**: retrieve a list of processes from Carbon Black EDR that have links to the given MD5 hash (a loaded module/DLL, the executable itself, a file write to an executable with the given MD5 hash).
- **Search for Processes contacting Domain**: retrieve a list of processes from Carbon Black EDR that have made a connection to or received a connection from the given domain name.
- **Search for Processes related to filename**: retrieve a list of processes from Carbon Black EDR that refer to the given filename (written/modified the file, etc.).

In addition, for events that were generated by Carbon Black EDR (forwarded into Splunk via the Carbon Black Event Forwarder), additional Workflow Actions provide deep links into the Carbon Black EDR console directly from the event in Splunk, where applicable. These deep links require the Carbon Black Event Forwarder to be configured to generate these links at event generation time (see the Carbon Black Event Forwarder configuration file for more details).

- Deep Link to target process's Process Analysis page
- Deep Link to parent process's Process Analysis page
- Deep Link to child process's Process Analysis page
- Deep Link to Binary Analysis page
- Deep Link to Sensor page

### Using Performance & Data Models
This app contains one data model, which represents Carbon Black alerts plus watchlist/feed hits. The data model ``CbR_Alert`` is generated by searching for Carbon Black EDR 
events with the query ``tag=alert``. This data model is accelerated by default.

In addition, the saved search ``CbResponse Alert Activity`` is scheduled to run once per day by default, but is disabled out-of-box.

## Diagnostics
The Carbon Black EDR App for Splunk writes its log files into the standard Splunk log directory. The following log files (at ``$SPLUNK_HOME/var/log/splunk``) are used by the App:

- ``da-ess-cbresponse.log``: main log file for common Carbon Black EDR helper functions, including the search Custom Commands
- ``isolate_modalert.log``: log file for the Isolate Endpoint Adaptive Response Action
- ``banhash_modalert.log``: log file for the Ban Hash Adaptive Response Action
- ``killprocess_modalert.log``: log file for the Kill Process Adaptive Response Action

## Getting Support
- View all API and integration offerings on the [Developer Network](https://developer.carbonblack.com/) along with reference documentation, video tutorials, and how-to guides.
- Use the [Developer Community Forum](https://community.carbonblack.com/community/resources/developer-relations) to discuss issues and get answers from other API developers in the VMware Carbon Black Community.
- Report bugs and change requests to [Carbon Black Support](http://carbonblack.com/resources/support/)

## Summary Indexing

- None 

## Data Model Acceleration

- None

## Report Acceleration

- None

## Eventgen

Event Generator is not included.

## Support Offered

* Support URL: [Carbon Black Support](http://carbonblack.com/resources/support/)

## Third-party software

- CBAPI
