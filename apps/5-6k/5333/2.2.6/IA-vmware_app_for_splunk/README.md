# VMware Carbon Black Cloud Documentation

Provides a view into VMware Carbon Black Cloud using events and alerts from the CBC.

|                            |                                          |
|----------------------------|------------------------------------------|
| Version                    | 2.2.6                                    |
| Release Date               | 2026-03-24                               |
| Build                      | 221                                      |
| Splunk Enterprise Versions | 10.2, 10.1, 10.0, 9.4, 9.3               |
| Platforms                  | Splunk Enterprise, Splunk Cloud          |
| Splunkbase Url             | <https://splunkbase.splunk.com/app/5332> |
| Author                     | Aplura, LLC                              |

## Overview

The VMware Carbon Black Cloud App for Splunk is a single application to integrate your endpoint and workload security features and telemetry directly into Splunk dashboards, workflows and alert streams.

This application connects with any Carbon Black Cloud offering and replaces the existing product-specific Carbon Black Cloud apps for Splunk. This app provides a unified solution to integrate Carbon Black Cloud Endpoint and Workload offerings with Splunk Enterprise, Splunk Cloud, and Splunk Enterprise Security (ES). Out-of-the-box, this app provides holistic visibility into the state of your endpoints and workloads through customizable dashboards and alert feeds in Splunk.

## Quick Links

