[comment]: # "Auto-generated SOAR connector documentation"
# ThreatQ

Publisher: ThreatQuotient  
Connector Version: 2.4.0  
Product Vendor: ThreatQuotient  
Product Name: ThreatQ  
Product Version Supported (regex): "4.\*"  
Minimum Product Version: 6.1.1  

Integrates a variety of ThreatQ services into Splunk SOAR

[comment]: # " File: README.md"
[comment]: # ""
[comment]: # "    ThreatQuotient Proprietary and Confidential"
[comment]: # "    Copyright (c) 2016-2024 ThreatQuotient, Inc."
[comment]: # ""
[comment]: # "    NOTICE: All information contained herein, is, and remains the property of ThreatQuotient, Inc."
[comment]: # "    The intellectual and technical concepts contained herein are proprietary to ThreatQuotient, Inc."
[comment]: # "    and its suppliers and may be covered by U.S. and Foreign Patents, patents in process, and are"
[comment]: # "    protected by trade secret or copyright law."
[comment]: # ""
[comment]: # "    Dissemination of this information or reproduction of this material is strictly forbidden unless prior"
[comment]: # "    written permission is obtained from ThreatQuotient, Inc."
[comment]: # ""
[comment]: # "    Licensed under the Apache License, Version 2.0 (the 'License');"
[comment]: # "    you may not use this file except in compliance with the License."
[comment]: # "    You may obtain a copy of the License at"
[comment]: # ""
[comment]: # "        http://www.apache.org/licenses/LICENSE-2.0"
[comment]: # ""
[comment]: # "    Unless required by applicable law or agreed to in writing, software distributed under"
[comment]: # "    the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,"
[comment]: # "    either express or implied. See the License for the specific language governing permissions"
[comment]: # "    and limitations under the License."
[comment]: # ""
# <span id="Splunk_SOAR_App_0"></span> Splunk SOAR App

## <span id="Introduction_2"></span> Introduction

The Splunk SOAR App for ThreatQ allows a user to execute a variety of actions on ThreatQ from a
Phantom playbook.  
With ThreatQ as a single source of truth for Threat Intelligence, you will be able to accurately
triage a sighting, and ultimately, make a quick decision.  
This will allow your analysts to focus on what’s important to their organization, instead of getting
inundated with sightings of non-malicious indicators.  
The goal being, to increase your response time and improve your ROI.

## <span id="Installation_9"></span> Installation

This section will describe how you can install the app into your Phantom instance

**WARNING** : This release (v2.x) has fundamentally changed how the App operates!  
If you are upgrading from v1.x, please refer to the
`     App Instructions -> Upgrading from 1.x to 2.x    ` section!

1.  Download the Splunk SOAR App (tar.gz) for ThreatQ via any of these methods:
    -   Marketplace
    -   Download Center
    -   Splunkbase
2.  Login to your Phantom instance
3.  In your navigation dropdown, select `      Apps     `
4.  Click on the `      Install App     ` button at the top right of your Apps page
5.  Select the Splunk SOAR App for ThreatQ tar.gz file

## <span id="Configuration_26"></span> Configuration

Once the app is installed, you will see a ThreatQ logo on your Apps page. If you do not, you can
search for `     ThreatQ    ` in the search bar

1.  Next to the ThreatQ logo, click on the `      Configure New Asset     ` button
2.  Fill out the following information in the `      Asset Info     ` tab, and save:
    -   **Asset name** : threatq
    -   **Asset description** : Integration with the ThreatQ Threat Intelligence Platform
    -   **Product vendor** : ThreatQuotient
    -   **Product name** : ThreatQ
3.  Fill out the following information in the `      Asset Settings     ` tab, and save:
    -   **Server IP/Hostname** : Enter the hostname or IP address for your ThreatQ instance
    -   **Client ID** : Enter your API Credentials found under your `        My Account       ` page
        in ThreatQ
    -   **Username** : Enter your username to authenticate with ThreatQ
    -   **Password** : Enter your password to authenticate with ThreatQ
    -   **Trust SSL Certificate?** : Check this box if you want to trust the ThreatQ certificate
        (default: checked)
4.  Click the `      Test Connectivity     ` button after saving to test your connection information
    -   If this test fails, verify your Phantom instance has access to your ThreatQ instance, as
        well as make sure your credentials are correct
5.  The ThreatQ App should now be configurable within a playbook!

## <span id="App_Actions_46"></span> App Actions

The following actions come out of the box with the Splunk SOAR App for ThreatQ

### <span id="Query_Indicators_50"></span> Query Indicators

**Name:** query_indicators

