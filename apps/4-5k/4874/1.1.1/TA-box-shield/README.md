# Box Shield Add-on for Splunk

Box Shield Add-on for Splunk collects shield and classification events from the Box API and ingests it into the Splunk index. It also provides CIM mapping with `alerts` and `change` data model respectively. Additionally, Shield events with Malicious Content type are mapped with `malware attacks` and `alerts` data model.

This is an app powered by the Splunk Add-on Builder.

## Requirements

Splunk Enterprise:

* Version 7.2.x, 7.3.x and 8.0.x

Python:

* Version 2.7
* Version 3.7

Tested on Linux, Windows and MacOS with the latest Chrome and Firefox version.
This TA should be installed on Forwarder and Search Head.

## Release Notes

### Version 1.1.1

* Minor bug fixes.

### Version 1.1.0

* Provided support for `Malicious Content` type of shield events.
* Provided CIM mapping for the `Malicious Content` type of shield events with `malware attacks` and `alerts` data model.

## Upgrading to version 1.1.1

Follow the below steps to upgrade the Add-on to 1.1.1

-   Go to `Apps > Manage Apps` and click the `Install app from file`.
-   Click `Choose File` and select the TA-box-shield installation file.
-   Check the `Upgrade app` checkbox and click on `Upload`.
-   After a successful restart, go to the Apps list and open `Box Shield Add-on for Splunk`.
-   From the `Inputs` page, click on `Create New Input` to create new inputs with required fields.


## Recommended System Configuration  

* Standard Splunk Enterprise configuration of Search Head, Indexer, and Heavy Forwarder.
* For the distributed environment, only indexes on the forwarder would be shown in the input configuration page.

## Installation  
  
This TA can be installed through UI using following steps.  
  
1. Log in to Splunk Web and navigate to Apps > Manage Apps.  
2. Click `Install app from file`.  
3. Click `Choose file` and select Box Shield Add-on installation file.  
4. Click on `Upload`.
5. Restart Splunk.

## Application Setup   

### Configurations  

After Installation
  
1. Click on the `Configuration` tab next to `Inputs` tab.  
2. Click on the `Add` button to add the Box Account information.
3. Provide your Box credential and Click on `Add`.
  
| Box Account parameters|   Mandatory or Optional  |                Description                                  |  
|  ----------------------  |   --------------------   |-------------------------------------------------------------|  
|     Box Account         |     Mandatory            |  Provide unique name to uniquely identify Box Account details|  
|     Client ID      |     Mandatory            |  Provide Client ID of Box Account  |  
|     Client Secret             |     Mandatory            |  Provide a Client Secret of Box Account  |  
|     Access Token            |     Mandatory            |  Provide an Access Token of Box Account  |
|  Refresh Token  |     Mandatory     |  Provide a Refresh Token of Box Account |

To Configure the Proxy

1. Click on the `Configuration` tab next to `Inputs` tab. 
2. Click on the `Proxy` tab. 
3. Provide your Proxy credential and Click on `Save`.

| Proxy Parameters          |   Mandatory or Optional  |                Description                                                             |
|  ----------------------  |   --------------------   |----------------------------------------------------------------------------------------|
|    Enable                |       Optional           |  To enable the proxy                                                      |
|    Proxy Type            |     Mandatory            |  Select proxy type that you want to use from dropdown. The TA supports http proxy only|
|    Proxy Host            |     Mandatory            |  Host or IP of the proxy server                                                        |
|    Proxy Port            |     Mandatory            |  Port for proxy server                                                                 |
|  Proxy Username          |     Optional             |  Username of the proxy server. It is mandatory in case when user has entered `Password`|
|  Proxy Password          |     Optional             |  Password of the proxy server. It is mandatory in case when user has entered `Username`|


1. To configure log-level, Select `Logging`.  
2. Select the log level from dropdown and click on `Save`.
  
### Inputs  
  
1. Go to the apps list and click on `Box Shield Add-on for Splunk`. From the inputs screen, click on `Create New Input`. `Add Box Shield Input` pop-up will open. Provide your credentials and click on `Add` to start the data collection.

