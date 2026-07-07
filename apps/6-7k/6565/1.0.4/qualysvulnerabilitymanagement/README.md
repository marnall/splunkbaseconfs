# Qualys Vulnerability Management

Publisher: Splunk <br>
Connector Version: 1.0.4 <br>
Product Vendor: Qualys <br>
Product Name: Qualys Vulnerability Management <br>
Minimum Product Version: 6.1.1

This app integrates with Qualys to perform generic and investigative actions

## Explanation of the Asset Configuration Parameters

The asset configuration parameters affect 'test connectivity' and some other actions of the
application. The parameters related to 'test connectivity' action are listed below

- **base url:** Qualys API URL. You can find the API URL for a specific platform
  [here](https://www.qualys.com/platform-identification/)
- **username:** The user name (login) of a Qualys user account.
- **password:** The password of a Qualys user account.
- **timeout:** The total time available for a request to be processed and answered. The default
  time is 30 seconds.

## Explanation of the Qualys Action's Parameters

- ### Test Connectivity (Action Workflow Details)

  - This action will test the connectivity of the Splunk SOAR server to the Qualys instance by
    making an initial API call using the provided asset configuration parameters.
  - The action validates the provided asset configuration parameters. Based on the API call
    response, the appropriate success and failure message will be displayed when the action gets
    executed.

- ### Scan Summary

  This action will identify hosts that were not scanned and why.\
  Permissions - 'Manager' role is required.\
  Categories for hosts not scanned:

  - **Excluded** - The hosts were excluded. Hosts may be excluded on a per scan basis (by the
    user launching or scheduling the scan) or globally for all scans. Managers and Unit Managers
    have privileges to edit the global excluded hosts list for the subscription.
  - **Dead** - The hosts were not “alive” at the time of the scan
  - **Cancelled** - Hosts were not scanned because the scan was cancelled. Scans may be
    cancelled by a user, by an administrator or automatically by the service as specified in
    scheduled scan settings.
  - **Unresolved** - Hosts were scanned but they could not be reported
  - **Aborted** - The scan was abruptly discontinued. This is a rare occurrence that may be
    caused for different reasons. For example, it's possible that a connection timed out or
    there were connection errors on a particular port or the scan time elapsed.
  - **Blocked** - Hosts were blocked from scanning for some reason. For example, user-provided
    blacklisted IPs to scan and after the scan was launched it was blocked due to improper
    configuration.

- ### Launch Scan

  This action will launch a vulnerability scan in the user's account.\
  This action will give an error message for all the current VMs scanning if you have exceeded the
  limit of concurrent scan VM as per your account.

  - **Action Parameter : iscanner_name**

    - The friendly names of the scanner appliances to be used or “External” for external
      scanners. Multiple entries are comma separated.

    - Steps to get iscanner_name from Qualys platform

      - Login to the Qualys platform
      - Navigate to the **Scans**
      - In Scans Click on the **Appliances**
      - Copy the appliance name and paste it into the iscanner_name field of the launch scan
        action

  - **Action Parameter : option_title**

    - Steps to get option_title from Qualys platform

      - Login to the Qualys platform
      - Navigate to the **Scans**
      - In Scans Click on the **Option Profiles**
      - Copy the option title and paste it into the option_title field of the launch scan
        action

  - **Action Parameter: priority**

    - Specify a value of 0 - 9 to set a processing priority level for the scan.

      - 0 = No Priority (the default)
      - 1 = Emergency
      - 2 = Ultimate
      - 3 = Critical
      - 4 = Major
      - 5 = High
      - 6 = Standard
      - 7 = Medium
      - 8 = Minor
      - 9 = Low

### Configuration variables

This table lists the configuration variables required to operate Qualys Vulnerability Management. These variables are specified when configuring a Qualys Vulnerability Management asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Base url |
**timeout** | required | numeric | Timeout |
**username** | required | string | Username |
**password** | required | password | Password |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[list asset groups](#action-list-asset-groups) - List asset groups in the user account <br>
[list host findings](#action-list-host-findings) - List hosts and their vulnerability details <br>
[launch scan](#action-launch-scan) - Launch vulnerability scan for vm <br>
[scan summary](#action-scan-summary) - Identify hosts that were not scanned and why

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list asset groups'

List asset groups in the user account

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ids** | optional | Show only asset groups with certain IDs (Comma separated value) | string | `asset group id` |
**truncation_limit** | optional | Specify the maximum number of asset group records to output (Max 1000000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ids | string | `asset group id` | 504351 |
action_result.parameter.truncation_limit | numeric | | 1000 |
action_result.data.\*.ID | string | | 934333 |
action_result.data.\*.NETWORK_ID | string | | Default |
action_result.data.\*.IP_SET.IP.\* | string | | 8.8.8.8 |
action_result.data.\*.IP_SET.IP_RANGE.\* | string | | 1.1.1.1-1.1.1.3 |
action_result.data.\*.APPLIANCE_IDS | string | | 4950577,4950578 |
action_result.data.\*.DEFAULT_APPLIANCE_ID | string | | 4950577 |
action_result.summary.found_asset_groups | numeric | | 4 |
action_result.message | string | | Found asset groups: 4 |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list host findings'

List hosts and their vulnerability details

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ips** | optional | IPv4 IP addresses (Comma separated value or IP address range) | string | `ip range` `ip` |
**vm_scan_date_before** | optional | Shows hosts with a vulnerability scan before a given date and time. Specify the date in YYYY-MM-DDTHH:MM:SSZ format | string | `date` |
**vm_scan_date_after** | optional | Shows hosts with a vulnerability scan after a given date and time. Specify the date in YYYY-MM-DDTHH:MM:SSZ format | string | `date` |
**truncation_limit** | optional | Specify the maximum number of host records to output (Max 1000000) | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ips | string | `ip range` `ip` | 8.8.8.8 |
action_result.parameter.truncation_limit | numeric | | 1000 |
action_result.parameter.vm_scan_date_after | string | `date` | 2022-07-19T09:59:59Z |
action_result.parameter.vm_scan_date_before | string | `date` | 2022-07-19T10:59:59Z |
action_result.data.\*.ASSET_ID | string | | 2805388 |
action_result.data.\*.DNS | string | | fra16s14-in-f14.1e100.net |
action_result.data.\*.DNS_DATA.DOMAIN | string | | 1e100.net |
action_result.data.\*.DNS_DATA.FQDN | string | | fra16s14-in-f14.1e100.net |
action_result.data.\*.DNS_DATA.HOSTNAME | string | | fra16s14-in-f14 |
action_result.data.\*.ID | string | | 1941672 |
action_result.data.\*.IP | string | | 172.217.22.14 |
action_result.data.\*.NETBIOS | string | | WIN-QQ1C9VPRU4R |
action_result.data.\*.NETWORK_ID | string | | Default |
action_result.data.\*.OS | string | | EulerOS / Ubuntu / Fedora / Tiny Core Linux / Linux 3.x / IBM / FortiSOAR |
action_result.data.\*.TRACKING_METHOD | string | | IP |
action_result.data.\*.VULN.\*.CATEGORY | string | | TCP/IP |
action_result.data.\*.VULN.\*.QID | string | | 70000 |
action_result.data.\*.VULN.\*.SEVERITY_LEVEL | string | | 1 |
action_result.data.\*.VULN.\*.TITLE | string | | Open TCP Services List |
action_result.data.\*.VULN.\*.VULN_TYPE | string | | Information Gathered |
action_result.summary.found_hosts | numeric | | 3 |
action_result.message | string | | Found hosts: 3 |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'launch scan'

Launch vulnerability scan for vm

Type: **generic** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**scan_title** | optional | The scan title (Maximum 2000 characters) | string | |
**ip** | optional | The IP addresses to be scanned (Comma separated value and IP address ranges) | string | `ip range` `ip` |
**asset_group_ids** | optional | The IDs of asset groups containing the hosts to be scanned (Comma separated value) | string | `asset group id` |
**exclude_ip_per_scan** | optional | The IP addresses to be excluded from the scan (Comma separated value and IP address ranges) | string | `ip range` `ip` |
**iscanner_name** | optional | The name of the scanner appliances to be used (Comma separated value) | string | |
**option_title** | required | The title of the option profile to be used | string | |
**priority** | optional | Specify a value of 0 - 9 to set a processing priority level for the scan | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.asset_group_ids | string | `asset group id` | 504351 |
action_result.parameter.exclude_ip_per_scan | string | `ip range` `ip` | 8.8.8.8 |
action_result.parameter.ip | string | `ip range` `ip` | 8.8.8.8 |
action_result.parameter.iscanner_name | string | | External |
action_result.parameter.option_title | string | | Initial Options |
action_result.parameter.priority | numeric | | 3 |
action_result.parameter.scan_title | string | | Test Title |
action_result.data.0.ITEM.0.VALUE | string | `scan id` | 994463 |
action_result.data.0.ITEM.1.VALUE | string | `reference` | scan/1658741010.01010 |
action_result.summary | string | | |
action_result.message | string | | VM scan launched successfully |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'scan summary'

Identify hosts that were not scanned and why

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**scan_date_since** | required | Include scans started since a certain date. Specify the date in YYYY-MM-DD format | string | `date` |
**scan_date_to** | optional | Include scans started up to a certain date. Specify the date in YYYY-MM-DD format | string | `date` |
**include_dead** | optional | If marked, dead host will be included in the output | boolean | |
**include_excluded** | optional | If marked, excluded host will be included in the output | boolean | |
**include_unresolved** | optional | If marked, unresolved host will be included in the output | boolean | |
**include_cancelled** | optional | If marked, cancelled host will be included in the output | boolean | |
**include_blocked** | optional | If marked, blocked host will be included in the output | boolean | |
**include_aborted** | optional | If marked, aborted host will be included in the output | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.include_aborted | boolean | | True |
action_result.parameter.include_blocked | boolean | | True |
action_result.parameter.include_cancelled | boolean | | True |
action_result.parameter.include_dead | boolean | | True |
action_result.parameter.include_excluded | boolean | | True |
action_result.parameter.include_unresolved | boolean | | True |
action_result.parameter.scan_date_since | string | `date` | 2022-07-19 |
action_result.parameter.scan_date_to | string | `date` | 2022-07-20 |
action_result.data.\*.HOST_SUMMARY.\*.CATEGORY | string | | dead |
action_result.data.\*.HOST_SUMMARY.\*.IP | string | | 8.8.8.8 |
action_result.data.\*.HOST_SUMMARY.\*.TRACKING_METHOD | string | | IP |
action_result.data.\*.SCAN_DATE | string | | 2022-07-14T07:34:17Z |
action_result.data.\*.SCAN_REF | string | | scan/1657784057.92367 |
action_result.summary.found_scans | numeric | | 21 |
action_result.message | string | | Found scans: 21 |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

______________________________________________________________________

Auto-generated Splunk SOAR Connector documentation.

Copyright 2025 Splunk Inc.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
