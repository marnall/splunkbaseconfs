# VMware Carbon Black EDR Documentation

Provides a view into VMware Carbon Black EDR platform.

|                            |                                 |
|----------------------------|---------------------------------|
| Version                    | 3.0.5                           |
| Build                      | 26                              |
| Splunk Enterprise Versions | 9.0, 8.2                        |
| Platforms                  | Splunk Enterprise, Splunk Cloud |
| Splunkbase Url             | 5624                            |
| Author                     | Aplura, LLC                     |

Allows a Carbon Black EDR administrator or analyst to interact with the CB EDR product.

## License

This software is licensed under the MIT license.

The MIT License (MIT)

Copyright (c) 2021 VMware, Inc. and Aplura, LLC.

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## Scripts and binaries

For more information on these scripts, and what they do, please refer to the `Initial Application Configuration` section of this document.

VMware Carbon Black EDR includes the following scripts:

|                                |                                                                                                |
|--------------------------------|------------------------------------------------------------------------------------------------|
| vmware-edr-ban-hash.py         | This is the Alert Action to ban a Hash in VMware Carbon Black EDR                              |
| vmware-edr-isolate-device.py   | This is the Alert Action to Isolate a sensor in VMware Carbon Black EDR                        |
| vmware-edr-kill-process.py     | This is the Alert Action to Kill a process on a sensor via VMware Carbon Black EDR             |
| vmware-edr-unisolate-device.py | This is the Alert Action to UnIsolate a sensor in VMware Carbon Black EDR                      |
| vmware_cmd_binarysearch.py     | This is the custom command to search for binaries in VMware Carbon Black EDR                   |
| vmware_cmd_processsearch.py    | This is the custom command to search for processes in VMware Carbon Black EDR                  |
| vmware_cmd_sensorsearch.py     | This is the custom command to search for sensors in VMware Carbon Black EDR                    |
| vmware_edr_client.py           | This is the core client configurations for interactions via Splunk and VMware Carbon Black EDR |
| AlertAction.py                 | This is the base alert action class.                                                           |
| ModularInput.py                | This is the base modular input class                                                           |
| Utilities.py                   | This is the base class for utility actions                                                     |
| cim_actions.py                 | This is a base class for CIM and Adaptive Response Actions                                     |
| edr_upgrader.py                | This is a base script for upgrade assistance.                                                  |
| variables.py                   | This is an included file for localized variables.                                              |
| app_properties.py              | This is an included file for localized properties.                                             |
| version.py                     | This also includes localized information.                                                      |
| Diag.py                        | This is the custom diag generation helper.                                                     |

## Migration from v2.2.0 to v3.0.0

Migration specifics for moving from `v2.2.0` of the `` DA-ESS-cbresponse`app to `v3.0.0 `` of the `vmware_cb_edr_app_for_splunk` are below. Please make sure to check Splunk version compatibility prior to migration.

### Migration while using HEC inputs

1.  Install v3.0.0 of the `vmware_cb_edr_app_for_splunk` from Splunkbase on the Search Tier of your environment.

2.  Install v3.0.0 of the `TA-vmware_cb_edr_app_for_splunk` from Splunkbase on the Indexing Tier of your environment.

3.  Update/Create the Splunk HEC input to use the new sourcetype `vmware:cb:edr:json`

### Migration while using AWS S3 inputs

1.  Install v3.0.0 of the `vmware_cb_edr_app_for_splunk` from Splunkbase on the Search Tier of your environment.

2.  Install v3.0.0 of the `TA-vmware_cb_edr_app_for_splunk` from Splunkbase on the Indexing Tier of your environment.

3.  Update/Create the AWS S3 input to use the new sourcetype `vmware:cb:edr:json`

### Migration while using `event_bridge_output.json`

1.  Install v3.0.0 of the `vmware_cb_edr_app_for_splunk` from Splunkbase on the Search Tier of your environment.

2.  Install v3.0.0 of the `TA-vmware_cb_edr_app_for_splunk` from Splunkbase on the Indexing Tier of your environment.

3.  Update the sourcetype setting of `inputs.conf` of the Universal Forwarder to `vmware:cb:edr:json`

