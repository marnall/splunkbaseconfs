# Webex Teams Modular Input

Authors: Datapunctum GmbH
Description: Webex Teams Modular Input
Version: 1.0.0

## Introduction

The purpose of this add-on is to collect Webex Teams Events and Webex Teams Audit-Events through the [Webex Teams API](https://developer.webex.com/docs/api/getting-started)

This Add-on has been built using the Splunk Add-on Builder

## Special Features

* If files have been uploaded in a message, the event can be enriched with file information.
* If rooms have been created, the event can be enriched with the room title.
* Messages can be masked for privacy

## Authentication

Authentication to the API is through Personal Access Tokens. An Personal Access Token can be acquired through a Refresh Token, which has to be renewed once a while.

The Add-on expects an active Refresh Tokens and keeps track of the lifetime of the Access Token and automatically refreshes the access token if needed.

Additionally to the Refresh Token, the Client ID and Client Secret has to be provided.

Multiple Refresh Tokens with different access rights.(up to 4) may be configured and referenced by Inputs.

## Additional Configuration

### Logging

The Log-Level can be set in the "Logging" Tab.

Log Files can be found under:

* $SPLUNK_HOME/var/log/splunk/ta_dp_webex_teams_webex_teams_events.log for Events

* $SPLUNK_HOME/var/log/splunk/ta_dp_webex_teams_webex_teams_admin_audit_events.log for Audit Events

### General Configuration

In some cases, the Webex API did not give back a valid certificate. For all requests, it's possible to disable Certificate Verification.

### Proxy

For connections over a proxy, the settings can be found under "Configuration"

## Input Configuration

### Overview

Under Inputs, select which type of input should be created

### Creating Webex Teams Event Inputs

Following parameters have to be set for the input:

* Name
* Interval
* Index
* Refresh Token
* Resource
* Message Masking
* Fetch Attachemen Information
* Fetch Room Information

Events will be created with the webex:teams:events sourcetype.

## Creating Webex Teams Admin Audit Event Input

Following parameters have to be set for the input:

* Name
* Interval
* Index
* Refresh Token
* Organization ID

Events will be created with the webex:teams:adminaudit:events sourcetype.

## Release Notes

* 1.0.1 / 2020-08-04 Bugfix Release
* 1.0.0 / 2020-07-23 First Release
 
## Change Notes

* 2020-07-23 mbo
  * First Release
* 2020-08-04 mbo
  * Fixed in issue with too many token refreshes
  
## License

Copyright 2020 Datapunctum GmbH

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.

## Sourcecode Repository

https://github.com/datapunctum/TA-DP-webex-teams