Note that if multiple inputs are created with the same global account, there will be duplicate Events in Splunk.
  
| Input Parameter | Mandatory or Optional |                Description                   |  
|  -------------- |    -----------------  |----------------------------------------------|  
|      Name       |      Mandatory        | Provide unique name to uniquely identify a Box details |
|     Interval    |      Mandatory        | Interval in seconds in range of 5 to 60 |
|     Index       |      Mandatory        | Index in which you want to store your data   |
|   Global Account|      Mandatory        | Select previously configured Box Account details|
|   Start Time    |      Optional         | Provide start time in GMT from which Data Collection will start. Time format is  "%Y-%m-%dT%H:%M-00:00"| 

## Search  
  
To see data ingested by `Box Shield Add-on for Splunk`, select the `Search` tab. Search index=<indexname>, where the indexname is the name of the index which is configured in data input.

## External Libraries used

| Libraries(Python)      |  Version   |                Repository link            |                            License                          |
|  --------------      | -----------| ----------------------------------------- |-------------------------------------------------------------|
|   boxsdk         |   2.6.1   | https://github.com/box/box-python-sdk/tree/v2.6.1       | https://github.com/box/box-python-sdk/blob/v2.6.1/LICENSE |
|   attr           |   19.2    | https://github.com/python-attrs/attrs | https://github.com/python-attrs/attrs/blob/master/LICENSE    |
|   enum           |   1.1.6    | https://pypi.org/project/enum34/ |https://github.com/cloudera/hue/blob/master/desktop/core/ext-py/enum34-1.1.6/enum/LICENSE    |
|   chainmap           |   1.0.3    | https://pypi.org/project/chainmap/| https://github.com/jonathaneunice/chainmap/blob/master/LICENSE.txt   |
|   funcsigs           |   1.0.2   | https://pypi.org/project/funcsigs/ | https://github.com/aliles/funcsigs/blob/master/LICENSE   |
|   requests_toolbelt           |   0.9.1    | https://pypi.org/project/requests-toolbelt/ | https://github.com/requests/toolbelt/blob/0.9.1/LICENSE   |
|   wrapt              |  1.11.2   | https://pypi.org/project/wrapt/                       | https://github.com/GrahamDumpleton/wrapt/tree/develop/src/wrapt  |

## Troubleshooting  

* To troubleshoot Box Shield Add-on for Splunk, check $SPLUNK_HOME/var/log/splunk/**ta_box_shield_box_shield_input.log** and $SPLUNK_HOME/var/log/splunk/**ta_box_shield_box_shield_validation.log** files. Also, user can search for ERROR logs in the Splunk using this query `index="_internal" source=ta_box_shield_box_shield*.log ERROR`
* If data collection is not working then ensure that internet is active where proxy is configured and also ensure that kvstore is enabled.
* If data is not being indexed due to `Invalid created_after parameter` error in log, then use the following command:
    kv store- curl -k -u `SPLUNK_USERNAME`:`SPLUNK_PASSWORD` -X DELETE https://localhost:8089/servicesNS/nobody/TA-box- shield/storage/collections/data/TA_box_shield_checkpointer/`INPUTNAME:SOURCETYPE`
    Note: This command will remove the checkpoint data for the provided input name and sourcetype from the kvstore and data collection for that sourcetype will start again from the provided start_time from UI. It may cause duplication of events.
* If data is not being indexed due to `Refresh token has expired` error in log, then reconfigured the credentials of the respective box account.


## Uninstall & Clean-up steps

* Remove $SPLUNK_HOME/etc/apps/TA-box-shield
* Remove $SPLUNK_HOME/var/log/splunk/**ta_box_shield_box_shield_input.log** and $SPLUNK_HOME/var/log/splunk/**ta_box_shield_box_shield_validation.log**
* To reflect the clean-up changes in UI, Restart Splunk Enterprise instance

## Support

* Support Offered: Yes
* Support Email: support@box.com

## Copyright

* Copyright (C) 2020 Box, Inc. and/or its affiliates. All rights reserved.