# Welcome to Netskope App for Splunks documentation!

# Overview

## About Netskope App For Splunk

|                           |                                                |
| ------------------------- | ---------------------------------------------- |
| Author                    | Netskope, Inc.                                 |
| App Version               | 1.2.0                                          |
| App Build                 | 252                                            |
| Vendor Products           | Netskope API 48                                |
| Has index-time operations | true                                           |
| Creates an index          | false                                          |
| Implements summarization  | Currently, the app does not generate summaries |

About Netskope App For Splunk

The Netskope App for Splunk integrates with the Netskope service to provide value and insight into your data.

# Scripts and binaries

This App provides the following scripts:

|                         |                                                                       |
| ----------------------- | --------------------------------------------------------------------- |
| bin/netskope.py         | The Modular Input used to communicate and consume the API data.       |
| netskope_client.py     | This chunk of Python contains the Modular Input Classes for Netskope. |
| netskope_url.py        | Alert Action script for URL lists.                                    |
| netskope_file_hash.py | Alert Action script for file hash lists.                              |
| Diag.py                 | Allows diag-targeted collection of information.                       |
| ModularInput.py         | Inheritable Class to create Modular Inputs                            |
| RESTClient.py           | Inheritable Class to create REST clients                              |
| Utilities.py            | Allows utility interactions with Splunk Endpoints                     |

Scripts

# Release notes

## Version 1.2.0

  - New Feature
    
      - [NET-114] - Web Transaction Logs

  - Improvement
    
      - [NET-115] - Request for Changes in Splunk API call

# About this release

Version 1.2.0 of Netskope App For Splunk is compatible with:

|                            |                   |
| -------------------------- | ----------------- |
| Splunk Enterprise versions | 7.0, 7.1, 7.2     |
| Platforms                  | Splunk Enterprise |
| Vendor Platform            | Netskope API 48   |

Compatability

# Known Issues

Version 1.2.0 of Netskope App For Splunk has the following known issues:

  - None

Version 1.1.0 of Netskope App For Splunk has the following known issues:

  - The macro `netskope_configured_inputs` is not configured to use a generating command, therefore the dashboards are failing to create the filtering search.

Version 1.0.3 (83) of Netskope App For Splunk has the following known issues:

  -   - Application Detail and Alert Detail dashboards will not work in Splunk 6.4 due to token incompatibilities.
        
          - Resolution: Change the count \<option> in the XML and restart Splunk.

# Support and resources

## Questions and answers

Access questions and answers specific to Netskope App For Splunk at [https://answers.splunk.com](https://answers.splunk.com) . Be sure to tag your question with the App.

## Support

  - Support Email: [support@netskope.com](mailto:support%40netskope.com)
  - Support Offered: Email

Support is available via email at [support@netskope.com](mailto:support%40netskope.com). Responses vary on working days between working hours.

# Installation and Configuration

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements]([https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements)) apply.

## Download

