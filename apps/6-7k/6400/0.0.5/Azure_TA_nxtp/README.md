# Technical Add-On for _Azure_

This extension for [Splunk®](https://www.splunk.com/) allows you to retrieve data from the
[public API](https://learn.microsoft.com/en-us/graph/use-the-api) of [Azure](https://azure.microsoft.com/en-us/)
and integrate this data into your log management. 
With the setting of the inputs data of [application](https://learn.microsoft.com/en-us/graph/api/resources/application?view=graph-rest-1.0), [credentials](https://learn.microsoft.com/en-us/graph/api/resources/federatedidentitycredential?view=graph-rest-1.0) and [groupmemberships](https://learn.microsoft.com/en-us/graph/office365-groups-concept-overview?view=graph-rest-1.0) are fetched and indexed. 
You can then use the logs to create various evaluations, audits, reports or alerts.

## Author information

- Author: Nextpart Security Intelligence GmbH
- Version: `0.0.5` (dynamic)
- Creation: February, 2023

## Using this Application

- Source: `azure`
- Sourcetype:
  - `azure:application:app`
  - `azure:application:credential`
  - `azure:groupmembership`

## Setup

1. After you have installed and activated the app, create an index (e.g. "`azure`").

2. Then you can configure and activate the input.

### Inputs

- Azure Applications
  - This Input is used to fetch App related Data in the Active Directory via the Graph API
- Azure Groupmembership
  - This Input is used to fetch all Groups in the Active Directory via the Graph API

## Copyright & License

Copyright © 2023 Nextpart Security Intelligence GmbH
