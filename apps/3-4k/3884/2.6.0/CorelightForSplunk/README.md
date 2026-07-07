# Corelight App For Splunk Documentation

The Corelight App for Splunk enables incident responders and threat hunters who use Splunk® and Splunk Enterprise Security to work faster and more effectively.

|                            |                                          |
|----------------------------|------------------------------------------|
| App Version                | 2.6.0                                    |
| App Build                  | 268                                      |
| Splunk Enterprise Versions | 10.X                                     |
| Platforms                  | Splunk Enterprise, Splunk Cloud          |
| Splunkbase Url             | <https://splunkbase.splunk.com/app/3884> |
| Author                     | Aplura, LLC. and Corelight, Inc.         |
| Creates an index           | False                                    |
| Implements summarization   | No                                       |
| Summary Indexing           | False                                    |
| Report Acceleration        | False                                    |
| Release Date               | 06/04/2026                               |

**IMPORTANT**

When upgrading from Corelight App For Splunk version 2.4.4 or earlier, remove the previous app before installing the latest Corelight App For Splunk app release. Additionally, check in the `local/data/ui/views` folder for conflicting dashboards.

**Corrupt CSV**

In versions of Corelight App For Splunk 2.5.3 and earlier, there is a semi-corrupt lookup. The lookup still works as intended, but will generate an increased volume in internal logging warnings. These additional logs do not increase license usage, as they are in the `_internal` index. The following search command can be executed within the Corelight App For Splunk to correct the CSV.

    | inputlookup corelight_base64conversion |outputlookup corelight_base64conversion

## Corelight App For Splunk - Dashboard Overview

The Corelight App For Splunk transforms complex network data into actionable security intelligence, enabling faster threat detection and incident response. By seamlessly integrating with Corelight Sensors and Zeek data, the app provides security teams with comprehensive visibility through specialized dashboards covering alert aggregation, protocol analysis, threat intelligence matching, and network behavior analytics. Built for security analysts, incident responders, and threat hunters, the app streamlines investigation workflows and enhances threat hunting capabilities with features like MITRE ATT&CK framework integration, automated alert correlation, and detailed traffic analysis.

### Security Workflows Dashboards

- **Alert Aggregations**: Consolidates and prioritizes security alerts with MITRE ATT&CK mapping for streamlined threat response

- **Intel**: Monitors IOC matches from external threat intelligence sources in network traffic

- **IP Interrogation**: Analyzes specific IP addresses for connection patterns, protocol usage, and network interactions

- **Log Hunting**: Enables detailed investigation of network events with customizable filters and search criteria

- **Notices**: Tracks system-generated security notices and intelligence alerts with severity classification

- **Security Posture**: Provides comprehensive overview of network security status including alerts, encryption, and DNS health

- **RDP Inferences**: Monitors Remote Desktop Protocol connections, authentication patterns, and security protocols

- **SSH Inferences**: Analyzes SSH connection patterns, authentication methods, and potential security issues

- **Suricata IDS Alert Overview**: Displays intrusion detection alerts with temporal patterns and severity levels

- **Threat Hunting**: Corelight-powered hunts for suspicious network activity

- **VPN Insights**: Tracks VPN usage patterns, connections, and user activity across the network

### Data Explorer Dashboards

- **Connections**: Visualizes top services, ports, dataflows, and network connection patterns

- **DNS**: Monitors DNS query patterns and potential exfiltration attempts through domain analysis

- **Files**: Identifies suspicious files, executables, and compressed file transfers

- **HTTP**: Analyzes HTTP transactions for suspicious patterns in headers, user agents, and requests

- **ICS/OT Monitoring**: Asset and security insights of ICS/OT protocols on your network.

- **Software**: Tracks software versions and usage patterns across monitored network traffic

- **SSL and x509**: Monitors SSL/TLS certificates and validation status for encrypted traffic

- **AWS VPC Flow**: Visualize and interrogate AWS VPC Flow network connections

### Data Insights Dashboards

- **Secure Channel Insights**: Analyzes encrypted and non-encrypted SSL, SSH, TLS, and x509 traffic

- **Name Resolution Insights**: Provides deep analysis of DNS traffic patterns and potential threats

- **Remote Activity Insights**: Monitors remote access patterns and authentication attempts