### Update Event types

If the old data using the `bit9:carbonblack:json` sourcetype is to be integrated into the new apps, please update the following eventtypes for your environment:

- `vmware_cb_edr`

  - Update this to have the older sourcetype

  - `eventtype=vmware_cb_edr_base_index sourcetype IN (vmware:cb:edr:json, bit9:carbonblack:json)`

### Changes from v2.2.0 to v3.0.0

1.  Removed the datamodel `CbResponse`

2.  Commands

    1.  Renamed `binarysearch` to `edrbinarysearch`

    2.  Renamed `processsearch` to `edrprocesssearch`

    3.  Renamed `sensorsearch` to `edrsensorsearch`

3.  Alert Actions (stanza ids)

    1.  Renamed `banhash` to `vmware-edr-ban-hash`

    2.  Renamed `isolatesensor` to `vmware-edr-isolate-device`

    3.  Renamed `killprocess` to `vmware-edr-kill-process`

    4.  Added `vmware-edr-unisolate-device`

4.  Workflow Actions (stanza ids)

    1.  Renamed `sensor_info_by_ip` to `vmware_edr_sensor_info_by_ip`

    2.  Renamed `md5binarysearch` to `vmware_md5binarysearch`

    3.  Renamed `ipsearch` to `vmware_ipsearch`

    4.  Renamed `md5processsearch` to `vmware_md5processsearch`

    5.  Renamed `deeplinkprocess` to `vmware_edr_deeplink_process`

    6.  Renamed `deeplinksensor` to `vmware_edr_deeplink_sensor`

    7.  Renamed `VMware Carbon Black EDR Deep Link to $link_target$` to `vmware_edr_deeplink_target`

    8.  Renamed `VMware Carbon Black EDR Deep Link to $link_parent$` to `vmware_edr_deeplink_parent`

    9.  Renamed `VMware Carbon Black EDR Deep Link to $link_child$` to `vmware_edr_deeplink_child`

    10. Renamed `VMware Carbon Black EDR Process Search from NetConn` to `vmware_search_process_netconn`

    11. Renamed `VMware Carbon Black EDR Process Search on Filename` to `vmware_search_process_file_name`

    12. Renamed `VMware Carbon Black EDR Process Search on Domain` to `vmware_search_process_domain`

    13. Added `vmware_edr_deeplink_md5`

5.  Saved Searches

    1.  Disabled by default. Enable those that are needed.

6.  Dashboards

    1.  Removed `setup_page.xml` and `Setup.xml`

    2.  Added new configuration page `App_Config.xml`

    3.  Renamed and updated various dashboards for branding/efficiency.

# User Guide

## Initial Application Configuration

VMware Carbon Black EDR is configured from the `Application Configuration` menu option under the `Administration` menu.

- VMware Base Configuration

  - The options configured on this page will update settings in `local/eventtypes.conf`.

  - VMware CB EDR Base Index: specify where the events from EDR will be searched. Required on the searching tier.

  - VMware CB EDR Action Index: specify where events generated from alert actions will be stored and/or searched. Required on the searching tier. Should be a single index. `index=main`

- API Token Configuration

  - Use this tab to configure access to VMware Carbon Black EDR. The application supports multiple API Configurations to enable data from multiple Carbon Black EDR organizations to be ingested.

- Alert Actions

  - All available alert actions will be displayed on this page.

  - See the “Alert Actions” section below for configuration details and considerations

- Custom Commands

  - See the “Custom Commands” section below for configuration details and usage examples

**NOTE**: Do not modify any configurations in `/default`. Doing so will cause your changes to be overwritten when the app is upgraded. If required or directed to by support, create the appropriate configuration files in `/local` and include the stanza attributes that are being changed.

### Dashboards

VMware Carbon Black EDR includes the following dashboards.

- Application Health Overview (under the Administration menu option)

  - Use this page to get health and status information about any alerts, events, or API errors in the Carbon Black EDR. View total_failures, messages, and severity level for each instance.

- Binary status

- Endpoint status

- Network Overview

- Process Timeline

- System Check

- Binary Search

- Process Search

- Sensor Search

## Alert Actions

