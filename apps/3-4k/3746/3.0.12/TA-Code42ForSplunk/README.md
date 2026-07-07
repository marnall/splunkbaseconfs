# Welcome to Code42 for Splunk Apps documentation!

# Overview

## About Code42 App For Splunk

|                           |                                                |
| ------------------------- | ---------------------------------------------- |
| Author                    | Aplura, LLC. Code42, Inc.                      |
| App Version               | 3.0.12                                         |
| App Build                 | 250                                            |
| Vendor Products           | Code42 Appliance                               |
| Has index-time operations | false                                          |
| Creates an index          | false                                          |
| Implements summarization  | Currently, the app does not generate summaries |

About Code42 App For Splunk

Code42 App For Splunk allows a Splunk Enterprise administrator to extract information and knowledge from Code42.

## Scripts and binaries

This App provides the following scripts:

## Release notes

### Version 3.0.11

  - Improvement
    
      - [C42-87] Fix for data ingestion delay

### Version 3.0.10

  - Improvements
    
      - Changes to C42 SDK to better enhance stability and data consumption

### Version 3.0.9

  - Improvement
    
      - [C42-84] - Use is_cloud from Utilities

### Version 3.0.8

  - Bug
    
      - [C42-83] - Bug in Batch Processor - Cursor not retrieved correctly

## About this release

Version 3.0.12 of Code42 App For Splunk is compatible with:

|                            |                                    |
| -------------------------- | ---------------------------------- |
| Splunk Enterprise versions | 6.6, 7.0, 7.1, 7.2                 |
| Platforms                  | Splunk Enterprise                  |
| Vendor Platform            | Code42 Enterprise / Small Business |

Compatability

## Known Issues

Version 3.0.12 of Code42 App For Splunk has the following known issues:

  - None

# Support and resources

## Questions and answers

Access questions and answers specific to Code42 App For Splunk at [https://answers.splunk.com](https://answers.splunk.com) . Be sure to tag your question with the App.

## Support

  - Support Email: [enterprise-support@code42.com](mailto:enterprise-support%40code42.com)
  - Support Offered: Email

Support is available via email at [enterprise-support@code42.com](mailto:enterprise-support%40code42.com). Responses vary on working days between working hours.

# Installation and Configuration

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements]([https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements)) apply.

## Download