- **Anomaly Detection Insights**: Identifies anomalous activity from baselined network behavior

### Corelight Menu Dashboards

- **Configuration**: Manages app settings, indexes, and logging configuration

- **Operations Insights**: Network throughput and quality metrics of Corelight Sensors

- **Lookup Generation**: Creates and manages lookup files for dashboard filtering

- **Sensor Overview**: Provides operational status of Corelight sensors

- **Key Network Questions**: Shows essential network information to answer important questions

- **About**: Displays app version information and documentation

- External Corelight Resources

  - **Corelight Documentation**: The Corelight documentation provides user guides, quick starts, API references, tutorials, and more

  - **Corelight Logs Cheatsheet**: A reference PDF of the Corelight logs, the most commonly-used fields in those logs, and a description of those fields

  - **Corelight Threat Hunting Guide**: Introduces the process of Threat Hunting with network forensic logs, and provides practical examples of Threat Hunting with Zeek and Corelight data

  - **Corelight YouTube Channel**: The Corelight YouTube channel has videos explaining Corelight concepts, as well as past recordings of webinars hosted by Corelight

# User Guide

## Custom Search Commands

`cid` is a custom command provided to turn a tuple of `src_ip`, `src_port`, `dest_ip`, and `dest_port` into a community string.

## Lookups

Corelight App For Splunk contains several lookup files.

<div class="note">

It is a best practice and recommendation to **not** use the direct CSV name, as these will change between versions. Use the `transforms` name as listed in the table.

</div>

|                                  |                                             |                                                   |
|----------------------------------|---------------------------------------------|---------------------------------------------------|
| Transforms                       | Filename                                    | Description                                       |
| port_descriptions                | port_desc_2.6.0.csv                         | Gives port descriptions to ports.                 |
| corelight_systems                | corelight_systems_2.6.0.csv                 | Auto-generated from sensor data                   |
| corelight_services               | corelight_services_2.6.0.csv                | Auto-generated from services data                 |
| corelight_dns_ports              | corelight_dns_ports_2.6.0.csv               | Auto-generated from DNS data                      |
| corelight_dns_record_types       | corelight_dns_record_type_2.6.0.csv         | Auto-generated from NDS data                      |
| corelight_files_mime_types       | corelight_files_mime_types_2.6.0.csv        | Auto-generated from files data                    |
| corelight_software_types         | corelight_software_types_2.6.0.csv          | Auto-generated from software data                 |
| corelight_dns_reply_code         | corelight_dns_reply_code_2.6.0.csv          | Provided to lookup reply code types               |
| corelight_conn_state_description | corelight_conn_state_description_2.6.0.csv  | Describes connection states                       |
| corelight_status_action          | corelight_status_action_2.6.0.csv           | Describes Corelight action and status             |
| ssh_inference                    | ssh_inference_lookup_2.6.0.csv              | Describes SSH inferences                          |
| corelight_inferences_description | corelight_inferences_description_2.6.0.csv  | Describes SSH and RDP inferences                  |
| corelight_severity               | corelight_severities_2.6.0.csv              | Maps severity ids and severity text               |
| corelight_error_messages         | corelight_error_messages_2.6.0.csv          | Contains information on Corelight Error messages. |
| corelight_alert_aggregations     | corelight_alert_aggregations_enrichment.csv | Provides enrichments for Suricata alerts.         |
| corelight_rdp_inference_lookup   | corelight_rdp_inference_lookup_2.6.0.csv    | Describes RDP inferences                          |
| corelight_use_cases              | corelight_use_cases_2.6.0.csv               | Describes Corelight Anomaly Detection use cases   |
| corelight_direction              | corelight_direction_2.6.0.csv               | Lookup to enrich direction of data flow           |
| corelight_internal_networks      | KVStore                                     | Used to determine local networks via CIDR lookup  |
| corelight_internal_networks.csv  | corelight_internal_networks_csv.csv         | Used to determine local networks via CIDR lookup  |

## Scripts and binaries

This App provides the following scripts:

- cid.py

  - Script for use with the `cid` command.

- Diag.py

  - Custom diag generation

- Utilities.py

  - Splunk utilities for python scripts

- version.py

  - The splunk app version for logging purposes