- Alert Configuration Notes: The global configurations referenced below are configured under “Administration/Application Configuration” under the “Alert Actions” tab.

- ALL search results that are being passed to the alert actions are required to have a "host" field that corresponds to the correct "Organization Name" as configured in the API Configuration Tab.

- If you use multi-tenancy, include the host field with the corresponding value in the Splunk search query. This value is the "Organization Name" found in the API Token Configuration.

- By default, when a new alert is created in Splunk the parameter `action.*.param.api_config = <api_config guid>` will be added to the `savedsearches.conf` file in the VMware Carbon Black EDR local directory. If you need to change credentials used on an alert action in the “Application Configuration” dashboard then all previously created alerts that were using the old credential needs to be changed. After updating credentials, delete the above parameter from the `savedsearches.conf` file for the appropriate saved search and restart Splunk.

VMware Carbon Black EDR includes the following alert actions:

- Kill Process

  - Remotely kill a process on the devices specified in the search

  - Search Configuration

    - Device ID Field: the field name that contains the device id to list processes.

    - Process Field: the field name that contains the process name to kill.

- Isolate Sensor

  - Isolating the specified device(s) prevents suspicious activity and malware from affecting the rest of your network. The device(s) will only be able to communicate with Carbon Black EDR until unisolated.

  - Search Configuration

    - Device ID Field: the field name that contains the device id to isolate.

- Un-isolate Sensor

  - Remove the specified device from the isolated state, allowing it to communicate normally on the network.

  - Search Configuration

    - Device ID Field: the field name that contains the device id to un-isolate.

- Ban Hash

  - Add the MD5 in the Splunk result set into VMware CB EDR banned hashes.

  - Search Configuration

    - Hash field name: The field name that contains the hash to ban.

## Custom Commands

VMware Carbon Black EDR includes the following custom commands (`default/commands.conf`).

- `edrbinarysearch`

  - Searches EDR for binaries.

  - Example: `|edrbinarysearch query="md5:fd3cee0bbc4e55838e65911ff19ef6f5"`

- `edrsensorsearch`

  - Searches EDR for sensors.

  - Example: `|edrsensorsearch query="ip:172.22.5.141"`

- `edrprocesssearch`

  - Searches EDR for processes.

  - Example: `edrprocesssearch query="process_name:cmd.exe"`

## Monitoring Console Health Checks

VMware Carbon Black EDR includes the following health checks in the Monitoring Console health check list(`default/checklist.conf`).

## Lookups

The contains the following lookup files.

- vmware_cb_actions.csv

  - This is the lookup to transform vendor actions into actions for CIM compliance.

## Event Generator

VMware Carbon Black EDR no longer will include an event generator.

## Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: No

3.  Report Acceleration: No

# Upgrader

VMWare CBC includes `edr_upgrader` modular input to assist in app upgrades. It is located in input `edr_upgrader://E2469382-11CF-48B9-B95C-956D0DAB9B48` :package: vmware_cb_edr_app_for_splunk :description: Provides a view into VMware Carbon Black EDR platform. :long_name: VMware Carbon Black EDR :version: 3.0.5 :app_author: Aplura, LLC :build: 26 :base_color: \#1d428a :splunk_versions: 9.0, 8.2 :splunkbase_url: 5624 :menu_slide_auto_close: false :include_app_setup: true :alert_actions: vmware-edr-ban-hash,vmware-edr-isolate-device,vmware-edr-kill-process,vmware-edr-unisolate-device :force_configuration: true :configuration_view: application_configuration == Installation

## Deployment Guide

**Note**: Installing the VMware EDR TA or IA on the same node as the App is an unsupported configuration that may result in instability or errors. If you are seeing the error message "More than 1 VMware EDR App detected", refer to the recommendations below for which Apps/Add-ons should be installed on which node and fully delete (not just disable) extra copies of VMware EDR apps/add-ons from nodes where they are not needed. Then restart Splunk on that node.

- Single Instance (8.0+)

  - Only the VMware Carbon Black EDR App

- Single Instance + Heavy Forwarder (8.0+)

  - Single Instance

    - VMware Carbon Black EDR App

  - Heavy Forwarder

    - VMware Carbon Black EDR App

