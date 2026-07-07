# Rundeck App Community Version v1.0
* June 2018
* Developed by BaboonBones, Ltd. ( www.baboonbones.com ) for Rundeck, Inc. ( www.rundeck.com )

## Overview

Community edition App for monitoring Rundeck Core Community Edition

## Dependencies

* Splunk 7.0+ , https://www.splunk.com/en_us/download/splunk-enterprise.html
* Supported on all Splunk platforms
* Rundeck Core Community Edition or Pro Edition(Team/Cluster)
* Minimum Rundeck API Version 18
* HTTPS network access from your Splunk Server to your Rundeck Server
* TCP network access from your Rundeck Server to your Splunk Receiver port(default 9997)
* Rundeck Authentication token for REST API Access , http://rundeck.org/docs/api/index.html#token-authentication

## Installation

* Untar the App release to your `SPLUNK_HOME/etc/apps` directory
* Restart Splunk and Login

## Distributed Installation

In a distributed Splunk installation you will typically install the App components across Heavy Forwarders and Search Heads.

As this App requires that you have access to the App's Setup page in order to configure hosts and encrypted auth tokens , you will have to use a Heavy Forwarder(HF) rather than a Universal Forwarder if you want to split out the data collection (REST polling) logic to a forwarder tier.

The App's setup page will only automatically enable the REST polling stanzas if this App is running on a Splunk instance that is an Indexer or Forwarder server role.

Your HF will forward data into your indexer cluster as per standard Splunk administation of `outputs.conf` configurations.

The Search Heads will then only require the UI,Knowledge Object and Custom Alert Action components of the App release.

The App release ships with an `app.manifest` file , so you can utilise Splunk's Packaging Toolkit (http://dev.splunk.com/view/packaging-toolkit/SP-CAAAE9V) to build the Search Head App bundle.

If you install the App on a Heavy Forwarder , the Modular Input (for polling REST Endpoints) needs to have access to your Rundeck index.This is because it executes Splunk searches to dynamically create endpoints to poll based on values in the search results ie: list of Project names. 

## Setup

Browse to `Rundeck App Community Version` in the lefthand side Apps panel and enter various global settings as well as your authentication token.These global settings are used by both the Rundeck Modular Input and the Rundeck Custom Alert Action.

The authentication token gets securely encrypted in `local/passwords.conf`

Upon saving the setup screen , the REST inputs will automatically enable and start polling for data if the Splunk instance is an Indexer or Forwarder server role only.

Check that the REST API data is being received by browsing to the `Data -> Data Sources` dashboard , it may take a minute or 2.

The setup page can be browsed to at any time for configuration edits via the navigation menu: `Admin -> Configuration -> Setup Rundeck Environment`

## Configure/Enable/Disable the REST Inputs via the Splunk Web UI

The REST inputs can be manually viewed/edited/controlled via the navigation menu  :  `Admin -> Configuration -> REST Endpoints`

Descriptions of the input configuration fields can be found in `README/inputs.conf.spec` and also in the UI.

## Host name and port