Download Netskope App For Splunk at [https://splunkbase.splunk.com/app/3414/](https://splunkbase.splunk.com/app/3414/).

## Installation steps

NOTE: Where referenced, TA-NetSkopeAppForSplunk and IA-NetSkopeAppForSplunk are located on Splunkbase.

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Download the Netskope App For Splunk package from [https://splunkbase.splunk.com/app/3414/](https://splunkbase.splunk.com/app/3414/)
2.  Install the App via the recommended installation methods (CLI, Web GUI)
3.  Restart Splunk.
4.  Navigate to App_Config to setup modular input settings.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation.

### Deploy to distributed deployment

#### Install to search head

1.  Download the Netskope App For Splunk package from [https://splunkbase.splunk.com/app/3414/](https://splunkbase.splunk.com/app/3414/)
2.  Install the App via the recommended installation methods (CLI, Web GUI, Deployment Server)

#### Install to indexers

1.  Download the TA-NetSkopeAppForSplunk package from [https://splunkbase.splunk.com](https://splunkbase.splunk.com).
2.  Install TA-NetSkopeAppForSplunk onto the indexers per your environment.

#### Install to universal forwarders

1.  There is no installation to Universal Forwarders.

#### Install to Heavy Forwarders

1.  Download the IA-NetSkopeAppForSplunk package from [https://splunkbase.splunk.com](https://splunkbase.splunk.com).
2.  Install IA-NetSkopeAppForSplunk onto a heavy forwarder in your environment.
3.  Configure the Modular Input with the required settings.

#### Deploy to distributed deployment with Search Head Clustering

1.  Place the App into the deploy_apps folder on the Deployer Server.
2.  Deploy the App to the Search Head Cluster. DO NOT install IA-NetSkopeAppForSplunk to the Cluster!

# User Guide

## Configure Netskope App For Splunk

  - Install the App according to your environment (see steps above)
  - Navigate to App > IA-NetSkopeAppForSplunk > Administration > Application Configuration

### Application Configuration Dashboard

To configure the Netskope application you should start on the Application Configuration page (Administration > Application Configuration)\*[]:

### Application Configuration

On this screen you can set the base index as well as a flag that specifies that the application is configured. In the future there will be additional configurations available.

### Proxy Configuration

If you have configured a proxy server you can view the configuration under this tab. These are proxy server configurations that are being used by existing modular inputs for the Netskope application. You can also delete existing proxy configurations on this tab.

### Encrypted Credentials

You can view/delete existing credentials on this tab. These are credentials that are being used by existing modular inputs in the Netskope application. These credentials are the credentials used to connect to Netskope appliances.

### Netskope

On this screen you can view and make any changes to existing modular inputs. As you make changes and tab between fields the modular input is modified.

### Creating New Proxy Configurations

If you need to use a proxy as part of the connection to Netskope, configure it here.

  - To create a new proxy server configuration, click the Create New Proxy button and fill in the following fields:
    
      - Proxy Name: Name for the proxy configuration. This name will be used as the proxy name in the modular input configuration.
      - Host: Proxy host name or IP.
      - Port: Port used to connect to the proxy server.
      - Username: Username used to connect to the proxy server.
      - Password: Password for the username specified above.
      - Use SSL: Should SSL be used for the proxy configuration?

### Creating New Credentials

By default creating a new modular input with a username and password specified will create the necessary encrypted credentials. However if you want to create encrypted credentials manually follow this process:

  - To create a new encrypted credential, click the Create New Credential button and fill in with the appropriate username and password.
  - The realm is the application name where the encrypted credential is created + the username.

*NOTE: By default creating a new modular input will automatically create a new encrypted credential so this process is not necessary unless you need a new credential for another purpose.*

### Creating New Netskope Inputs

**NOTE:** You will need to configure a new modular input for each Netskope url

  -   - To create a new modular input configuration click Create New Modular Input.
        
          - Modular Input Name: Name for the modular input configuration.
          - URL: The URL provided for the Netskope instance without the [https://](https://) portion of the address.
          - Limit: The maximum number of events to collect on each interval, with a maximum of 5000.
          - Interval: The number of seconds between data collections.
          - Event Type: The type(s) of event(s) to collect separated by commas. Valid types are connection, alert, audit, infrastructure, and/or application.
          - Encrypted Token: Should the token be encrypted.
          - Token: The API token generated by Netskope for the instance.
          - Use Proxy: Will a proxy server be used.
          - Proxy Name: Name of the stanza configured in the proxy configuration.

This will configure the modular input settings in the SPLUNK_HOME/etc/apps/NetskopeAppForSplunk/local/inputs.conf. These settings are available under the modular input tab on the Application Configuration page as well as the data input page under Settings>Data Inputs>Netskope. If the token is to be encrypted then the encrypted token will be written to the encrypted credential store and the token on the modular input will show the value that used to retrieve the encrypted token.

NOTE: To make sure that the modular input gets enabled properly navigate to Settings>Data Inputs>Netskope> and press Disable then press Enable to enable the modular input.

All proxy, encrypted credential and modular input configurations are available in the tabs on the Application Configuration page.

## Netskope and Enterprise Security

Netskope ships with the knowledge objects required for Enterprise Security integration. These objects need to be imported to Enterprise Security. This can be done in two ways:

  -   - Netskope App
        
          - If dashboards are required, install the App
          - This will also require app import settings to be updated in the Enterprise Security [App Import](https://docs.splunk.com/Documentation/ES/latest/Install/ImportCustomApps) settings.

  -   - Netskope TA
        
          - If dashboards are not required, install the TA.
          - App import settings of Enterprise Security will not need to be modified.

  - Do not install both the App and the TA on the Enterprise Security server. This may cause a precedence import error.

  - The default `netskope_idx` event type will need to be updated to properly locate the data for the Data Models of Enterprise Security.

## Netskope Alert Actions

Netskope App For Splunk v1.0.6 introduces 2 alert actions, File Hash and URL lists. In order to use the Adaptive responses, a corresponding list must be created in the Netskope product. The list *must* have the same name for both URL and file hash lists.

1.  Configure the Adaptive Response Global configuration under the `Application Configuration` page of the TA/App.
2.  Click the button labeled `Create New Netskope Alert Action Global Configuration` and fill out the fields for hostname, token, and list.
3.  Once saved, you can then use the Alert Actions to either add or remove items from the lists. When configuring the Alert Action, you can choose either `Add` or `Remove` and the field name that contains the value to update.
4.  Please see the [Adaptive Response in Enterprise Security](https://docs.splunk.com/Documentation/ES/5.2.0/User/Takeactiononanotableevent#Run_an_adaptive_response_action) documentation on how to run Adaptive Responses in Enterprise Security.
5.  Please see the [Alerts](http://docs.splunk.com/Documentation/Splunk/7.2.1/Alert/Aboutalerts) documentation to create your own alerts and corresponding actions.

NOTE: When running adaptive responses from the Incident Review dashboard in Enterprise Security, the results are written to the notable index. If this needs changed, please contact support.

## Netskope Time Offset

Netskope App For Splunk v1.1.2 introduces the ability to specify a time offset.This setting allows the user to specify an offset to be used to retrieve events that start further back in time. Example: the modular input runs and pulls events between 6:00 AM and 12:00 PM. Because the Netskope API may not process some events in real-time some events may not be available from the API until a later period. To handle this the Splunk admin can specify a time offset to go backwards to pull events.

1.  Configure the time offset in the `inputs.conf` configuration file in the local folder of the IA/App.
2.  This offset is only available in the inputs.conf file. To disable the time offset set this value to 0. To specify an offset specify the number of seconds to go back in time. Default is 0.

NOTE: This is an advanced setting and should only be set when directed by support. NetSkope support will guide you with the appropriate setting for your environment.

Customers running Enterprise Security (or any searches using a small timeframe): Some correlation searches in ES only look back 60 minutes. Using an offset may cause the searches in ES (or small timeframe searches) may not work properly. Therefore it may be necessary to tune some correlation searches to account for the offset.

## Indexes

By default all events will be written to the main index. You should change the index on the modular input to match your specific index.

## Troubleshoot Netskope App For Splunk

1.  Check the Monitoring Console (`>=v6.5`) for errors
2.  Visit the `Application Health` dashboard

Another troubleshooting method for the Netskope App For Splunk app is using this search:

`sourcetype=` NetSkopeAppForSplunk `:error`

If you are still having problems, use the Command line and run this command:

`$SPLUNK_HOME/bin/splunk diag --collect app:NetSkopeAppForSplunk`

Send the generated diag file to Netskope App For Splunk support.

### Update log.cfg

Copy the `log.cfg` file from `default` of the app to the `local` folder, and edit the settings to reflect which items need increased verbosity.

## Upgrade Netskope App For Splunk

Upgrade Netskope App For Splunk by re-installing into your environment per Splunk Documentation and your environment (see steps above).

## Full Data Reset

If you experiencing issues, and would like to reset the Netskope Data to factory install, there are few steps to take.

1.  Disable the input.
2.  Clear the indexed data. This is covered in the [Splunk documentation](http://docs.splunk.com/Documentation/Splunk/7.2.0/Indexer/RemovedatafromSplunk#How_to_use_the_clean_command)
3.  Delete the checkpoint files in `$SPLUNK_HOME/var/lib/splunk/modinputs/netskope`
4.  Enable the input.

## CIM Compatibility

The Netskope App for Splunk is fully compliant with the Common Information Model (CIM) provided by Splunk to normalize data fields. This table indicates the CIM datamodels and tags that apply to the Netskope data.

| Datamodel            | Tags                        | Eventtypes                                                               |
| -------------------- | --------------------------- | ------------------------------------------------------------------------ |
| Alert                | alert                       | netskope_cim_alert                                                     |
| Change               | change, audit               | netskope_audit                                                          |
| Data Loss Prevention | dlp                         | netskope_cim_application, netskope_cim_alert                         |
| Inventory            | inventory                   | netskope_cim_connection, netskope_clients, netskope_infrastructure   |
| Malware              | malware, attack, operations | netskope_cim_malware, netskope_cim_application, netskope_cim_alert |
| Network Traffic      | network, communicat         | netskope_cim_connection                                                |
| Splunk Audit Logs    | modaction                   | netskope_action_modresult                                              |
| Web                  | web, proxy                  | netskope_cim_web                                                       |

CIM Mappings

## Lookups

Netskope App For Splunk contains no automatically generated lookups.

The following lookup files are generated automatically during Alert Action operations.

  - netskope_file_hash.csv
  - netskope_url.csv

## Event Generator

Netskope App For Splunk does make use of an event generator. There are four sample event files supplied for event generation. These samples are found in the samples folder of the app and are:

  - netskope_alert.sample
  - netskope_application.sample
  - netskope_audit.sample
  - netskope_connection.sample

**NOTE:** To generate events the Eventgen app must be installed. The app and instructions can be found at [https://splunkbase.splunk.com/app/1924/](https://splunkbase.splunk.com/app/1924/). This app should not be installed on a production system unless you understand the ramifications of generated data being mixed with production data.

## Acceleration

1.  Summary Indexing: No
2.  Data Model Acceleration: No
3.  Report Acceleration: No

# Third Party Notices

Version 1.2.0 of Netskope App For Splunk incorporates the following Third-party software or third-party services .

## Aplura, LLC Components

Components Written by Aplura, LLC Copyright (C) 2016-2017 Aplura, ,LLC

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA 02110-1301, USA.

## defusedxml

## defusedxml

PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2

1\. This LICENSE AGREEMENT is between the Python Software Foundation (PSF), and the Individual or Organization (Licensee) accessing and otherwise using this software (Python) in source or binary form and its associated documentation.

2\. Subject to the terms and conditions of this License Agreement, PSF hereby grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce, analyze, test, perform and/or display publicly, prepare derivative works, distribute, and otherwise use Python alone or in any derivative version, provided, however, that PSFs License Agreement and PSFs notice of copyright, i.e., Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008 Python Software Foundation; All Rights Reserved are retained in Python alone or in any derivative version prepared by Licensee.

3\. In the event Licensee prepares a derivative work that is based on or incorporates Python or any part thereof, and wants to make the derivative work available to others as provided herein, then Licensee hereby agrees to include in any such work a brief summary of the changes made to Python.

4\. PSF is making Python available to Licensee on an AS IS basis. PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED. BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.

5\. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON, OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.

6\. This License Agreement will automatically terminate upon a material breach of its terms and conditions.

7\. Nothing in this License Agreement shall be deemed to create any relationship of agency, partnership, or joint venture between PSF and Licensee. This License Agreement does not grant permission to use PSF trademarks or trade name in a trademark sense to endorse or promote products or services of Licensee, or any third party.

8\. By copying, installing or otherwise using Python, Licensee agrees to be bound by the terms and conditions of this License Agreement.

## markdown.js

Released under the MIT license.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## jquery.js

[https://github.com/jquery/jquery/blob/master/LICENSE.txt](https://github.com/jquery/jquery/blob/master/LICENSE.txt)

Copyright JS Foundation and other contributors, [https://js.foundation/](https://js.foundation/)

This software consists of voluntary contributions made by many individuals. For exact contribution history, see the revision history available at [https://github.com/jquery/jquery](https://github.com/jquery/jquery)

The following license applies to all parts of this software except as documented below:

-----

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the Software), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED AS IS, WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

-----

All files located in the node_modules and external directories are externally maintained libraries used by this software which have their own licenses; we recommend you read them, as their terms may differ from the terms above.

## d3.js

[https://github.com/d3/d3/blob/master/LICENSE](https://github.com/d3/d3/blob/master/LICENSE)

Copyright 2010-2016 Mike Bostock All rights reserved.

Redistribution and use in source and binary forms, with or without modification, are permitted provided that the following conditions are met:

  - Redistributions of source code must retain the above copyright notice, this list of conditions and the following disclaimer.
  - Redistributions in binary form