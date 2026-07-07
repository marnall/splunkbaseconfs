# Sonar Add-on for Splunk

## Overview

Sonar Add-on for Splunk is a [Custom Search Command] that allows Splunk Users to query Sonar data using SPL (Splunk Search Language)

## Usage

`sonar` is a search command that generates events, and therefore it must be used in the beginning of a search query.

### Syntax 

`| sonar index="<index-pattern-name>|<database-collection>"` 

### Examples
* `| sonar index="<index-pattern>"`
* `| sonar index="<database>-<collection>" timestamp="<timestamp field>"`
* `| sonar index="<index-pattern>" timestamp="<timestamp field>"`
* `| sonar index="<index-alias>" timestamp="<timestamp field>"`
* `| sonar index="<database>-<collection>" limit=<limit>  | spath company | search company=jsonar`

### Parameters

#### index

**Format:** String

**Required:** Yes

Index must contain only one dash, and some special characters[-, ., $, ", \s, /, \\] are not allowed.
(Dot `.` is allowed anywhere after the dash `-`)

There are two ways to use this parameter to retrieve data from sonar service,

1. Expecting string for the index to be usually an index-pattern or index-alias already defined in sonar service.

2. Or string concatenation of database name, dash(-) and collection name.
 
#### timestamp

**Format:** String

**Required:** No

Used as the Splunk Time field. The time range filter will be applied to this field.

This parameter will override the index-pattern timestamp field.

If a timestamp field is not present in the search nor in the index pattern, 
Sonar Service will look for any date field in the collection to use as timestamp. 

**PS.:** The result is going to be empty If the time range is anything other than `All time` AND no date field is present in the collection.
 
#### limit

**Format:** Integer

**Required:** No

Limit the maximum number of results from the 'sonar' command.
This parameter will override the default limit configuration.

Any value less or equal to 0 will remove the limit from the search.

#### disable_count

**Format:** Boolean

**Required:** No

Disable the count pipeline to improve performance when dealing with a large set of data.

By default, Sonar service will execute a count pipeline to inform users the total amount of events their query returns and if it will be limited.  

## Sonar Actions

Fields with a `SonarAction:` prefix are going to be present in the event when querying an Index Pattern that contains sonar actions.

### Executing Sonar Actions

`SonarAction` fields will provide [Splunk Workflow Actions] that, when executed, are going to redirect the user to the Run Sonar Action page.
Those workflow actions will have different behavior depending on [Sonar Splunk Service]'s token configuration (`com.jsonar.splunk.token.enable`).

- **When Enabled**, the workflow action will terminate the current **sonar user** session and start a new session with the **mapped user**.

- **When Disabled**, the workflow action will use the current **sonar user** session to run Sonar Actions. If there is no sonar session available, the Splunk User will be redirected to Sonar's login page.

## Dependencies

* Splunk 7.0+
* [Sonar Splunk Service]

## Setup

* ##### On Sonar Machine:
  * Install [Sonar Splunk Service](../service/README.md#installation-steps)
  
* ##### On Splunk Machine:
  * Install the latest [Sonar Add-on for Splunk]

## Configuration

#### On Sonar Machine:

* Configure [Sonar Splunk Service](../service/README.md#configuration)
* Make sure [Sonar Splunk Service] is running

#### On Splunk Machine:

After installing [Sonar Add-on for Splunk] the configuration page will be available.


##### Configuration

* License - [Sonar Splunk Service] license. The license will be printed in the service log during the startup process.
* Address - [Sonar Splunk Service] machine's IP/Hostname. Make sure the Splunk Machine can ping this address.
* Port - Port which [Sonar Splunk Service] is listening for connections.
* Limit - Limit the number of events [Sonar Splunk Service] returns to Splunk. It must be an integer.
This limit has lower precedence than the limit in the sonar command but will override the default limit configured in the service. 

## Troubleshooting

If some error occurred, please inspect the current job, open search.log and look for an ERROR message

* ##### HTTP Error 111:
    Sonar-Splunk service is down
    ###### Solution:
    Contact the Sonar Admin to start/configure Sonar-Splunk service

* ##### HTTP Error 403:
    Your Splunk user is not allowed to access Sonar Database
    ###### Solution:
    Contact the Sonar Admin to enable access to your Splunk user

* ##### HTTP Error 404:
    Malformed URL to Sonar-Splunk service
    ###### Solution:
    Contact the Splunk Admin.
    ###### Possible causes:
    Issue in SSL configuration
    Wrong Endpoint in URL

* ##### Exception: Missing configuration:
    Missing field in indexer or provider
    ###### Solution:
    Contact the Splunk Admin to find and configure the missing field

* ##### Exception: Incomplete input from Splunk
* ##### HTTP Error 400
* ##### HTTP Error 500
* ##### Or other errors:
    Contact the jSonar team. If possible, please provide the ERROR messages found in "search.log", and some explanation on how it happened or how to reproduce it.

[//]: #

[Splunk Workflow Actions]: <https://docs.splunk.com/Documentation/Splunk/8.0.3/Knowledge/CreateworkflowactionsinSplunkWeb>
[Sonar Splunk Service]: <../service>
[Sonar Add-On for Splunk]: <https://splunkbase.splunk.com/app/4463/>
[Custom Search Command]: <https://dev.splunk.com/enterprise/docs/developapps/customsearchcommands/>