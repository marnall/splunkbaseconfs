# Welcome to CB ThreatHunter for Splunk Apps documentation!

# Overview

## About CB ThreatHunter For Splunk

|                           |                                                          |
| ------------------------- | -------------------------------------------------------- |
| Author                    | Aplura, LLC                                              |
| App Version               | 1.0.0                                                    |
| App Build                 | 27                                                       |
| Vendor Products           | CB ThreatHunter on the CarbonBlack PSC                   |
| Has index-time operations | true, the Modular Input configurations must be in place. |
| Creates an index          | false                                                    |
| Implements summarization  | Currently, the app does not generate summaries           |

About CB ThreatHunter For Splunk

CB ThreatHunter For Splunk allows a Splunk Administrator to connect to and pull notifications from the CarbonBlack Predictive Security Cloud, with a focus on ThreatHunter information.

## Scripts and binaries

This App provides the following scripts:

# Release notes

## Version 1.0.0

  - Bug
    
      - [CB-7] - Update Checklist.conf

  - New Feature
    
      - [CB-2] - Create Modular Input
      - [CB-4] - Create REST Client
      - [CB-5] - Dashboards - Initial Set
      - [CB-6] - Documentation Update

  - Task
    
      - [CB-8] - Update Web Tests
      - [CB-14] - Documentation and Final Builds

  - Improvement
    
      - [CB-9] - Event Generator
      - [CB-13] - Threat Action Dashboard Enhancements

## About this release

Version 1.0.0 of CB ThreatHunter For Splunk is compatible with:

|                            |                   |
| -------------------------- | ----------------- |
| Splunk Enterprise versions | 7.1, 7.2          |
| Platforms                  | Splunk Enterprise |

Compatability

## Known Issues

Version 1.0.0 of CB ThreatHunter For Splunk has the following known issues:

  - None

# Support and resources

## Questions and answers

Access questions and answers specific to CB ThreatHunter For Splunk at [https://answers.splunk.com](https://answers.splunk.com) . Be sure to tag your question with the App.

## Support

  - Support Offered: Community Engagement

# Installation and Configuration

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all of the [Splunk Enterprise system requirements]([https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements)) apply.

## Download

Download CB ThreatHunter For Splunk at [https://splunkbase.splunk.com](https://splunkbase.splunk.com).

## Installation steps

NOTE: Where referenced, the IA-cb_psc_for_splunk and TA-cb_psc_for_splunk versions of this App are located on Splunkbase.

### Deploy to single server instance

Follow these steps to install the app in a single server instance of Splunk Enterprise:

1.  Deploy as you would any App, and restart Splunk.
2.  Configure.

### Deploy to Splunk Cloud

1.  Have your Splunk Cloud Support handle this installation. Do NOT install the IA on the same system as the App.
2.  You may consider using an on-premise Heavy Forwarder to install IA-cb_psc_for_splunk, and send the logs to Splunk Cloud.

### Deploy to a Distributed Environment

1.  For each Search Head in the environment, deploy a configured copy of the App. DO NOT SEND TA or IA to a Search Head Cluster (SHC).
2.  For each indexer in the environment, deploy a copy of the TA-cb_psc_for_splunk Add-On that is located as mentioned above.
3.  For a single Data Collection Node OR Heavy Forwarder (a full instance of Splunk is required), install IA-cb_psc_for_splunk and configure through the GUI.

# User Guide

## Key concepts for CB ThreatHunter For Splunk

1.  Make sure the event type is configured properly for the App on the `Application Configuration` page. This will determine if the data is visible in the App.

## Modular Input

**NOTE:** You will need to configure a new modular input for each tenant

  - Navigate to the Application Configuration dashboard to configure the modular input.
  - Click the `Create New CB ThreatHunter Input`.
  - Fill out the form.
      - Modular Input Name: Name for the data input configuration.
      - Hostname: The hostname of CarbonBlack tenant you have been assigned.
      - Token: The API key retrieved from the CarbonBlack interface.
      - Connector ID: The connector that is used with the API key to pull the notification data.
      - Interval: The number of seconds indicate how often the input will poll for new data. This setting must be at least 120.
      - Index: This sets the index for data to be written to. This setting should be changed from default, which normally writes to the main index, to a specified index for best performance.
      - Proxy Name: Enter the name of the proxy stanza to use with the input.

**NOTE:** When configuring the modular input through the Application Configuration dashboard, the password is automatically encrypted into the credential store. If you need to change the credential, create a new credential, and reference the realm/connector id pair in the modular input configuration. An encrypted credential is required for this Splunk App.

## Indexes

By default all events will be written to the main index. You should change the index in the modular input setup to specify a custom location.

## Configure Proxy Support

This App Supports proxy configuration. Configure the proxy first in the `Application Configuration` dashboard on the Proxy Tab, and then choose it during the modular input configuration.

## Troubleshoot CB ThreatHunter For Splunk

1.  Check the Monitoring Console (>=v6.5) for errors
2.  Visit the Application Health dashboard
3.  Search for eventtype=cbthreathunter_api_errors
4.  Collect logs and send to support: `$SPLUNK_HOME/bin/splunk diag --collect app:cb_psc_for_splunk`

## Lookups

CB ThreatHunter For Splunk contains no lookup files.

## Event Generator

CB ThreatHunter For Splunk does make use of an event generator. This allows the product to display data, when there are no inputs configured. To enable them, visit the `Application Configuration` page, Eventgen Configuration tab.

  - cb_threathunter_notification_policy.json.sample
  - cb_threathunter_notification_summary.json.sample
  - cb_threathunter_notification_threat.json.sample
  - cb_threathunter_new_threat_notification.json.sample
  - cb_threathunter_threat_info.json.sample

## Acceleration

1.  Summary Indexing: No
2.  Data Model Acceleration: No
3.  Report Acceleration: No

# Third Party Notices

Version 1.0.0 of CB ThreatHunter For Splunk incorporates the following Third-party software or third-party services .

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