Download Code42 App For Splunk at [https://splunkbase.splunk.com/app/3736/](https://splunkbase.splunk.com/app/3736/).

## Installation steps

NOTE: Where referenced, TA-Code42ForSplunk and IA-Code42ForSplunk are located on Splunkbase.

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Download the Code42 App For Splunk package from [https://splunkbase.splunk.com/app/3736/](https://splunkbase.splunk.com/app/3736/)
2.  Install the App via the recommended installation methods (CLI, Web GUI)
3.  Restart Splunk.
4.  Download IA-Code42ForSplunk from [https://splunkbase.splunk.com](https://splunkbase.splunk.com)
5.  Install IA via the recommended installation methods (CLI, Web GUI)
6.  Navigate to IA-Code42ForSplunk/App_Config to setup modular input settings.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation.

### Deploy to distributed deployment

#### Install to search head

1.  Download the Code42 App For Splunk package from [https://splunkbase.splunk.com/app/3736/](https://splunkbase.splunk.com/app/3736/)
2.  Install the App via the recommended installation methods (CLI, Web GUI, Deployment Server)

#### Install to indexers

1.  Download the TA-Code42ForSplunk package from [https://splunkbase.splunk.com](https://splunkbase.splunk.com).
2.  Install TA-Code42ForSplunk onto the indexers per your environment.

#### Install to universal forwarders

1.  There is no installation to Universal Forwarders.

#### Install to Heavy Forwarders

1.  Download the IA-Code42ForSplunk package from [https://splunkbase.splunk.com](https://splunkbase.splunk.com).
2.  Install IA-Code42ForSplunk onto a heavy forwarder in your environment.
3.  Configure the Modular Input with the required settings.

#### Deploy to distributed deployment with Search Head Clustering

1.  Place the App into the deploy_apps folder on the Deployer Server.
2.  Follow the instructions to install to a Heavy Forwarder. This Step is REQUIRED in a clustered SH environment!
3.  Deploy the App to the Search Head Cluster. DO NOT install IA-Code42ForSplunk to the Cluster!

# User Guide

## Configure Code42 App For Splunk

  - Install the App according to your environment (see steps above)
  - Navigate to App > IA-Code42ForSplunk > Administration > Application Configuration

### Application Configuration Dashboard

To configure the Code42 application you should start on the Application Configuration page (Administration > Application Configuration)\*[]:

### Application Configuration

On this screen you can set the base index as well as a flag that specifies that the application is configured. In the future there will be additional configurations available.

### Proxy Configuration

If you have configured a proxy server you can view the configuration under this tab. These are proxy server configurations that are being used by existing modular inputs for the Code42 application. You can also delete existing proxy configurations on this tab.

### Encrypted Credentials

You can view/delete existing credentials on this tab. These are credentials that are being used by existing modular inputs in the Code42 application. These credentials are the credentials used to connect to Code42 appliances.

### Code42

On this screen you can view and make any changes to existing modular inputs. As you make changes and tab between fields the modular input is modified.

### Creating New Proxy Configurations

If you need to use a proxy as part of the connection to the Code42 appliance configure it here.

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

### Creating New Code42 Inputs

**NOTE:** You will need to configure a new modular input for each appliance

  - To create a new data input, click the Create New Modular Input button and fill in the following fields. Those with a red asterisk on the screen are required.
      - Modular Input Name: Name for the data input configuration.
      - Hostname and port: The hostname or IP address and port of the Code42 appliance. By default you can specify hostname:443.
      - Username: The username used to connect to the appliance. This user should have a of role of Security Center User, Customer Cloud Admin, or Server Admin.
      - Password: The password for the previously specified username.
      - Toggle all data keys: Check to select all data keys.
      - Data keys: List of endpoints available on the Code42 appliance. Check the data key if you wish to pull event data.
      - Historical Lookback: This is the number of days to lookback for Security Events. Default is 60.
      - Interval: The number of seconds indicate how often the input will poll for new data. This setting must be at least 60.
      - Index: This sets the index for data to be written to. This setting should be changed from default, which normally writes to the main index, to a specified index for best performance.
      - Use Proxy: Indicates if a proxy should be use for communication with the Code42 appliance.
      - Proxy Name: Enter the name of the proxy stanza to use with the input.
  - After creating the modular input you may need to disable/re-enable the input in Settings > Data Inputs > Code42 App For Splunk to activate the input.

**NOTE:** When configuring the modular input through the Application Configuration dashboard, the password is automatically encrypted into the credential store. If you need to change the credential, create a new credential, and reference the host/user pair in the modular input configuration. An encrypted credential is required for this Splunk App.

## Indexes

By default all events will be written to the main index. You should change the index in the configuration files to match your specific index.

## Troubleshoot Code42 App For Splunk

1.  Check the Monitoring Console (>=v6.5) for errors
2.  Visit the Application Health dashboard

## Full Data Reset

If you experiencing issues, and would like to reset the Code42 Data to factory install, there are few steps to take.

1.  Disable the input.
2.  Clear the indexed data. This is covered in the [Splunk documentation](http://docs.splunk.com/Documentation/Splunk/7.2.0/Indexer/RemovedatafromSplunk#How_to_use_the_clean_command)
3.  Clear the KVStore that is tracking the cursors using the search ``|`code42_zero_cursors` ``
4.  Enable the input.

## Lookups

Code42 App For Splunk contains three automatically generated lookups.

The following lookup files are generated automatically from saved searches every hour.

  - code42_users.csv
  - code42_computers.csv
  - code42_alertlog.csv

## Event Generator

Code42 App For Splunk does make use of an event generator. This allows the product to display data, when there are no inputs configured.

The stanzas are:

  - code42_org.eventgen
  - code42_security.eventgen
  - code42_computer.eventgen
  - code42_restore.eventgen
  - code42_user.eventgen
  - code42_alertlog.eventgen

## Acceleration

1.  Summary Indexing: No
2.  Data Model Acceleration: No
3.  Report Acceleration: No

# Third Party Notices

Version 3.0.12 of Code42 App For Splunk incorporates the following Third-party software or third-party services .

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
  - Redistributions in binary form must reproduce the above copyright notice, this list of conditions and the following disclaimer in the documentation and/or other materials provided with the distribution.
  - Neither the name of the author nor the names of contributors may be used to endorse or promote products derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS AS IS AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

### Related Topics

  - [Documentation overview](index.html#document-index)

2017, Aplura, LLC. | Powered by [Sphinx 1.6.4](http://sphinx-doc.org/) & [Alabaster 0.7.10](https://github.com/bitprophet/alabaster)