- Distributed deployment (8.0+)

  - Heavy Forwarder

    - VMware Carbon Black EDR App

  - Search Head

    - VMware Carbon Black EDR App

  - Indexer:

    - TA-vmware_cb_edr_app_for_splunk

- Splunk Cloud

  - Use the Splunk Cloud self-service app install system to install this app.

  - If Self service is not available, contact Splunk Cloud Support handle this installation.

### Configuration

1.  Deploy the Apps and/or Add-ons per the Deployment Guide above.

2.  Create the index(s) for your data (if required)

    1.  One index for the Carbon Black EDR data

    2.  One index for the results of the Alert Actions

        1.  This can be the same index as the EDR data

3.  Navigate to the Administration -→ Application Configuration menu, `VMware EDR Base Configuration` tab

    1.  Update the index names to those created above

    2.  Click the "Save Application Configuration" button to enable the App.

4.  Configure a proxy if needed from the “Proxies” tab

5.  The Administration -→ “Application Health Overview” menu shows errors during processing and can be very useful during troubleshooting

6.  The Administration -→ “Application Usage” menu provides insights into which Splunk users are using the app

## Authorization

For built-in data inputs, alert actions, and commands, create API Keys with the correct permissions in the Carbon Black EDR and then configure Splunk to use those keys.

## Data Onboarding