Your Rundeck host must be entered in the format : foo.myrundeck.com (don't include 'https://' , this is hardcoded by default to satisfy Splunk certification requirements for secure network communications).You can also specify an alternative port with the host , foo.myrundeck.com:1234

## Configure the Custom Alert Action

When you create a scheduled alert in Splunk (http://docs.splunk.com/Documentation/Splunk/7.1.1/Alert/Definescheduledalerts) , `Rundeck Job` will be presented as one of the available Trigger Actions.

The UI will then guide you to fill in any additional fields.

For a detailed list of the fields , refer to `README/alert_actions.spec` and `README/savedsearches.spec`

The Rundeck host that you specify for your Alert Action must match 1 of the hosts that you setup on the App's setup page.

## Configure Forwarding of Rundeck logs

##### index

main (this is the default , change this if your Splunk admin has directed you to use a different index)

##### sourcetype

see below for the log sourcetypes to use for the various log sources.It is important that you use the correct sourcetype name.

##### host

the host you specify must match what you setup in the Rundeck App setup screen.

### Universal Forwarder (inputs/outputs conf files)

1. Configure Splunk receiving in your Splunk Server.Default port 9997 is usually fine (unless your network admin says otherwise) , https://docs.splunk.com/Documentation/Splunk/7.1.2/Forwarding/Enableareceiver

2. Ensure your network is open for TCP 9997 from your Rundeck Server to your Splunk server

3. Download a Splunk Universal Forwarder(UF) https://www.splunk.com/en_us/download/universal-forwarder.html

4. Install the UF on your Rundeck Server to monitor the Rundeck log files, http://docs.splunk.com/Documentation/Forwarder/7.1.2/Forwarder/Abouttheuniversalforwarder. You can just untar the UF tarball release to your Rundeck install directory.

5. Setup the `inputs.conf` and `outputs.conf` files

    5.1. Copy the example `local` directory from `SPLUNK_HOME/etc/apps/rundeck_app/forwarder_config` to your UF's  SPLUNK_HOME/etc/apps/search directory

    5.2. Replace placeholders

      5.2.1. `inputs.conf`
      * host (to match what you specified in the app's setup page).For a cluster , use the cluster address in the host field.
      * log paths , if these are different to the examples (which are the Rundeck defaults)
      * index , if using a different index to the default of `main`

      5.2.2. `outputs.conf`
      * your Splunk server host/IP and receiving port

6. Restart the UF

7. Check that the log data is being received by browsing to the `Data -> Data Sources` dashboard

### log4j appenders

Rundeck uses log4j as it's logging framework , http://rundeck.org/docs/administration/configuration-file-reference.html#log4j.properties

An alternative to installing a Splunk Universal Forwarder is to install a Splunk log4j appender to forward log data directly to Splunk via raw TCP or HTTP Event Collector.There are 3rd party libraries availble for this purpose , such as https://splunkbase.splunk.com/app/1715/

## Authentication Token

You can request your authentication token from your Rundeck administrator.This app has a background task that will automatically check if the authentication token is going to expire within 2 days time(by default) , and automatically generate a new token for you. The new token will start being used and the old token discarded (but not deleted from Rundeck).

Token generation settings are configurable via the `rundeck://authtokenrefresh` stanza in inputs.conf

##### Token Duration

* `duration` : the duration in days of new token ie: 30d , 120d

##### Expiry Window

* `expiry_window_secs` : if the current token is due to expire within this window in seconds , generate a new one


## Permissions

By default ,this App is set to be Globally accessible by all users and apps

## Indexes

This App does not create any indexes by default.If you want to change the default index (main), ensure you also change the global index used for searches in `default/macros.conf` in the 'rundeck_index' stanza. This is done for you automatically if you change the index via the App's setup page.

You will also need to update the index in `inputs.conf` on your Splunk Forwarders.

## Sources

This App uses 2 sources of data :

* Rundeck REST API
* Rundeck Logs

## Sourcetypes

#### REST

##### rundeck_rest_sysinfo

http://rundeck.org/docs/api/#system-info

##### rundeck_rest_users

http://rundeck.org/docs/api/#list-users

##### rundeck_rest_logstorage

http://rundeck.org/docs/api/#log-storage-info

##### rundeck_rest_logstorage_incomplete

http://rundeck.org/docs/api/#list-executions-with-incomplete-log-storage

##### rundeck_rest_projects

http://rundeck.org/docs/api/#listing-projects

##### rundeck_rest_project_event_history

http://rundeck.org/docs/api/#listing-history

##### rundeck_rest_project_resources

http://rundeck.org/docs/api/#listing-resources

##### rundeck_rest_project_jobs

http://rundeck.org/docs/api/#listing-jobs

##### rundeck_rest_project_executions

http://rundeck.org/docs/api/index.html#execution-query

#### Logs

Below are the sourcetypes you must use for monitoring your Rundeck log files.The example stanzas below can be added to inputs.conf on your Splunk Forwarder instance.

Ensure that your `host` and `index` match what you specified in the App setup page.

For a cluster , use the cluster address in the host field.

The monitoring path is the default Rundeck log path, change this if necessary.

##### rundeck_logs_access

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.access.*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_access
```

##### rundeck_logs_api

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.api.*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_api
```

##### rundeck_logs_audit

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.audit.*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_audit
```

##### rundeck_logs_executions

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.executions.*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_executions
```

##### rundeck_logs_jobs

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.jobs.*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_jobs
```

##### rundeck_logs_main

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.log*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_main
```

##### rundeck_logs_options

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.options.*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_options
```

##### rundeck_logs_storage

###### Example monitor definition

```
[monitor:///var/log/rundeck/rundeck.storage.*]
disabled = false
index = main
host = yourhost
sourcetype = rundeck_logs_storage
```

##### rundeck_logs_service

###### Example monitor definition

```
[monitor:///var/log/rundeck/service.log*] 
disabled = false 
index = main 
host = yourhost
sourcetype = rundeck_logs_service 
```


## Logging and Errors

Any log entries/errors will get written to `SPLUNK_HOME/var/log/splunk/rundeck_app*.log`

* `rundeck_app_alertaction.log` : alert action script
* `rundeck_app_modularinput.log` : modular input script
* `rundeck_app_setuphandler.log` : custom setup handler script

This log file is rotated daily.

You can set the logging level globally via the App's setup page.

You can then easily search for logs in Splunk : `index=_internal source=*rundeck_app*.log ERROR`


## Troubleshooting

* You are using Splunk 7+
* Look for any errors as detailed in the "Logging and Errors" section
* Any firewalls blocking outgoing HTTP calls ?
* Are your proxy settings correct if required on your network ?
* Are there any error logs at the target API ?
* Are your URL's correct ?
* Is your authentication setup correctly ?
* If you are running on a Universal Forwarder , is Python 2.7 installed on the OS system path ?
* Can you see requests being made on the wire ? ie: using Wireshark or another wire capture utility

## Contact

This App was developed by BaboonBones, Ltd. for Rundeck, Inc. ( www.rundeck.com )
* www.baboonbones.com
* info@baboonbones.com