**Description:** Query a list of indicators against ThreatQ

**Parameters:**

-   indicator_list: A list of indicator values to query

### <span id="Create_Indicators_59"></span> Create Indicators

**Name:** create_indicators

**Description:** Create indicators in ThreatQ

**Parameters:**

-   indicator_list: A list of indicators to add

**Formatting:**  
See *Details \> Formatting an Indicator List*

### <span id="Create_Task_71"></span> Create Task

**Name:** create_task

**Description:** Create a task in ThreatQ

**Parameters:**

-   task_name: The name of the task to create
-   assigned_to: The email or username of a user within ThreatQ to assign the task to
-   task_status: The task status in ThreatQ
-   task_priority: The task priority in ThreatQ
-   task_description: The description of the task
-   indicator_list: A list of indicators to relate to the task

**Formatting:**  
See *Details \> Formatting an Indicator List*

### <span id="Create_Event_88"></span> Create Event

**Name:** create_event

**Description:** Creates an event in ThreatQ, based on the container metadata in Phantom

**Parameters:**

-   event_type: The type of event to create in ThreatQ
-   indicator_list: A list of indicators to relate to the event

**Formatting:**  
See *Details \> Formatting an Indicator List*

### <span id="Upload_Spearphish_101"></span> Upload Spearphish

**Name:** upload_spearphish

**Description:** Creates a spearphish event in ThreatQ, based on a spearphish email in the Phantom
vault

**Parameters:**

-   vault_id: The ID of an email file in your Phantom vault
-   indicator_status: The indicator status for any parsed indicators from the spearphish

### <span id="Upload_File_111"></span> Upload File

**Name:** upload_file

**Description:** Creates a file (attachment) in ThreatQ

**Parameters:**

-   vault_id: The ID of the file in your Phantom vault
-   parse_for_indicators: Whether or not to parse the file for indicators
-   default_indicator_status: The indicator status for any parsed indicators from the file

### <span id="Start_Investigation_122"></span> Start Investigation

**Name:** start_investigation

**Description:** Start an investigation within ThreatQ

**Parameters:**

-   investigation_name: The name of the investigation to create in ThreatQ
-   investigation_priority: The priority of the investigation in ThreatQ
-   investigation_description: The description of the investigation in ThreatQ
-   investigation_visibility: Whether the investigation is public or private
-   indicator_list: A list of indicators to relate to the investigation

**Formatting:**  
See *Details \> Formatting an Indicator List*

### <span id="Create_Adversaries_138"></span> Create Adversaries

**Name:** create_adversaries

**Description:** Create adversaries in ThreatQ

**Parameters:**

-   adversary_list: A list of adversary names to create in ThreatQ

### <span id="Create_Custom_Objects_147"></span> Create Custom Objects

**Name:** create_custom_objects

**Description:** Creates custom objects in ThreatQ

**Parameters:**

-   object_list: A list of custom object values in ThreatQ
-   object_type: The type of object that the object list specifies

### <span id="Add_Attribute_157"></span> Add Attribute

**Name:** add_attribute

**Description:** Adds an attribute to a list of custom objects

**Parameters:**

-   object_list: A list of custom object values in ThreatQ
-   object_type: The type of object that the object list specifies
-   attribute_name: The name for the attribute to add
-   attribute_value: The value for the attribute to add

### <span id="Set_Indicator_Status_169"></span> Set Indicator Status

**Name:** set_indicator_status

**Description:** Sets the status of an indicator in ThreatQ

**Parameters:**

-   indicator_list: A list of indicators
-   indicator_status: The status to give to the list of indicators

**Formatting:**  
See *Details \> Formatting an Indicator List*

## <span id="App_Instructions_182"></span> App Instructions

### <span id="Formatting_an_Indicator_List_184"></span> Formatting an Indicator List

You can pass a list of indicators to action in few different ways. Each being parsed, slightly
differently, but with similar outcomes

-   If only values are specified, the integration will attempt to “detect” the indicator types and
    upload the known values (i.e. `      1.1.1.1, badurl.com     ` ) The following indicator types are supported by this method:
  - MD5
  - SHA-1
  - SHA-256
  - SHA-384
  - SHA-512
  - CIDR Block
  - URL
  - FQDN
  - Email Address
  - IP Address
  - CVE
  - Filename
  - File Path
-   You can specify indicators on multiple lines by separating the type and value by a `      :     ` or
    `      =     ` character (i.e. `      IP Address: 1.1.1.1, FQDN: badurl.com     ` )
    Note: The entries are not case sensitive. You must use the same string type and spacing used by ThreatQ. 
    Example: ThreatQ uses the following spacing IP Address, so using IPAddress in your entry will not work