- [Introduction to version 2.0](https://www.youtube.com/watch?v=H-YdqmF4oPk&t=1s&ab_channel=CarbonBlack)

- [App Setup and Configuration](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk-app/#app-setup-and-configuration)

- [FAQ & Troubleshooting](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk/faq-troubleshooting)

- [Release Notes](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk/release-notes)

- [Support](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk-app/#support-and-resources)

- [User Guide](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk/user-guide)

## License

MIT

Copyright 2021, Aplura, LLC.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Scripts and binaries

For more information on these scripts, and what they do, please refer to the [App Setup and Configuration](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk-app/#app-setup-and-configuration) and the [User Guide](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk/user-guide).

### binary file declaration

This app does not include any binary files. All vendored Python dependencies are pure Python.

### script file declaration

This app includes the following scripts:

|                                     |                                                                                                               |
|-------------------------------------|---------------------------------------------------------------------------------------------------------------|
| vmware-cbc-alerts.py                | This is the modular input for the VMware Carbon Black Alerts API Integration.                                 |
| vmware-cbc-vuln.py                  | This is the script for the VMware Carbon Black Vulnerabilities API integration.                               |
| vmware-cbc-audit.py                 | This is the script for the VMware Carbon Black Audit Logs API integration.                                    |
| vmware-cbc-live-query.py            | This is the script for the VMware Carbon Black Live Query Results API integration.                            |
| vmware-cbc-clients.py               | This is the base client for the VMware Carbon Black API Integration.                                          |
| vmware-add-ioc-watchlist.py         | This is the script for the VMware Carbon Black Alerts Add IoC to Watchlist alert action.                      |
| vmware-get-file-metadata.py         | This is the script for the VMware Carbon Black Alerts Get File Metadata alert action.                         |
| vmware-kill-process.py              | This is the script for the VMware Carbon Black Alerts Kill Process alert action.                              |
| vmware-list-process.py              | This is the script for the VMware Carbon Black Alerts List Process alert action.                              |
| vmware-quarantine-device.py         | This is the script for the VMware Carbon Black Alerts Quarantine Device alert action.                         |
| vmware-remove-ioc-watchlist.py      | This is the script for the VMware Carbon Black Alerts Remove IoC From Watchlist alert action.                 |
| vmware-unquarantine-device.py       | This is the script for the VMware Carbon Black Alerts Unquarantine Device alert action.                       |
| vmware-close-alert.py               | This is the script for the VMware Carbon Black Alerts Dismiss Alerts alert action.                            |
| vmware-enrich-events.py             | This is the script for the VMware Carbon Black Alerts Enrich Events alert action.                             |
| vmware-process-guid-details.py      | This is the script for the VMware Carbon Black Alerts Process GUID details alert action.                      |
| vmware-run-livequery.py             | This is the script for the VMware Carbon Black Alerts Run Livequery alert action.                             |
| vmware-update-device-policy.py      | This is the script for the VMware Carbon Black Alerts Update Device Policy alert action.                      |
| vmware-cmd-dvc-info.py              | This is the script for the VMware Carbon Black Custom Command for Device Information enrichment (cbcdvcinfo). |
| vmware-cmd-hash-info.py             | This is the script for the VMware Carbon Black Custom Command for Hash information (cbchashinfo).             |
| vmware-enrich-alert-obs.py          | This is the script for the VMware Carbon Black Alert Action for Observations based on alert ids.              |
| AlertAction.py                      | An alert action base class.                                                                                   |
| ModularInput.py                     | A modular input base class.                                                                                   |
| Utilities.py                        | A helper utility script to interface with Splunk                                                              |
| cbc_upgrader.py                     | A helper script for upgrading the VMware Carbon Black Cloud app.                                              |
| cim_actions.py                      | A CIM-app provided helper for adaptive response actions.                                                      |
| variables.py (deprecated)           | A generated python script for constants within the scripts to keep consistency.                               |
| app_properties.py (deprecated)      | A generated python script for constants within the scripts to keep consistency.                               |
| version.py (deprecated)             | The vmware_app_for_splunk version. Currently is 2.2.6b221                                                     |
| vmware-ban-hash.py                  | AlertAction script for banning hashes.                                                                        |
| vmware_cbc_client.py                | Master client script to interface with various components of VMWare CBC                                       |
| vmware-cbc-authentication-events.py | Modular Input for Authentication Events                                                                       |
| vmware_cbc_alert_actions.py         | Alert Actions Class for VMware alert actions                                                                  |
| vmware-alert-history.py             | Python for the Alert History Alert Action.                                                                    |
| vmware_cbc_utilities.py             | VMware specific utilities.                                                                                    |
| vmware_cbc_cmd.py                   | VMware Custom Command class.                                                                                  |
| Diag.py                             | A helper script to generate VMware Carbon Black Cloud specific diagnostic files.                              |
| \_paths.py                          | A Helper script that pulls in and sets local lib path.                                                        |
| vmware_app_for_splunk_props.py      | App-scoped properties.                                                                                        |

## Event Generator

An event generator is not included.

## Data Model Acceleration

Data model acceleration will only occur if the enabled via UI. This app contains 1 Data Model (`VMWare_CBC`).

## Upgrader

VMWare CBC includes `cbc_upgrader` modular input to assist in app upgrades. It is located in input `cbc_upgrader://B309635C-9A2D-4535-B78C-4FFC3F198901`

## Other Settings

VMware Carbon Black Cloud includes specific fields related to CIM mapping.

- vmwaudcimlkup

  - Assists with the Audit Log input and CIM Mapping.

## Configuration Notes

<div class="note">

During configuration of the inputs, there are buttons that can be used to test the API configuration against the live API endpoints. The test for "API Configuration" (not an input configuration) does NOT use any configured proxies. If you need to test a proxy configuration, use the input configuration check to make sure the proxy is working as intended.

</div>

# Installation

Please see [App Setup and Configuration](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk-app/#app-setup-and-configuration) for more information.

# WINDOWS INSTALLATION

Due to the need for a binary (`backports`), the Splunk Admin must run a command line operation to provide the Windows binary. This binary is included in the package for Linux-based systems, but not Windows.

Open an `Administrative cmd prompt`, and execute the following commands. Substitute paths for your environment, these are from a standard installation. `<APP>` is whichever VMWare Splunk App was installed.

    cd "C:\Program Files\Splunk\etc\apps\<APP>\lib"`
    "C:\Program Files\Splunk\bin\splunk.exe" cmd python3 -m pip install --upgrade -t . backports._datetime_fromisoformat==2.0.1

## Software requirements

The [Splunk CIM Add-on](https://splunkbase.splunk.com/app/1621/) is a required pre-requisite.

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements ](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

### Download

Download VMware Carbon Black Cloud at <https://splunkbase.splunk.com/app/5332>.

## Release Notes

### v2.2.5

- Removed python files to comply with AppInspect check `check_prohibited_python_filenames` (`defusedxml` package)

### v2.2.4

- Converted `Audit Logs` input from URL/time based to the new Queue based ingest method.

  - <https://developer.carbonblack.com/reference/carbon-black-cloud/guides/api-migration/audit-log-migration/>

### v2.2.3

- Upgraded `splunk-sdk` to latest version to pass Splunk AppInspect

- Clarified results of API `Test Config` messages.

### v2.2.2

- Improvement

  - The IA and App for VMWare CBC should work on Splunk 9.3 and Splunk Cloud (with the Python 3.9 update)

- Bug Fix

  - Detection for "Splunk Cloud" should be improved.

- Documentation

  - Backports python library may not work correctly on Windows. Follow this documentation to update a windows system with the correct backports library.

### backports

Run from Splunk. Linux is supported via packaged ".so" file. To fix for windows, run the following command from the "lib" folder.

This is 9.1 on Linux: `/opt/splunk/bin/splunk cmd python3.7 -m pip install --upgrade -t . backports._datetime_fromisoformat==2.0.1`

This is on Windows Splunk \>= 9.2.X:

`cd "C:\Program Files\Splunk\etc\apps\<APP>\lib"` `"C:\Program Files\Splunk\bin\splunk.exe" cmd python3 -m pip install --upgrade -t . backports._datetime_fromisoformat==2.0.1`

### v2.2.1

- Bug Fix

  - The `IA` (`Input AddOn`) had an improper python import, caused by the fix in v2.2.0, and results in an error on Introspection of modular inputs. This is fixed.

- Improvement

  - The Application Page supports up to 500 items for dropdowns and tables. The previous limit of 30 is updated.

### v2.2.0

- Improvements

  - Live Query Input uses the updated CBC SDK to allow for more than 10,000 events per run history found.

  - Upgraded `splunk-sdk` to 2.0.1

  - Inputs and API Configurations have `Test Config` buttons to help test permissions and configurations prior to implementation.

- Bug Fix

  - The `IA` (`Input AddOn`) does not provide a required python file, and results in an error. This is fixed.

  - The `Asset Details` dashboard contained a hard-coded IP Address. This is fixed.

### v2.1.0

- New Features

  - Asset Inventory Input

    - Includes USB Devices

  - Asset Details Dashboard

- Bug Fix

  - Index dropdowns will support more than 30 indexes.

  - The Input Addon was missing the App Configuration XML Dashboard.

### v2.0.0

- Improvements

  - CBC SDK is now version 1.5.0

  - Audit Logs Input now uses a Custom API key. Permissions Required: `org.audits (READ)`.

  - Upgraded various inputs and alert actions for use with the new CBC SDK.

- Bug Fix

  - Alerts Input: Enabled the `query` parameter to send the correct query to the API.

- UI/UX

  - Updated the `Active` columns to have on-demand input activation. Inputs will now be turned on/off instantly.

# Troubleshooting

Please refer to [FAQ & Troubleshooting](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk/faq-troubleshooting) for further documentation.

## Configuration Dashboard

To review current configurations (available via API calls, authorization roles apply), navigate manually to `https://<yourSplunkInstance>/<language>/app/vmware_app_for_splunk/vmware_cbc_current_configurations`.

## Support Offered

- Use the [Developer Community Forum](https://community.carbonblack.com/) to discuss issues and get answers from other API developers in the Carbon Black Community.

- Access questions and answers specific to the VMware Carbon Black Cloud app at [https://answers.splunk.com.](https://answers.splunk.com/) Be sure to tag your question with VMware Carbon Black Cloud Splunk App.

- Check out the [frequently asked questions and common troubleshooting](https://developer.carbonblack.com/reference/carbon-black-cloud/integrations/splunk/faq-troubleshooting).

- Report bugs and change requests to [Carbon Black Support](https://www.carbonblack.com/support/).

- View all API and integration offerings on the [Developer Network](https://developer.carbonblack.com/) along with reference documentation, video tutorials, and how-to guides.

## Diagnostics Generation

Please include a support diagnostic file when creating a support ticket. Use the following command to generate the file based on which Splunk app or add-on is installed. Send the resulting file to support.

- `$SPLUNK_HOME/bin/splunk diag --collect=app:vmware_app_for_splunk`

- `$SPLUNK_HOME/bin/splunk diag --collect=app:IA-vmware_app_for_splunk`

- `$SPLUNK_HOME/bin/splunk diag --collect=app:TA-vmware_app_for_splunk`

# Third Party Notices

Version of incorporates the following Third-party software or third-party services.

## NPM Packages

| name                                     | version        | license                 |
|------------------------------------------|----------------|-------------------------|
| name                                     | version        | license                 |
| @babel/runtime                           | 7.19.0         | MIT                     |
| @date-io/date-fns                        | 1.1.0          | MIT                     |
| @material-ui/core                        | 4.9.11         | MIT                     |
| @material-ui/icons                       | 4.9.1          | MIT                     |
| @material-ui/lab                         | 4.0.0-alpha.51 | MIT                     |
| @material-ui/pickers                     | 3.2.2          | MIT                     |
| @material-ui/react-transition-group      | 4.3.0          | BSD-3-Clause            |
| @material-ui/styles                      | 4.11.5         | MIT                     |
| @material-ui/system                      | 4.12.2         | MIT                     |
| @material-ui/utils                       | 4.11.3         | MIT                     |
| aplura-node                              | 1.1.12         | ISC                     |
| bail                                     | 1.0.5          | MIT                     |
| canvg                                    | 3.0.10         | MIT                     |
| ccount                                   | 1.1.0          | MIT                     |
| classnames                               | 2.3.1          | MIT                     |
| classnames                               | 2.2.6          | MIT                     |
| clsx                                     | 1.2.1          | MIT                     |
| comma-separated-tokens                   | 1.0.8          | MIT                     |
| core-js                                  | 3.25.1         | MIT                     |
| css-box-model                            | 1.2.1          | MIT                     |
| css-loader                               | 1.0.0          | MIT                     |
| css-vendor                               | 2.0.8          | MIT                     |
| date-fns                                 | 2.0.0-alpha.27 | MIT                     |
| debounce                                 | 1.2.0          | MIT                     |
| dom-helpers                              | 5.2.1          | MIT                     |
| dompurify                                | 2.4.0          | (MPL-2.0 OR Apache-2.0) |
| escape-string-regexp                     | 4.0.0          | MIT                     |
| eventemitter3                            | 3.1.2          | MIT                     |
| extend                                   | 3.0.2          | MIT                     |
| fast-deep-equal                          | 2.0.1          | MIT                     |
| filefy                                   | 0.1.10         | MIT                     |
| hoist-non-react-statics                  | 3.3.2          | BSD-3-Clause            |
| html2canvas                              | 1.4.1          | MIT                     |
| hyphenate-style-name                     | 1.0.4          | BSD-3-Clause            |
| inline-style-parser                      | 0.1.1          | MIT                     |
| is-buffer                                | 2.0.5          | MIT                     |
| is-in-browser                            | 1.1.3          | MIT                     |
| is-plain-obj                             | 2.1.0          | MIT                     |
| jspdf                                    | 2.1.0          | MIT                     |
| jspdf-autotable                          | 3.5.9          | MIT                     |
| jss                                      | 10.9.2         | MIT                     |
| jss-plugin-camel-case                    | 10.9.2         | MIT                     |
| jss-plugin-default-unit                  | 10.9.2         | MIT                     |
| jss-plugin-global                        | 10.9.2         | MIT                     |
| jss-plugin-nested                        | 10.9.2         | MIT                     |
| jss-plugin-props-sort                    | 10.9.2         | MIT                     |
| jss-plugin-rule-value-function           | 10.9.2         | MIT                     |
| jss-plugin-vendor-prefixer               | 10.9.2         | MIT                     |
| lodash                                   | 4.17.21        | MIT                     |
| markdown-table                           | 2.0.0          | MIT                     |
| material-table                           | 1.69.3         | MIT                     |
| mdast-util-definitions                   | 4.0.0          | MIT                     |
| mdast-util-find-and-replace              | 1.1.1          | MIT                     |
| mdast-util-from-markdown                 | 0.8.5          | MIT                     |
| mdast-util-gfm                           | 0.1.2          | MIT                     |
| mdast-util-gfm-autolink-literal          | 0.1.3          | MIT                     |
| mdast-util-gfm-strikethrough             | 0.2.3          | MIT                     |
| mdast-util-gfm-table                     | 0.1.6          | MIT                     |
| mdast-util-gfm-task-list-item            | 0.1.6          | MIT                     |
| mdast-util-to-hast                       | 10.2.0         | MIT                     |
| mdast-util-to-markdown                   | 0.6.5          | MIT                     |
| mdast-util-to-string                     | 2.0.0          | MIT                     |
| mdurl                                    | 1.0.1          | MIT                     |
| memoize-one                              | 5.2.1          | MIT                     |
| micromark                                | 2.11.4         | MIT                     |
| micromark-extension-gfm                  | 0.3.3          | MIT                     |
| micromark-extension-gfm-autolink-literal | 0.5.7          | MIT                     |
| micromark-extension-gfm-strikethrough    | 0.6.5          | MIT                     |
| micromark-extension-gfm-table            | 0.4.3          | MIT                     |
| micromark-extension-gfm-task-list-item   | 0.3.3          | MIT                     |
| object-assign                            | 4.1.1          | MIT                     |
| parse-entities                           | 2.0.0          | MIT                     |
| performance-now                          | 2.1.0          | MIT                     |
| popper.js                                | 1.16.1         | MIT                     |
| process                                  | 0.11.10        | MIT                     |
| prop-types                               | 15.8.1         | MIT                     |
| prop-types                               | 15.6.2         | MIT                     |
| prop-types                               | 15.7.2         | MIT                     |
| property-information                     | 5.6.0          | MIT                     |
| raf                                      | 3.4.1          | MIT                     |
| raf-schd                                 | 4.0.3          | MIT                     |
| react                                    | 0.1.0          | MIT                     |
| react                                    | 16.13.1        | MIT                     |
| react-beautiful-dnd                      | 13.0.0         | Apache-2.0              |
| react-dom                                | 16.13.1        | MIT                     |
| react-double-scrollbar                   | 0.0.15         | MIT                     |
| react-external-link                      | 1.2.1          | MIT                     |
| react-iframe                             | 1.8.0          | ISC                     |
| react-is                                 | 16.13.1        | MIT                     |
| react-is                                 | 17.0.2         | MIT                     |
| react-markdown                           | 6.0.2          | MIT                     |
| react-redux                              | 7.2.8          | MIT                     |
| react-stickynode                         | 3.0.5          | BSD-3-Clause            |
| react-tabs                               | 3.2.2          | MIT                     |
| react-tabs                               | 3.1.0          | MIT                     |
| react-transition-group                   | 4.4.5          | BSD-3-Clause            |
| react-uuid                               | 1.0.2          | MIT                     |
| redux                                    | 4.2.0          | MIT                     |
| remark-gfm                               | 1.0.0          | MIT                     |
| remark-parse                             | 9.0.0          | MIT                     |
| remark-rehype                            | 8.1.0          | MIT                     |
| repeat-string                            | 1.6.1          | MIT                     |
| rgbcolor                                 | 1.0.1          | MIT                     |
| rifm                                     | 0.7.0          | MIT                     |
| shallowequal                             | 1.1.0          | MIT                     |
| space-separated-tokens                   | 1.1.5          | MIT                     |
| stackblur-canvas                         | 2.5.0          | MIT                     |
| style-loader                             | 0.21.0         | MIT                     |
| style-to-object                          | 0.3.0          | MIT                     |
| subscribe-ui-event                       | 2.0.7          | BSD-3-Clause            |
| svg-pathdata                             | 6.0.3          | MIT                     |
| tiny-invariant                           | 1.2.0          | MIT                     |
| tiny-warning                             | 1.0.3          | MIT                     |
| trough                                   | 1.0.5          | MIT                     |
| unified                                  | 9.2.2          | MIT                     |
| unist-builder                            | 2.0.3          | MIT                     |
| unist-util-generated                     | 1.1.6          | MIT                     |
| unist-util-is                            | 4.1.0          | MIT                     |
| unist-util-position                      | 3.1.0          | MIT                     |
| unist-util-stringify-position            | 2.0.3          | MIT                     |
| unist-util-visit                         | 2.0.3          | MIT                     |
| unist-util-visit-parents                 | 3.1.1          | MIT                     |
| use-memo-one                             | 1.1.3          | MIT                     |
| vfile                                    | 4.2.1          | MIT                     |
| vfile-message                            | 2.0.4          | MIT                     |
| webpack                                  | 4.42.1         | MIT                     |
| xtend                                    | 4.0.2          | MIT                     |

OSS Licenses - NPM

## Python Packages

| Name                   | Version   | License                                             |
|------------------------|-----------|-----------------------------------------------------|
| PyYAML                 | 5.4.1     | MIT License                                         |
| Pygments               | 2.9.0     | BSD License                                         |
| cachetools             | 4.2.2     | MIT License                                         |
| carbon-black-cloud-sdk | 1.3.1     | MIT                                                 |
| certifi                | 2021.5.30 | Mozilla Public License 2.0 (MPL 2.0)                |
| chardet                | 4.0.0     | GNU Library or Lesser General Public License (LGPL) |
| charset-normalizer     | 2.0.3     | MIT License                                         |
| decorator              | 5.0.9     | BSD License                                         |
| idna                   | 3.2       | BSD License                                         |
| pika                   | 1.2.0     | BSD License                                         |
| prompt-toolkit         | 3.0.19    | BSD License                                         |
| protobuf               | 3.17.3    | 3-Clause BSD License                                |
| python-dateutil        | 2.8.2     | Apache Software License; BSD License                |
| requests               | 2.26.0    | Apache Software License                             |
| six                    | 1.16.0    | MIT License                                         |
| solrq                  | 1.1.1     | BSD License                                         |
| splunk-sdk             | 1.6.18    | Apache Software License                             |
| urllib3                | 1.26.6    | MIT License                                         |
| validators             | 0.18.2    | MIT License                                         |
| wcwidth                | 0.2.5     | MIT License                                         |

OSS Licenses - Python