- app_properties.py

  - The Splunk extension properties.

## Event Generator

Corelight App For Splunk does not make use of an event generator.

## Acceleration

1.  Summary Indexing: No

2.  Data Model Acceleration: No

3.  Report Acceleration: No

# Installation

## Software requirements

### Splunk Enterprise system requirements

Review the Splunk Enterprise system requirements at [Splunk Enterprise system Requirements](https://docs.splunk.com/Documentation/Splunk/latest/Installation/Systemrequirements) at <https://docs.splunk.com>.

### Download

The Corelight App For Splunk and the TA for Corelight add-on are available on Splunkbase.

- [Corelight App for Splunk](https://splunkbase.splunk.com/app/3884)

- [TA for Corelight add-on](https://splunkbase.splunk.com/app/3885)

**Important**: The **TA for Corelight** add-on is required on indexers, or index clusters. If your Corelight sensors send data directly to a heavy forwarder or a Splunk Cloud Platform receiver that is a heavy forwarder, the **TA for Corelight** is also required on those instances. The add-on is not required on search heads, or single-instance Splunk Enterprise environments.

# App Installation steps

Your Splunk Enterprise infrastructure will determine where the Corelight App for Splunk is installed.

## Splunk Cloud Platform customers

Contact your Splunk Administrator before installing Splunk apps in your Splunk Cloud Platform environment. The Corelight App for Splunk supports self-service installation. Cloud app installation guidance is available in [Install apps on your Splunk Cloud Platform deployment](https://docs.splunk.com/Documentation/SplunkCloud/latest/Admin/SelfServiceAppInstall#Install_a_public_app_from_Splunkbase) at <https://docs.splunk.com>

## Splunk Enterprise on-premises customers

When working with an on-premises Splunk Enterprise infrastructure, contact your Splunk Administrator to determine what locations and options are available for installing and distributing Splunk Apps. Installing Splunk apps typically requires administrative credentials.

### Splunk Enterprise single-instance

To deploy to single server instance of Splunk Enterprise:

1.  Log in to Splunk Web as an administrator.

2.  Browse to **Apps** \> **Find More Apps**.

3.  Use the search box to find **Corelight**.

4.  Click the **Install** button for the **Corelight App for Splunk**.

5.  (Optional) If a restart is required, click **Restart Splunk** to restart Splunk services.

### Other Splunk Enterprise architectures

Review the [Corelight App for Splunk documentation](https://docs.corelight.com) at <https://docs.corelight.com>

## Install the Add-on

The **TA for Corelight** add-on is required on indexers, or index clusters. If your Corelight sensors send data directly to a heavy forwarder or a Splunk Cloud Platform receiver that is a heavy forwarder, the **TA for Corelight** is also required on those instances. The add-on is not required on search heads, or single-instance Splunk Enterprise environments.

- Contact your Splunk Administrator. To determine which instances require the **TA for Corelight** add-on, you must understand the data flow from the sensor network to the Splunk Enterprise indexers, including any intermediate forwarding layers, and the tools used to deploy changes to those Splunk Enterprise instances.

## Configuration Steps

Configuring the Corelight App For Splunk requires the \`\`admin_all_objects\`\` capability, typical reserved for administrative users only. Once the configuration changes are saved, the admin user is no longer required.

1.  Log in to Splunk Web on the search head as an administrator.

2.  Browse to **Apps** \> **Corelight App for Splunk**.

3.  Select the **Corelight** drop-down, and click **Configuration**.

4.  Review the **Indexes** field, and add all indexes that contain Corelight sensor log data.

5.  Review the **Products** field, and verify that **Corelight** is selected.

    - If the **Corelight** option is selected, the dashboard searches will use log data source types beginning with the name \`\`corelight\_\`\`.

    - If the **Zeek** option is selected, the dashboard searches will use log data source types beginning with the name \`\`bro\_\`\`. If those source types do not exist in the indexes configured, the dashboard panels will display a warning about missing eventtypes. For example, \`\`Eventtype *bro_x509* does not exist or is disabled.\`\` If your sensor log sources don’t use source type names starting with \`\`bro\_\`\`, you can disable the **Zeek** option.

6.  Review the **Local Network Block(s)** field, and define your local networks in CIDR format. The networks defined in the app should match the **Local Network Blocks** defined on the Corelight sensor, or in the Fleet Manager sensor policy. For more information on sensor local networks, see [Configure network infrastructure](https://docs.corelight.com/docs/sensor/sensor/bro/setup.html#localizing) at <https://docs.corelight.com>.

    1.  **Note**: **Local Network Block(s)** are pre-populated with the default private address blocks, as mentioned in [Configure network infrastructure](https://docs.corelight.com/docs/sensor/sensor/zeek/setup.html#localizing) in the Sensor User Guide. To activate `direction`, `is_src_internal_ip`, and `is_dest_internal_ip` metadata generation based on your Local Network Block(s), click into the dropdown box and then out of the dropdown box whereby you should receive three (3) notifications: "Updated CSV Store Network Blocks", "Updated KV Store Network Blocks", and "Updated Network Blocks"

    2.  **Important**: If the connection establishment (e.g. conn history field) does not annotate a clean connection (e.g. syn/syn-ack/data/fin), the `direction` may not be accurate.

7.  (Optional) In the **Aggregation Saved Searches** field, enable the **Corelight Suricata Detections** search option. The search runs on a 10-minute interval by default, and generates data for the `corelight_suri_aggregations` sourcetype.

8.  Under **Application Control**, click the **Application Configured** switch.

## Enable the lookup generating searches

The Corelight App for Splunk includes lookup searches used to populate filters on the Corelight App dashboards.

1.  Log in to Splunk Web on the search head as an administrator.

2.  Browse to **Apps** \> **Corelight App for Splunk**.

3.  Select the **Corelight** drop-down, and click **Configuration**.

4.  In the **Lookup Generators** section, verify the lookup generating searches are enabled.

The lookup searches run on a 60-minute interval by default.

### Generate the lookup files manually

The lookup generating searches run on a schedule by default. You can generate the lookup files immediately by running the lookup searches manually.

## Next Steps

Use app dashboards such as the Data Explorer dashboards to verify the sensor data is available in Splunk Enterprise, and the Corelight App For Splunk is configured.

# Troubleshooting

## Actions

- Check the Monitoring Console for errors

- Validate if the Index(s), Product(s) and Local Network Block(s) are configured (Corelight \> Configuration).

- Ensure the lookup tables were fully updated by running the searches in the Lookup Generation dashboard (Corelight \> Lookup Generation)

## Support

- Support Email: None

- Support Website: <https://www.corelight.com/support>

- Support Offered: Web

App support is available through the [Corelight Support site](https://corelight.com/support/) at <https://corelight.com>.

You can find the latest documentation on the [Corelight documentation site](https://docs.corelight.com) at <https://docs.corelight.com>.

# Customer Agreement and Licensing

- For information related to access and use of Corelight Offerings, please refer to the following [document](https://8645105.fs1.hubspotusercontent-na1.net/hubfs/8645105/legal/220715MasterCustomerAgreementWebsiteDirect.pdf).

# Release Notes

## Version 2.6.0

### New Features

- **Network Directionality** – CIDR-based directionality for all Corelight sourcetypes using configured local network blocks

- Dashboards

  - Security Workflows

    - **Threat Hunting** – Corelight-powered hunts for suspicious connections

  - Corelight Menu

    - **Key Network Questions** – Shows essential network information to answer important questions

### Improvements

- Dashboards

  - Security Workflows

    - **VPN Insights** – Modernized to Dashboard Studio with VPN client/server panels and optimized parent/child searches.

    - **Corelight Suricata IDS Alert Overview** – Added a MITRE ATT&CK matrix with tactic/technique extraction and drilldown support.

    - **Log Hunting** – Consolidated and modernized in Dashboard Studio with global inputs, stacked charts, and CIM field names to facilitate Suricata and Notice investigations.

    - **IP Interrogation** – Upgraded to Dashboard Studio to leverage directionality feature, drive interrogation of suspicious IP Addresses, and address bugs

### Bug Fixes

- Dashboards

  - Data Insights

    - Security Posture – Fixed the SMBv1 panel on the Security Posture dashboard to filter SMBv1 traffic only, DNS panels with corrected data sources, sensor scoping, and SPL fixes.

- CIM Compliance

  - Fixed the CIM app field for conn logs by merging service and `app{}` fields with deduplication for Network Traffic compliance.

## Version 2.5.9

### New Features

- Dashboards

  - Data Explorer

    - Asset Classification – Automated network asset classification and visualization

### Improvements

- Dashboards

  - Corelight Menu

    - External Corelight Resources – Links to "Corelight Youtube Channel" and "Corelight Threat Hunting Guide"

- CIM Compliance

  - Improved mapping of `corelight_known_*` sourcetypes

  - Improved mapping of `corelight_suricata_corelight` to Intrusion Detection Data Model

  - Improved `corelight_smtp` sourcetype to extract src_user, src_user_domain

  - Improved `corelight_files`, `corelight_files_red`, and `corelight_files_agg` sourcetypes to mvappend md5, sha1, sha256 to file_hash field

  - Improved mapping of `corelight_smb_files` sourcetype to Data Access Data Model

  - Improved mapping of `corelight_notice` sourcetype to Alert Data Model

  - Improved mapping of `corelight_http`, `corelight_http_red`, and `corelight_http_agg` sourcetype to Web Application Data Model

- Lookups

  - `corelight_status_action`

    - Mapped `action` field values to match standardized [HTTP Response Status Codes](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Status) for Web Data Model

### Bug Fixes

- Dashboards

  - Security Workflows

    - Alert Aggregations – fixed formatting of `agg_id` field to address scientific-notation value issue to enable dashboard drilldown

  - Data Explorer

    - Connections - fixed `corelight_conn_agg` sourcetype and applied `tkn_conn_uid` token throughout Parent Data Sources

## Version 2.5.8

- New Features

  - Dashboards

    - Data Insights

      - Anomaly Detection Details - Added Drilldown Dashboards for Admin_Shares and RDP Use Cases

    - Data Explorer

      - ICS/OT Monitoring - Asset and security insights of ICS/OT protocols

      - Data Aggregation support for Dashboard Studio versions of Connections, DNS, Files, HTTP, and SSL and x509 dashboards

  - Corelight Menu

    - Operations Insights - Added 3 Visualizations to help Users understand Storage Needed when enabling SmartPCAP

    - External Corelight Resources

      - Links to "Corelight Docs" and "Zeek Cheat Sheet"

- Improvements

  - Dark theme supported

  - Dashboards

    - Anomaly Detection Details Dashboards - Optimized experience for existing 5 Use Cases

    - Corelight Suricata IDS Alert Overview

      - Replaced "Category Analysis" Table with a Sankey

      - Added description for "Signature Analysis" to click on SID

      - In "Log Details" Panel, if `has_payload` field returns `yes`, Users may click on the `session_id` to view the Decoded Payload

    - Alert Aggregations

      - Alerts Table now filters based on Impact and Category Input Filter selections.

    - Secure Channel Insights

      - Added missing traffic direction and IP classification fields to DNS and SSL sourcetypes.

      - Removed 8 Unused Visualizations and related 5 broken Datasources

    - Software

      - Converted dashboard from Classic XML to Dashboard Studio

## Version 2.5.7

- New Features

- Dashboards

  - Data Insights

    - Anomaly Detection Insights: Identifies anomalous activity from baselined network behavior

  - Data Explorer

    - AWS VPC Flow: Visualize and interrogate AWS VPC Flow network connections

  - Corelight Menu

    - Lookup Generation

      - Corelight Lookup File Generation Status - displays whether data is present in Corelight Lookup Generation files

      - Corelight Lookup Files - displays a field listing, file size, etc of all Corelight Lookup Files

- Improvements

- Corelight Suricata Lookup Gen

  - Added the `corelight_idx` macro to each search and sub-search to restrict to only those indexes. This should increase performance and reduce CPU load.

- Fixed Props configurations for `EVAL` and `FIELDALIAS` that were throwing `CalcFieldProcessor` errors in the internal logs.

- Dashboards

  - All: Standardized inputs for Corelight Sensor and Global Time Restriction

  - Secure Channel Insights: Datasources defining `weak_key` are updated to specify between RSA and ECDSA certificates

  - Security Workflows

    - All

      - Applied standardized colors to charts

      - Changed theme to dark

    - Alert Aggregations Details

      - Fixed *Payload* Panel size to auto

    - Security Posture

      - Datasources defining `weak_key` are updated to specify between RSA and ECDSA certificates

- Bug Fixes

- Corelight Sensor Lookup Gen

  - Updated the sensor lookup generator to have the latest time and sourcetypes the sensor was found.

- Dashboards

  - Security Workflows

    - Alert Aggregations

      - Fixed time passing when drilling from an agg_id value into the Alert Aggregations Details dashboard

    - Security Posture

      - Fixed *SMB v1 Connections* Panel size to auto

## Version 2.5.6

- Improvements

  - Updated props to ensure that all sourcetypes evaluate the sensor name correctly.

## Version 2.5.5

- POTENTIAL BREAKING Change

  - Due to enforcement of Splunk AppInspect check `check_props_conf_has_no_prohibited_characters_in_sourcetypes`, the "wildcard" property in `props.conf` has been REMOVED.

  - The settings are included below for reference if needed.

  - **NOTE**: This will not be available in Splunk Cloud.

        [(?::){0}corelight*]
        TRUNCATE                 = 9999999
        SHOULD_LINEMERGE         = FALSE
        TIME_PREFIX              = _write_ts(?:"\s*:\s*")?
        TIME_FORMAT              = %Y-%m-%dT%H:%M:%S.%6QZ
        MAX_TIMESTAMP_LOOKAHEAD  = 40
        KV_MODE                  = JSON
        FIELDALIAS-dest          = id.resp_h ASNEW dest id.resp_h ASNEW id_resp_h
        FIELDALIAS-dest_ip       = id.resp_h ASNEW dest_ip
        FIELDALIAS-dest_port     = id.resp_p ASNEW dest_port id.resp_p ASNEW id_resp_p
        FIELDALIAS-src           = id.orig_h ASNEW src id.orig_h ASNEW id_orig_h
        FIELDALIAS-src_ip        = id.orig_h ASNEW src_ip
        FIELDALIAS-src_port      = id.orig_p ASNEW src_port id.orig_p ASNEW id_orig_p
        EVAL-direction           = case(isnotnull(direction),direction,local_orig="true" AND local_resp="true", "internal", local_orig="true" and local_resp="false", "outbound", local_orig="false" and local_resp="false", "external", local_orig="false" and local_resp="true", "inbound", 1=1, "unknown")
        EVAL-is_broadcast        = if(src in("0.0.0.0", "255.255.255.255") OR dest in("255.255.255.255", "0.0.0.0"),"true","false")
        EVAL-is_src_internal_ip  = if(cidrmatch("10.0.0.0/8",src) OR cidrmatch("172.16.0.0/12",src) OR cidrmatch("192.168.0.0/16", src), "true", "false")
        EVAL-is_dest_internal_ip = if(cidrmatch("10.0.0.0/8",dest) OR cidrmatch("172.16.0.0/12",dest) OR cidrmatch("192.168.0.0/16", dest), "true", "false")
        EVAL-vendor_product      = "Corelight"
        EVAL-vendor              = "Corelight"
        EVAL-sensor_name         = coalesce(system_name, host, "unknown")

## Version 2.5.4

- Administrative Change

  - The app is no longer exported `system` by default. Please see latest Splunk documentation to enable system-wide export of knowledge objects. This change is to allow Splunk Administrators the ability to review all configurations prior to making the configurations globally available.

- Bugs

  - Fixed bugs in sourcetype `corelight_investigator_alerts`

    - FIELDALIAS of `_time` caused subsearch failure in ITSI specific searches

    - EVAL of `src_ip` and `dest_ip` have incorrect mvfilters

## Version 2.5.3

- Documentation

  - Updated documentation

- Sourcetypes

  - Added new sourcetype `corelight_investigator_alerts`

- Dashboards

  - Added new "Operational Insights" dashboard to explore sensor health

## Version 2.5.2

- **Configuration Dashboard**

  - Index Dropdown updated to allow more than 30 indexes

  - Added toggles to enable/disable Saved Searches

- **Python Library**

  - Updated Python library `splunk-sdk` to 2.1.0

## Version 2.5.1

### What’s New

- **Alert Aggregations**

  - Introducing a new suite of dashboards designed to aggregate Suricata alerts. These dashboards feature AI-driven enrichments and mappings to the MITRE ATT&CK framework, offering a comprehensive analytical perspective.

  - New Dashboards:

    - Alert Aggregations

    - Alert Aggregations Details

- **Corelight_ssh Integration**

  - Added `corelight_ssh` to the CIM framework with accurate tagging and mapping to their respective Splunk Data Models.

### Improvements to Functionality

- **Lookup Updates**

  - Removed versioning from generated lookups to prevent upgrade issues between generations.

- **Optimized Performance:**

  - Enhanced search performance on Security Posture panels, including SMBv1, FTP, and DNS.

### Issue Resolutions

- **Field Alias Adjustments:**

  - Updated `corelight_http`, `corelight_http_red`, and `corelight_http2` stanzas in `props.conf` to correctly handle field aliases for `bytes_in` and `bytes_out`.

- Lookup Updates

  - Removed versioning from generated lookups to prevent upgrade issues between generations.

- Dashboard Updates

  - Updated various dashboards for formatting and search optimizations.

- Upgraded `splunk-sdk` to 2.0.2.

## Version 2.5.0

- Dashboard Updates

  - Updated the `Welcome` dashboard

  - Added `Security Posture`

  - Added `Secure Channel Insights`

  - Added `Name Resolution Insights`

  - Added `Remote Activity Insights`

## Version 2.4.10

- Bug

  - \[DESK-1536\] - Various sourcetypes did not have the proper time extraction for the Corelight Appliance.

## Version 2.4.9

- Dashboard Enhancements

  - HTTP

    - Added dropdown filter for User Agents. Shows Top 100 only.

  - VPN Insights

    - Added dropdown filter for Inferences.

    - Fixed incorrect query for `Largest Transfers Between Host Pairs Over VPN`

  - Intel

    - Added dropdown filter for Incident Types.

  - Notices

    - Added a textual filter field for `msg` or `note` fields.

- Updated `Corelight Suricata IDS Alerts` dashboard.

- Extractions

  - Updated various sourcetypes to remove confusion around src/dest fields relating to `id.*` fields.

## Version 2.4.8

- Updated TA for proper permissions to pass Splunk Cloud

- Updated `corelight_ntp` sourcetype: correct an if statement

## Version 2.4.7

- Removed `KV_MODE` on `corelight_tsv` as invalid against `INDEXED_EXTRACTIONS`

- Updated lookups to a version based file-naming convention to facilitate Splunk Cloud updates.

- Additional CIM additions for additional sourcetypes

## Version 2.4.6

- Updated to CIM v5.1

- Fixed bug in `cid` search command relating to icmp6 with IPv6 src_ips.

- Updated `inferences` props for better extractions.

## Version 2.4.5

- Converted `cid` custom command to a v2 Search Command.

- Updated `splunklib` to current version.

- Updated Configuration Management page

- Added additional support easier diagnostic gathering

# Review and Optimization (removed on Release)

# Name Resolution Insights

## Reviewed: No Change

- **\*Responding DNS Servers**\*

  - Single Value

  - Table

- ****\*Unusual Qtypes****\*

  - Single Value

  - Table

- ****\*NXDOMAIN Responses****\*

  - Single Value

  - Table

- ****\*Failed DNS Queries****\*

  - Single Value

## Reviewed: Change

- ****\*Failed DNS Queries****\*

  - Table: "ds_dns_tbl_name_res_failed_table"

- **\*DNS Query Volume Over Time**\*

  - Single Value: "ds_dns_sv_volume_count"

- **\*Monitoring DNS Query Response Times \> 15ms**\*

  - Single Value: "ds_dns_sv_name_res_query_response_base"

  - Table: "ds_dns_tbl_name_res_query_response_base"

## Reviewed: Questions

- **\*DNS Query Volume Over Time**\*

  - Chart

  - What is this supposed to show? Right now it is "count of dns events over time", but the blurb indicates "avg rtt by qtype_name" should be displayed.

  - What is 35s as the average? of what?

# Third-party software

## Aplura, LLC Components

Components Written by Aplura, LLC Copyright © 2016-2023 Aplura, LLC

This program is free software; you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation; either version 2 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program; if not, write to the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, eMA 02110-1301, USA.