-   You can even pass the function a list of dictionaries. Each entry requires the following:
  - type
  - value
  - one of the following: object_name, object_type, object_code, collection, api_name

``` json
[
    {
        "type": "IP Address",
        "value": "1.1.1.1",
        "object_type": "indicators"
    },
    {
        "type": "FQDN",
        "value": "badurl.com",
        "object_type": "indicators"
    }
]
```

### <span id="Upgrading_from_1x_to_2x_204"></span> Upgrading from 1.x to 2.x

While many of the actions in v2.x of the Phantom App look very similar to the v1.x App, they operate
very differently. Chances are, you will need to recreate all of the ThreatQ App actions, and
reconfigure them. Please review all of the actions under the `     App Actions    ` section to see
how to configure them.

## <span id="Known_IssuesLimitations_208"></span> Known Issues/Limitations

N/A

## <span id="Changelog_212"></span> Changelog

Version 2.3.0

Improves parsing & support for other input formats for \`object_list\` parameters:

-   The \`object_list\` parameter can now take ThreatQ IDs (line-separated, comma-separated, JSON
    List, or JSON Dict)
-   The \`object_list\` parameter now supports Event object types better
-   Improves IOC parser

Fixes issue adding attributes to events

Adds \`add tag\` action

Adds \`add comment\` action

Version 2.2.0

-   Adds create signature action

Version 2.1.x

-   Fixed unwanted FQDN indicators creation when a parsed URL does not have a URL path
-   Fixed miscellaneous JSON and documentation issues

Version 2.0.3

-   Rewrite of the app to improve stability, error handling, and input support
-   Remove all “reputation” actions, and replaced them with an all-in-one query action
-   Adds actions to interact with custom objects
-   All response views now share the same template, including tables for attributes and related
    objects (including custom objects)
-   Response data is now better formatted to be used within phantom playbooks to make better
    decisions
-   Querying an indicator will query *all* information about that indicator, including attributes,
    score, status, and relationships. That information is then made accessible within the conditions
    block in order to make a decision

Version 1.0.0

-   Initial release

## Port Information

The app uses HTTP/ HTTPS protocol for communicating with the ThreatQuotient server. Below are the
default ports used by the Splunk SOAR Connector.

| SERVICE NAME | TRANSPORT PROTOCOL | PORT |
|--------------|--------------------|------|
| http         | tcp                | 80   |
| https        | tcp                | 443  |


### Configuration Variables
The below configuration variables are required for this Connector to operate.  These variables are specified when configuring a ThreatQ asset in SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**tq_server** |  required  | string | Server IP/Hostname
**clientid** |  required  | string | Client ID
**username** |  required  | string | Username
**password** |  required  | password | Password
**trust_ssl** |  optional  | boolean | Trust SSL Certificate?

### Supported Actions  
[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity  
[query indicators](#action-query-indicators) - Query ThreatQ for indicator context  
[create indicators](#action-create-indicators) - Create indicators within ThreatQ  
[create adversaries](#action-create-adversaries) - Create adversaries within ThreatQ  
[create custom objects](#action-create-custom-objects) - Create custom objects within ThreatQ  
[add attribute](#action-add-attribute) - Adds an attribute to objects in ThreatQ  
[add comment](#action-add-comment) - Adds a comment to objects in ThreatQ  
[add tag](#action-add-tag) - Adds a tag to objects in ThreatQ  
[set indicator status](#action-set-indicator-status) - Set a status for a given list of indicators  
[create task](#action-create-task) - Create a task within ThreatQ  
[create event](#action-create-event) - Create an event within ThreatQ  
[start investigation](#action-start-investigation) - Start an investigation within ThreatQ  
[upload spearphish](#action-upload-spearphish) - Upload a spearphish attempt to ThreatQ  
[upload file](#action-upload-file) - Upload (and parse) a file to ThreatQ  
[get related objects](#action-get-related-objects) - Query ThreatQ for an object's relationships  
[create signature](#action-create-signature) - Create a signature within ThreatQ  

## action: 'test connectivity'
Validate the asset configuration for connectivity

Type: **test**  
Read only: **True**

#### Action Parameters
No parameters are required for this action

#### Action Output
No Output  

## action: 'query indicators'
Query ThreatQ for indicator context

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**indicator_list** |  required  | A comma-separated or line-separated list of indicator values | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name` 
**exact** |  optional  | Do we want to find an exact match or an approximate match? | boolean | 
**with_all_relationships** |  optional  | Should we fetch all relationships with this action? | boolean | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.exact | boolean |  |   True  False 
action_result.parameter.indicator_list | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name`  |  
action_result.parameter.with_all_relationships | boolean |  |   True  False 
action_result.data.\*.adversaries.\*.name | string |  |  
action_result.data.\*.attack_pattern.\*.value | string |  |  
action_result.data.\*.attributes | string |  |  
action_result.data.\*.campaign.\*.value | string |  |  
action_result.data.\*.course_of_action.\*.value | string |  |  
action_result.data.\*.events.\*.title | string |  |  
action_result.data.\*.exploit_targets.\*.value | string |  |  
action_result.data.\*.identity.\*.value | string |  |  
action_result.data.\*.incident.\*.value | string |  |  
action_result.data.\*.indicators.\*.value | string |  |  
action_result.data.\*.intrusion_set.\*.value | string |  |  
action_result.data.\*.malware.\*.value | string |  |  
action_result.data.\*.report.\*.value | string |  |  
action_result.data.\*.score | numeric |  |  
action_result.data.\*.signatures.\*.name | string |  |  
action_result.data.\*.signatures.\*.value | string |  |  
action_result.data.\*.sources.\*.name | string |  |  
action_result.data.\*.status.name | string |  |  
action_result.data.\*.tool.\*.value | string |  |  
action_result.data.\*.ttp.\*.value | string |  |  
action_result.data.\*.type.name | string |  |  
action_result.data.\*.value | string |  |  
action_result.data.\*.vulnerability.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'create indicators'
Create indicators within ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**indicator_list** |  required  | A comma-separated or line-separated list of indicators and indicator type (optional) name/value pairs (e.g.: IP Address: 1.1.1.1) | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name` 
**indicator_status** |  optional  | The default status for the indicators uploaded to ThreatQ | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.indicator_list | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name`  |   IP Address: 1.1.1.1 
action_result.parameter.indicator_status | string |  |   Active 
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'create adversaries'
Create adversaries within ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**adversary_list** |  required  | A comma-separated or line-separated list of adversary names | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.adversary_list | string |  |  
action_result.data.\*.name | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'create custom objects'
Create custom objects within ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_list** |  required  | A comma-separated or line-separated list of custom object values | string | 
**object_type** |  required  | The object type of the specified list values | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.object_list | string |  |   Identity 
action_result.parameter.object_type | string |  |  
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'add attribute'
Adds an attribute to objects in ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_list** |  required  | A comma-separated or line-separated list of object values | string | 
**object_type** |  required  | The object type of the specified list values | string | 
**attribute_name** |  required  | The name of the attribute in ThreatQ | string | 
**attribute_value** |  required  | The value fo the attribute in ThreatQ | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.attribute_name | string |  |  
action_result.parameter.attribute_value | string |  |  
action_result.parameter.object_list | string |  |  
action_result.parameter.object_type | string |  |   Identity 
action_result.data.\*.name | string |  |  
action_result.data.\*.title | string |  |  
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'add comment'
Adds a comment to objects in ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_list** |  required  | A comma-separated or line-separated list of object values | string | 
**object_type** |  required  | The object type of the specified list values | string | 
**comment** |  required  | The comment to add to the objects | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.comment | string |  |  
action_result.parameter.object_list | string |  |  
action_result.parameter.object_type | string |  |   Identity 
action_result.data.\*.name | string |  |  
action_result.data.\*.title | string |  |  
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'add tag'
Adds a tag to objects in ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_list** |  required  | A comma-separated or line-separated list of object values | string | 
**object_type** |  required  | The object type of the specified list values | string | 
**tag** |  required  | The tag to add to the objects | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.tag | string |  |  
action_result.parameter.object_list | string |  |  
action_result.parameter.object_type | string |  |   Identity 
action_result.data.\*.name | string |  |  
action_result.data.\*.title | string |  |  
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'set indicator status'
Set a status for a given list of indicators

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**indicator_list** |  required  | A comma-separated or line-separated list of indicators and indicator type (optional) name/value pairs (e.g.: IP Address: 1.1.1.1) | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name` 
**indicator_status** |  required  | The status to give to the list of indicators | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.indicator_list | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name`  |   IP Address: 1.1.1.1 
action_result.parameter.indicator_status | string |  |   Active 
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'create task'
Create a task within ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**task_prefix** |  optional  | Prefix for the task name | string | 
**task_name** |  required  | Task name | string | 
**assigned_to** |  optional  | ThreatQ user to assign the task to | string | 
**task_status** |  required  | Task status in ThreatQ | string | 
**task_priority** |  required  | Task priority in ThreatQ | string | 
**task_description** |  optional  | Task description in ThreatQ | string | 
**indicator_list** |  optional  | List of indicator values (use format node) | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.assigned_to | string |  |  
action_result.parameter.indicator_list | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name`  |  
action_result.parameter.task_description | string |  |  
action_result.parameter.task_name | string |  |  
action_result.parameter.task_prefix | string |  |   Investigate Event 
action_result.parameter.task_priority | string |  |   Low 
action_result.parameter.task_status | string |  |   In Progress 
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'create event'
Create an event within ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**event_type** |  required  | The event type in ThreatQ | string | 
**indicator_list** |  optional  | List of comma-separated or line-separated indicator | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.event_type | string |  |   Anonymization 
action_result.parameter.indicator_list | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name`  |  
action_result.data.\*.title | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'start investigation'
Start an investigation within ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**investigation_name** |  required  | The investigation name | string | 
**investigation_priority** |  required  | The investigation's priority | string | 
**investigation_visibility** |  required  | The investigation's sharing status | string | 
**investigation_description** |  optional  | The investigation's description | string | 
**indicator_list** |  required  | List of comma-separated or line-separated indicator | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name` 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.indicator_list | string |  `domain`  `ip`  `email`  `url`  `hash`  `sha256`  `string`  `file name`  `file path`  `host name`  `md5`  `process name`  `sha1`  `user name`  |  
action_result.parameter.investigation_description | string |  |  
action_result.parameter.investigation_name | string |  |  
action_result.parameter.investigation_priority | string |  |   Normal 
action_result.parameter.investigation_visibility | string |  |   Shared 
action_result.data.\*.name | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'upload spearphish'
Upload a spearphish attempt to ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** |  required  | The Vault ID for the spearphish email file | string |  `vault id` 
**indicator_status** |  optional  | Default indicator status. If none selected, Review is used | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.indicator_status | string |  |   Review 
action_result.parameter.vault_id | string |  `vault id`  |   b69473ee89a6f7d216fb601e71d6e1f9d483c5de 
action_result.data.\*.title | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'upload file'
Upload (and parse) a file to ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**vault_id** |  required  | The Vault ID for the file to upload | string |  `vault id` 
**parse_for_indicators** |  required  | Whether or not to parse the file for indicators | boolean | 
**indicator_status** |  optional  | Default indicator status. If none selected, Review is used | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.indicator_status | string |  |   Review 
action_result.parameter.parse_for_indicators | boolean |  |   True  False 
action_result.parameter.vault_id | string |  `vault id`  |   b69473ee89a6f7d216fb601e71d6e1f9d483c5de 
action_result.data.\*.name | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'get related objects'
Query ThreatQ for an object's relationships