To properly onboard the VMware CB EDR data, please follow the [documentation](https://developer.carbonblack.com/guide/enterprise-response/splunk/). Once the data is configured via HEC, AWS S3, or file with UF, refer to this documentation to continue configuration.

### Configuring Event Forwarder & S3 Inputs

#### Requirements and recommendations

The AWS add-on for Splunk is required for configuring S3 inputs. The add-on can be downloaded fromhttps://splunkbase.splunk.com/app/1876/\[Splunkbase\]. This add-on will be used to configure inputs for this Splunk app. Before configuring any inputs, you should create separate queues and S3 buckets for alert and endpoint events. A Carbon Black Event Forwarder must also be configured in order to forward data to the S3 buckets and to efficiently take in data, see the *Event Forwarder Configuration* section below.

#### Event Forwarder Configuration

An event forwarder must be created before any input can be received. This forwarder will be responsible for routing data to an S3 bucket where it can then be taken as input by Splunk. Configure your forwarder with filters to limit the amount of event data forwarded to Splunk in order to reduce costs. The forwarder installation guide for VMware CB EDR is located at [Developer Network](https://developer.carbonblack.com/guide/enterprise-response/event-forwarder-s3-bucket-configuration/). It is recommended to follow the guide there, and then proceed with the installation and configuration of Splunk.

More details can be found at the [CB Event Forwarder on Github](https://github.com/carbonblack/cb-event-forwarder).

#### Configure input in AWS Add-On

Before configuring the AWS inputs, make sure that the AWS add-on is properly installed in your Splunk environment. Get details for installing the AWS add-on from the [Splunk documentation](https://docs.splunk.com/Documentation/AddOns/released/AWS/Distributeddeployment) site. This documentation provides helpful information regarding the app and configuration settings.

The recommended approach to ingest Carbon Black EDR Event Forwarder data into Splunk is the [SQS-based S3 data input](https://docs.splunk.com/Documentation/AddOns/released/AWS/SQS-basedS3).

====== Configuring input in AWS add-on to pull S3 using SQS S3

- Set up the account on the Configuration page in the AWS Add-on

- Set up the input on the Inputs page in the AWS Add-on

  - Create new input

  - Custom Data Type

  - SQS-based S3

  - Name: specify a name that should be used for this input

  - AWS Account: select account created in step 1

  - Assume Role: Depends on environment permissions

  - AWS Region: Region of the selected queue

  - SQS Queue Name: select queue that you created in AWS

  - SQS Batch Size: leave 10

  - S3 File Decoder: leave at "Custom Logs"

  - Source Type

    - Set to `vmware:cb:edr:json`

  - Index: specify index where events should be written

    - This should be set to the same index as configured within base configurations

    - Advanced Settings: can set polling interval here

**NOTE**: If you need to reload older events and are using SQS to pull buckets, the events will not be available in the queue once they are retrieved. To view historical events or reload data, use the generic S3 option or copy the events to another prefix to copy it to the queue.

## Software requirements

### Splunk Enterprise system requirements

Because this App runs on Splunk Enterprise, all the [Splunk Enterprise system requirements ](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) apply.

### Download

Download VMware Carbon Black EDR at 5624.

## Release Notes

Version 3.0.5 of VMware Carbon Black EDR has the following known issues:

- None

### Version 3.0.5

- Updated \`\`splunklib\`\`

- Updated app.conf triggers

- Updated Configuration page

  - Fix an undefined error on event type update.

### Version 3.0.4

- Updated CBAPI library to support pagination

### Version 3.0.3

- Updated app.conf for simple reload triggers

### Version 3.0.2

- Updated SimpleXML to v1.1 and confirmed jQuery 3.5

### Version 3.0.1

- Alert Actions displayed both CBC and EDR actions. This has been fixed.

### Version 3.0.0

- Initial Release

- Features

  - Alert Actions

    - Ban Hash

    - Isolate Sensor

    - Unisolate Sensor

    - Kill Process

  - Custom Commands

    - Binary Search

    - Process Search

    - Sensor Search

  - Support for CIM

    - Alerts

    - Endpoint

    - Intrusion Detection

    - Network Traffic

# Troubleshooting, support, and resources

## Questions and answers

Access questions and answers specific to at <https://answers.splunk.com> . Be sure to tag your question with the name of the app: "Carbon Black EDR Splunk App".

## Support

- Support Offered: Splunk Answers, Community Engagement, VMware Carbon Black Support

- View all API and integration offerings on the [Developer Network](https://developer.carbonblack.com) along with reference documentation, video tutorials, and how-to guides.

- Use the [Developer Community Forum](https://community.carbonblack.com) to discuss issues and get answers from other API developers in the Carbon Black Community.

- Report bugs and change requests to [Carbon Black Support](https://www.carbonblack.com/support).

## Diagnostics Generation

If a support representative asks for it, a support diagnostic file can be generated. Use the following command to generate the file. Send the resulting file to support.

`$SPLUNK_HOME/bin/splunk diag --collect=app:vmware_cb_edr_app_for_splunk`

## Internal Splunk Logs

`index=_internal source=/opt/splunk/var/log/splunk/vmware_cb_edr_app_for_splunk/*`

## Indexed Error Logs

`index=main sourcetype=vmware:cb:edr:*:error`

# Third Party Notices

Version 3.0.5 of VMware Carbon Black EDR incorporates the following Third-party software or third-party services.

| name                                     | version        | license                 |
|------------------------------------------|----------------|-------------------------|
| name                                     | version        | license                 |
| @babel/runtime                           | 7.20.1         | MIT                     |
| @date-io/date-fns                        | 1.3.13         | MIT                     |
| @date-io/date-fns                        | 1.1.0          | MIT                     |
| @material-ui/core                        | 4.9.11         | MIT                     |
| @material-ui/icons                       | 4.9.1          | MIT                     |
| @material-ui/lab                         | 4.0.0-alpha.51 | MIT                     |
| @material-ui/pickers                     | 3.2.2          | MIT                     |
| @material-ui/pickers                     | 3.3.10         | MIT                     |
| @material-ui/react-transition-group      | 4.3.0          | BSD-3-Clause            |
| @material-ui/styles                      | 4.11.5         | MIT                     |
| @material-ui/system                      | 4.12.2         | MIT                     |
| @material-ui/utils                       | 4.11.3         | MIT                     |
| aplura-node                              | 1.1.12         | ISC                     |
| bail                                     | 1.0.5          | MIT                     |
| canvg                                    | 3.0.10         | MIT                     |
| ccount                                   | 1.1.0          | MIT                     |
| classnames                               | 2.2.6          | MIT                     |
| classnames                               | 2.3.2          | MIT                     |
| clsx                                     | 1.2.1          | MIT                     |
| comma-separated-tokens                   | 1.0.8          | MIT                     |
| core-js                                  | 3.26.0         | MIT                     |
| css-box-model                            | 1.2.1          | MIT                     |
| css-loader                               | 1.0.0          | MIT                     |
| css-vendor                               | 2.0.8          | MIT                     |
| date-fns                                 | 2.0.0-alpha.27 | MIT                     |
| date-fns                                 | 2.29.3         | MIT                     |
| debounce                                 | 1.2.0          | MIT                     |
| debounce                                 | 1.2.1          | MIT                     |
| dom-helpers                              | 5.2.1          | MIT                     |
| dompurify                                | 2.4.0          | (MPL-2.0 OR Apache-2.0) |
| escape-string-regexp                     | 4.0.0          | MIT                     |
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
| jspdf                                    | 1.5.3          | MIT                     |
| jspdf-autotable                          | 3.5.9          | MIT                     |
| jspdf-autotable                          | 3.5.3          | MIT                     |
| jss                                      | 10.9.2         | MIT                     |
| jss-plugin-camel-case                    | 10.9.2         | MIT                     |
| jss-plugin-default-unit                  | 10.9.2         | MIT                     |
| jss-plugin-global                        | 10.9.2         | MIT                     |
| jss-plugin-nested                        | 10.9.2         | MIT                     |
| jss-plugin-props-sort                    | 10.9.2         | MIT                     |
| jss-plugin-rule-value-function           | 10.9.2         | MIT                     |
| jss-plugin-vendor-prefixer               | 10.9.2         | MIT                     |
| markdown-table                           | 2.0.0          | MIT                     |
| material-table                           | 1.69.3         | MIT                     |
| material-table                           | 1.67.1         | MIT                     |
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
| react-beautiful-dnd                      | 13.1.1         | Apache-2.0              |
| react-dom                                | 16.13.1        | MIT                     |
| react-double-scrollbar                   | 0.0.15         | MIT                     |
| react-iframe                             | 1.8.0          | ISC                     |
| react-is                                 | 17.0.2         | MIT                     |
| react-is                                 | 16.13.1        | MIT                     |
| react-markdown                           | 6.0.2          | MIT                     |
| react-redux                              | 7.2.9          | MIT                     |
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
| space-separated-tokens                   | 1.1.5          | MIT                     |
| stackblur-canvas                         | 2.5.0          | MIT                     |
| style-loader                             | 0.21.0         | MIT                     |
| style-to-object                          | 0.3.0          | MIT                     |
| svg-pathdata                             | 6.0.3          | MIT                     |
| tiny-invariant                           | 1.3.1          | MIT                     |
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

| Name                          | Version   | License                                             |
|-------------------------------|-----------|-----------------------------------------------------|
| PyYAML                        | 6.0       | MIT License                                         |
| Pygments                      | 2.11.2    | BSD License                                         |
| attrdict                      | 2.0.1     | MIT License                                         |
| backports.functools-lru-cache | 1.6.1     | MIT License                                         |
| cachetools                    | 5.0.0     | MIT License                                         |
| cbapi                         | 1.7.6     | MIT                                                 |
| certifi                       | 2021.10.8 | Mozilla Public License 2.0 (MPL 2.0)                |
| chardet                       | 4.0.0     | GNU Library or Lesser General Public License (LGPL) |
| charset-normalizer            | 2.0.11    | MIT License                                         |
| decorator                     | 5.1.1     | BSD License                                         |
| idna                          | 3.3       | BSD License                                         |
| pika                          | 1.2.0     | BSD License                                         |
| prompt-toolkit                | 3.0.26    | BSD License                                         |
| protobuf                      | 3.19.4    | 3-Clause BSD License                                |
| python-dateutil               | 2.8.2     | Apache Software License; BSD License                |
| requests                      | 2.27.1    | Apache Software License                             |
| six                           | 1.16.0    | MIT License                                         |
| solrq                         | 1.1.1     | BSD License                                         |
| splunk-sdk                    | 1.6.16    | Apache Software License                             |
| urllib3                       | 1.26.8    | MIT License                                         |
| validators                    | 0.18.2    | MIT License                                         |
| wcwidth                       | 0.2.5     | MIT License                                         |

OSS Licenses - Python
