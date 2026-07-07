# Dell ECS Add-on for Splunk

Dell ECS Add-on is a Splunk Add-on which is collecting data from ECS REST APIs and indexes into the Splunk Enterprise.
* Author - Dell Inc.

## Release Notes

* Version 1.2.1
    * Updated Splunk SDK to support Splunk cloud

* Version 1.2.0
    * Upgraded to latest python libraries.
    * Deprecated python2 support.
    * Added support for latest Splunk version.
    * Added flux API support for DELL v3.6.

* Version 1.1.0
    * Splunk 8 Support
    * Made Add-on Python23 compatible

## Requirements

Splunk Enterprise:

* Version 8.1.x and 8.2.x

Python:  

* Version 3.7

Tested on CentOS, Windows with the latest chrome and firefox version.

## Recommended System Configuration  

Standard Splunk Enterprise configuration of Search Head, Indexer, and Forwarder. 

## Topology and Setting up Splunk Environment

This Add-On can be set up in two ways:

1) Standalone Mode: Install the Add-on app on a single machine. This single machine would serve as a Search Head + Indexer + Heavy forwarder for this setup.
2) Distributed Environment: Install Add-on on search head and Heavy forwarder (for REST API).

   * Add-on resides on search head machine need not require any configuration here.
   * Add-on needs to be installed and configured on the Heavy forwarder system.
   * Execute the following command on Heavy forwarder to forward the collected data to the indexer. /opt/splunk/bin/splunk add forward-server <indexer_ip_address>:9997
   * On the Indexer machine, enable event listening on port 9997 (recommended by Splunk).
   * Add-on needs to be installed on search head for CIM mapping

## Installation
  
This TA can be installed through UI using following steps.  
  
1. Log in to Splunk Web and navigate to Apps > Manage Apps.  
2. Click `install app from file`.  
3. Click `Choose file` and select Dell ECS Add-on installation file.
4. Click on `Upload`.
5. Restart Splunk.

## Application Setup   

### Configurations  

After Installation
  
1. Click on the `Configuration` tab next to `Inputs` tab.  
2. Click on the `Add` button to add an ECS Server information.
3. Provide your ECS Server credential and Click on `Add`.
  
| Global account parameters|   Mandatory or Optional  |                Description                                  |  
|  ----------------------  |   --------------------   |-------------------------------------------------------------|  
|     Account name         |     Mandatory            |  Provide unique name to uniquely identify ECS Server details|  
|     Server Address       |     Mandatory            |  Provide Server Address for ECS server (IP Address)   |  
|     Username             |     Mandatory            |  Provide User name of ECS server                      |  
|     Password             |     Mandatory            |  Provide Password of ECS server                       |  
|  Verify SSL Certificate  |     Optional             |  To get the data from APIs using SSL, remains the checkbox enable otherwise disable it. Note that if checkbox is enable then user needs to append certificate in `$SPLUNK_HOME/etc/apps/TA-dellecs/ta_dell_ecs/requests/cacert.pem` file, for the safety purpose please take a backup of cacert.pem while appending SSL certificate |
|   Proxy Enable           |     Optional             |  To enable proxy for the account. If an account with proxy enabled is used in any input then it uses the proxy details attached to that account for the data collection |

Following proxy params will show up once Proxy Enable checkbox is checked:

| Proxy Paramters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Proxy Type            |     Mandatory            |  Select proxy type that you want to use from dropdown. The TA supports http proxy only.|
|    Proxy Host            |     Mandatory            |  Host or IP of the proxy server                                                        |
|    Proxy Port            |     Mandatory            |  Port for proxy server                                                                 |
|  Proxy Username          |     Optional             |  Username of the proxy server. It is mandatory in case when user has entered `Password`|
|  Proxy Password          |     Optional             |  Password of the proxy server. It is mandatory in case when user has entered `Username`|

1. To configure log-level, Select `Logging`.  
2. Select the log level from dropdown and click on `Save`.
  
### Inputs  
  
1. Go to the apps list and open `Dell ECS Add-on for Splunk`. From the inputs screen, click on `Create New Input`. It has multiple input configuration `Dell ECS Input` , `Dell ECS Namespaces Input`, `Dell ECS Buckets Input`.
* `Dell ECS Input` will index all the data into the Splunk except Namespace and Bucket data.
* `Dell ECS Namespace Input` will index Namespace data only.
* `Dell ECS Buckets Input` will index Buckets data only.
Note that if multiple inputs are created with the same global account, there will be duplicate Events in Splunk.
  
| Input Parameter | Mandatory or Optional |                Description                   |  
|  -------------- |    -----------------  |----------------------------------------------|  
|      Name       |      Mandatory        | Provide unique name to uniquely identify a ECS Server details |
|     Interval    |      Mandatory        | Interval in seconds or cron schedule. The input will be triggered at every interval time and fetch the data from ECS endpoints. cron schedule e.g. for every one minute cron schedule will be */1 * * * *. |
|     Index       |      Mandatory        | Index in which you want to store your data.    |
|   Global Account|      Mandatory        | Select previously configured ECS Server details.|
|   Start Time    |      Optional         | Provide start time in GMT from which Data Collection will start. Time format is  "%Y-%m-%dT%H:%M".| 

## Search  
  
To see data logged by `Dell ECS Add-on for Splunk`, select the `Search` tab. Search  ``Dell_ECS_index`` macro.

## External Libraries used

| Libraries(Python)      |  Version   |                Repository link            |                            License                          |
|  --------------      | -----------| ----------------------------------------- |-------------------------------------------------------------|
|   croniter           |   0.3.25   | https://pypi.org/project/croniter/        | https://github.com/kiorky/croniter/blob/master/docs/LICENSE |
|   dateutil           |   2.6.1    | https://pypi.org/project/python-dateutil/ | https://github.com/dateutil/dateutil/blob/master/LICENSE    |

## Troubleshooting  

To troubleshoot Dell ECS Add-on, check following log files
* $SPLUNK_HOME/var/log/splunk/**ta_dell_ecs_dell_ecs_input.log**
* $SPLUNK_HOME/var/log/splunk/**ta_dell_ecs_dell_ecs_namespaces_input.log** 
* $SPLUNK_HOME/var/log/splunk/**ta_dell_ecs_dell_ecs_buckets_input.log** file. 

User can search for ERROR logs in the Splunk using following query
* `index="_internal" source=**ta_dell_ecs_dell_ecs_*.log** ERROR`

## Uninstall & Cleanup steps

* Remove $SPLUNK_HOME/etc/apps/TA-dellecs
* Remove $SPLUNK_HOME/var/log/splunk/**ta_dell_ecs_dell_ecs_input.log**
* Remove $SPLUNK_HOME/var/log/splunk/**ta_dell_ecs_dell_ecs_namespaces_input.log** 
* Remove $SPLUNK_HOME/var/log/splunk/**ta_dell_ecs_dell_ecs_buckets_input.log**
* To reflect the cleanup changes in UI, Restart Splunk Enterprise instance

## Support

* Support Offered: Yes
* Support Email: dell-support@crestdata.ai

## Copyright

* Copyright (C) 2025 Dell Technologies Inc. All Rights Reserved.