Type: **investigate**  
Read only: **True**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**object_list** |  required  | A comma-separated or line-separated list of custom object values | string | 
**object_type** |  required  | The object type of the specified list values | string | 
**related_object_type** |  required  | The object type of the relationships you want to find | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.object_list | string |  |  
action_result.parameter.object_type | string |  |   Event 
action_result.parameter.related_object_type | string |  |   Event 
action_result.data.\*.attributes | string |  |  
action_result.data.\*.name | string |  |  
action_result.data.\*.score | numeric |  |  
action_result.data.\*.sources.\*.name | string |  |  
action_result.data.\*.status.name | string |  |  
action_result.data.\*.title | string |  |  
action_result.data.\*.type.name | string |  |  
action_result.data.\*.value | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary.total | numeric |  |   1 
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1   

## action: 'create signature'
Create a signature within ThreatQ

Type: **generic**  
Read only: **False**

#### Action Parameters
PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**signature_name** |  required  | The name for the signature uploaded to ThreatQ | string | 
**signature_value** |  required  | The value for the signature uploaded to ThreatQ | string | 
**signature_type** |  required  | The type for the signature uploaded to ThreatQ | string | 
**signature_status** |  required  | The status for the signature uploaded to ThreatQ | string | 

#### Action Output
DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.parameter.signature_name | string |  |   ExampleRule 
action_result.parameter.signature_value | string |  |   rule ExampleRule { strings: $my_text_string = \\"text here\\" $my_hex_string = { E2 34 A1 C8 23 FB } condition: $my_text_string or $my_hex_string } 
action_result.parameter.signature_type | string |  |   YARA 
action_result.parameter.signature_status | string |  |   Active 
action_result.data | string |  |  
action_result.status | string |  |   success  failed 
action_result.message | string |  |  
action_result.summary | string |  |  
summary.total_objects | numeric |  |   1 
summary.total_objects_successful | numeric |  |   1 