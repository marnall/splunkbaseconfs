# FireAMP

Publisher: Splunk <br>
Connector Version: 2.1.14 <br>
Product Vendor: Cisco Systems <br>
Product Name: FireAMP <br>
Minimum Product Version: 6.2.1

This App allows for querying endpoints connected to Cisco FireAMP while also providing investigative hunting capabilities

#### To Generate API Credentials

- Go to Accounts >> API Credentials
- Click New API Credential to generate an API key for your application. You can enter the name of
  the application for reference purposes and assign a scope of read only or read and write
  permissions as per your requirements.
- Store this generated API key somewhere secure since it cannot be retrieved after closing the
  window.

#### Base URL

- There are 3 different Base URLs available:

  - api.amp.cisco.com
  - api.apjc.amp.cisco.com
  - api.eu.amp.cisco.com

- To find the Base URL, Go to Accounts >> API Credentials

- Click on **View API Documentation** . It will redirect to the Endpoints API page. Check the
  value of the **api_host** parameter in the URL.

- If Base URL is not provided, **https://api.amp.sourcefire.com/** will be used as the Base URL by
  default.

### Configuration variables

This table lists the configuration variables required to operate FireAMP. These variables are specified when configuring a FireAMP asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | optional | string | Base URL |
**api_client_id** | required | string | API Client ID |
**api_key** | required | password | API Key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration by attempting to connect and getting the version of the API endpoint <br>
[list endpoints](#action-list-endpoints) - List all of the endpoints connected to FireAMP <br>
[hunt file](#action-hunt-file) - Search for a file matching a SHA256 hash across all endpoints <br>
[hunt ip](#action-hunt-ip) - Search for a given IP <br>
[hunt url](#action-hunt-url) - Search for a given URL <br>
[list groups](#action-list-groups) - List all of the groups are present in FireAMP <br>
[list policies](#action-list-policies) - List all of the policies present in FireAMP <br>
[change policy](#action-change-policy) - Updates group to given windows policy <br>
[change group](#action-change-group) - Change the group of provided GUID endpoint <br>
[unquarantine device](#action-unquarantine-device) - Stop host isolation based on connector GUID <br>
[quarantine device](#action-quarantine-device) - Isolate host based on connector GUID <br>
[find device](#action-find-device) - Finds system with search parameters <br>
[get device info](#action-get-device-info) - Get information about a device, given its connector GUID <br>
[block hash](#action-block-hash) - Add a file hash (sha256 only) to a file list specified by GUID <br>
[unblock hash](#action-unblock-hash) - Remove a file hash (sha256 only) from a file list specified by GUID <br>
[allow hash](#action-allow-hash) - Add a file hash (sha256 only) to a file list specified by GUID <br>
[disallow hash](#action-disallow-hash) - Remove all sha256 file hashes from a file list specified by GUID <br>
[list filelists](#action-list-filelists) - List all of the File Lists (application blocking & simple custom detections) in FireAMP <br>
[get filelist](#action-get-filelist) - Get all of the hashes in a File List in FireAMP. Lists can be retrieved by UUID, or file list name and type <br>
[remove listitem](#action-remove-listitem) - Removes file hash from file list <br>
[add listitem](#action-add-listitem) - Add file hash as listitem to file list <br>
[find listitem](#action-find-listitem) - Finds file hash in specified file list <br>
[get device trajectory](#action-get-device-trajectory) - Retrieve trajectory info about a device <br>
[get device events](#action-get-device-events) - Retrieve device events

## action: 'test connectivity'

Validate the asset configuration by attempting to connect and getting the version of the API endpoint

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'list endpoints'

List all of the endpoints connected to FireAMP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.data.\*.active | boolean | | |
action_result.data.\*.data.\*.connector_guid | string | `fireamp connector guid` | |
action_result.data.\*.data.\*.connector_version | string | | |
action_result.data.\*.data.\*.demo | boolean | | True |
action_result.data.\*.data.\*.external_ip | string | `ip` | |
action_result.data.\*.data.\*.group_guid | string | | |
action_result.data.\*.data.\*.hostname | string | `host name` | Demo_AMP |
action_result.data.\*.data.\*.install_date | string | | |
action_result.data.\*.data.\*.internal_ips | string | `ip` | |
action_result.data.\*.data.\*.is_compromised | boolean | | |
action_result.data.\*.data.\*.isolation.available | boolean | | |
action_result.data.\*.data.\*.isolation.status | string | | |
action_result.data.\*.data.\*.last_seen | string | | |
action_result.data.\*.data.\*.links.computer | string | | |
action_result.data.\*.data.\*.links.group | string | `url` | |
action_result.data.\*.data.\*.links.trajectory | string | | https://api.amp.sourcefire.com/v1/computers/05f5a5e6-6281-4582-a2c9-6d28d451cd9e/trajectory |
action_result.data.\*.data.\*.network_addresses.\*.ip | string | `ip` | |
action_result.data.\*.data.\*.network_addresses.\*.mac | string | `mac address` | |
action_result.data.\*.data.\*.operating_system | string | | |
action_result.data.\*.data.\*.orbital.status | string | | not_enabled |
action_result.data.\*.data.\*.policy.guid | string | | |
action_result.data.\*.data.\*.policy.name | string | | |
action_result.data.\*.data.\*.windows_processor_id | string | | |
action_result.data.\*.metadata.links.self | string | | |
action_result.data.\*.metadata.results.current_item_count | numeric | | |
action_result.data.\*.metadata.results.index | numeric | | |
action_result.data.\*.metadata.results.items_per_page | numeric | | |
action_result.data.\*.metadata.results.total | numeric | | |
action_result.data.\*.version | string | | |
action_result.summary.total_endpoints | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt file'

Search for a file matching a SHA256 hash across all endpoints

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | SHA256 of file to hunt | string | `hash` `sha256` |
**check_execution** | optional | Check file execution | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.check_execution | boolean | | |
action_result.parameter.hash | string | `hash` `sha256` | |
action_result.data.\*.data.\*.active | boolean | | |
action_result.data.\*.data.\*.connector_guid | string | `fireamp connector guid` | |
action_result.data.\*.data.\*.file_execution_details.executed | boolean | | |
action_result.data.\*.data.\*.file_execution_details.file_name | string | `file path` | |
action_result.data.\*.data.\*.file_execution_details.file_path | string | `file name` | |
action_result.data.\*.data.\*.file_execution_details.message | string | | |
action_result.data.\*.data.\*.hostname | string | `host name` | |
action_result.data.\*.data.\*.links.computer | string | `url` | |
action_result.data.\*.data.\*.links.group | string | `url` | |
action_result.data.\*.data.\*.links.trajectory | string | | https://api.amp.sourcefire.com/v1/computers/120da585-44f6-4b50-8d29-e5a87b7548a0/trajectory?q=ed01ebfbc9eb5bbea545af4d01bf5f1071661840480439c6e5babe8e080e41aa |
action_result.data.\*.data.\*.windows_processor_id | string | | |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.metadata.results.current_item_count | numeric | | |
action_result.data.\*.metadata.results.index | numeric | | |
action_result.data.\*.metadata.results.items_per_page | numeric | | |
action_result.data.\*.metadata.results.total | numeric | | |
action_result.data.\*.version | string | | |
action_result.summary.device_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt ip'

Search for a given IP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address to hunt | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.ip | string | `ip` | |
action_result.data.\*.data.\*.active | boolean | | |
action_result.data.\*.data.\*.connector_guid | string | `fireamp connector guid` | |
action_result.data.\*.data.\*.hostname | string | `host name` | |
action_result.data.\*.data.\*.links.computer | string | `url` | |
action_result.data.\*.data.\*.links.group | string | `url` | |
action_result.data.\*.data.\*.links.trajectory | string | `url` | |
action_result.data.\*.data.\*.windows_processor_id | string | | |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.metadata.results.current_item_count | numeric | | |
action_result.data.\*.metadata.results.index | numeric | | |
action_result.data.\*.metadata.results.items_per_page | numeric | | |
action_result.data.\*.metadata.results.total | numeric | | |
action_result.data.\*.version | string | | |
action_result.summary.device_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt url'

Search for a given URL

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**url** | required | URL to hunt | string | `url` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.url | string | `url` | |
action_result.data.\*.data.\*.active | boolean | | |
action_result.data.\*.data.\*.connector_guid | string | `fireamp connector guid` | |
action_result.data.\*.data.\*.hostname | string | `host name` | |
action_result.data.\*.data.\*.links.computer | string | `url` | |
action_result.data.\*.data.\*.links.group | string | `url` | |
action_result.data.\*.data.\*.links.trajectory | string | `url` | |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.metadata.results.current_item_count | numeric | | |
action_result.data.\*.metadata.results.index | numeric | | |
action_result.data.\*.metadata.results.items_per_page | numeric | | |
action_result.data.\*.metadata.results.total | numeric | | |
action_result.data.\*.version | string | | |
action_result.summary.device_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'list groups'

List all of the groups are present in FireAMP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.data.\*.description | string | | |
action_result.data.\*.data.\*.guid | string | | |
action_result.data.\*.data.\*.links.group | string | `url` | |
action_result.data.\*.data.\*.name | string | | |
action_result.data.\*.data.\*.source | string | | |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.metadata.results.current_item_count | numeric | | |
action_result.data.\*.metadata.results.index | numeric | | |
action_result.data.\*.metadata.results.items_per_page | numeric | | |
action_result.data.\*.metadata.results.total | numeric | | |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.group_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list policies'

List all of the policies present in FireAMP

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | optional | Policy Name Filter | string | |
**product** | optional | Product Name Filter | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.name | string | | |
action_result.parameter.product | string | | windows |
action_result.data.\*.data.\*.default | boolean | | |
action_result.data.\*.data.\*.description | string | | |
action_result.data.\*.data.\*.guid | string | | |
action_result.data.\*.data.\*.links.policy | string | `url` | |
action_result.data.\*.data.\*.name | string | | |
action_result.data.\*.data.\*.product | string | | |
action_result.data.\*.data.\*.serial_number | numeric | | 23 |
action_result.data.\*.data.install_date | string | `url` | |
action_result.data.\*.metadata.links.next | string | `url` | |
action_result.data.\*.metadata.links.prev | string | `url` | |
action_result.data.\*.metadata.links.self | string | | https://api.amp.sourcefire.com/v1/policies?name%5B%5D=windows |
action_result.data.\*.metadata.results.current_item_count | numeric | | |
action_result.data.\*.metadata.results.index | numeric | | |
action_result.data.\*.metadata.results.items_per_page | numeric | | |
action_result.data.\*.metadata.results.total | numeric | | |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.policy_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'change policy'

Updates group to given windows policy

Type: **contain** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**policy_guid** | optional | Windows policy GUID | string | |
**policy_name** | optional | Windows policy name | string | |
**group_guid** | optional | Group GUID | string | |
**group_name** | optional | Group name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.group_guid | string | | |
action_result.parameter.group_name | string | | |
action_result.parameter.policy_guid | string | | |
action_result.parameter.policy_name | string | | |
action_result.data.\*.policy_changed | boolean | | |
action_result.data.\*.policy_guid | string | | |
action_result.summary.policy_changed | boolean | | |
action_result.summary.policy_guid | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'change group'

Change the group of provided GUID endpoint

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connector_guid** | required | Connector GUID on endpoint | string | `fireamp connector guid` |
**group_guid** | optional | Group GUID | string | |
**group_name** | optional | Group name | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.connector_guid | string | `fireamp connector guid` | |
action_result.parameter.group_guid | string | | |
action_result.parameter.group_name | string | | |
action_result.data.\*.group_changed | boolean | | |
action_result.data.\*.group_guid | string | | |
action_result.summary.group_changed | boolean | | |
action_result.summary.group_guid | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unquarantine device'

Stop host isolation based on connector GUID

Type: **correct** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connector_guid** | required | Connector GUID on endpoint | string | `fireamp connector guid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.connector_guid | string | `fireamp connector guid` | |
action_result.data | string | | |
action_result.data.\*.data.available | boolean | | |
action_result.data.\*.data.comment | string | | |
action_result.data.\*.version | string | | |
action_result.data.\*.data.isolated_by | string | | User |
action_result.data.\*.data.status | string | | |
action_result.data.\*.data.unlock_code | string | | |
action_result.data.\*.metadata.links.self | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'quarantine device'

Isolate host based on connector GUID

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connector_guid** | required | Connector GUID on endpoint | string | `fireamp connector guid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.connector_guid | string | `fireamp connector guid` | |
action_result.data | string | | |
action_result.data.\*.data.available | string | | |
action_result.data.\*.data.comment | string | | |
action_result.data.\*.data.isolated_by | string | | User |
action_result.data.\*.version | string | | |
action_result.data.\*.data.status | string | | |
action_result.data.\*.data.unlock_code | string | | |
action_result.data.\*.metadata.links.self | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'find device'

Finds system with search parameters

Type: **investigate** <br>
Read only: **True**

If finding by user, no other search options can be used. Additionally group name and group GUID are mutually exclusive search options.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**group_guid** | optional | Group GUID | string | |
**group_name** | optional | Group name | string | |
**user** | optional | User | string | |
**hostname** | optional | Hostname | string | |
**external_ip** | optional | External ip | string | `ip` |
**internal_ip** | optional | Internal ip | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.external_ip | string | `ip` | |
action_result.parameter.group_guid | string | | |
action_result.parameter.group_name | string | | |
action_result.parameter.hostname | string | | |
action_result.parameter.internal_ip | string | `ip` | |
action_result.parameter.user | string | | |
action_result.data.\*.data.\*.active | boolean | | |
action_result.data.\*.data.\*.connector_guid | string | `fireamp connector guid` | |
action_result.data.\*.data.\*.connector_version | string | | |
action_result.data.\*.data.\*.demo | boolean | | True |
action_result.data.\*.data.\*.external_ip | string | `ip` | |
action_result.data.\*.data.\*.group_guid | string | | |
action_result.data.\*.data.\*.hostname | string | `host name` | |
action_result.data.\*.data.\*.install_date | string | | 2021-04-20T09:55:41Z |
action_result.data.\*.data.\*.internal_ips | string | `ip` | |
action_result.data.\*.data.\*.is_compromised | boolean | | False |
action_result.data.\*.data.\*.isolation.available | boolean | | True |
action_result.data.\*.data.\*.isolation.status | string | | not_isolated |
action_result.data.\*.data.\*.last_seen | string | | 2021-05-20T09:55:41Z |
action_result.data.\*.data.\*.links.computer | string | `url` | |
action_result.data.\*.data.\*.links.group | string | `url` | |
action_result.data.\*.data.\*.links.trajectory | string | `url` | |
action_result.data.\*.data.\*.network_addresses.\*.ip | string | `ip` | |
action_result.data.\*.data.\*.network_addresses.\*.mac | string | `mac address` | |
action_result.data.\*.data.\*.operating_system | string | | |
action_result.data.\*.data.\*.orbital.status | string | | not_enabled |
action_result.data.\*.data.\*.policy.guid | string | | |
action_result.data.\*.data.\*.policy.name | string | | |
action_result.data.\*.data.\*.windows_processor_id | string | | 65a9fd1b78043e2 |
action_result.data.\*.data.demo | boolean | | True |
action_result.data.\*.data.install_date | string | | 2021-04-20T09:55:41Z |
action_result.data.\*.data.is_compromised | boolean | | False |
action_result.data.\*.data.isolation.available | boolean | | False |
action_result.data.\*.data.isolation.status | string | | not_isolated |
action_result.data.\*.data.last_seen | string | | 2021-05-20T09:55:41Z |
action_result.data.\*.data.orbital.status | string | | not_enabled |
action_result.data.\*.data.windows_processor_id | string | | 198a4d60e2f7b53 |
action_result.data.\*.links.self | string | | https://api.amp.sourcefire.com/v1/computers/user_activity?q=johndoe |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.metadata.results.current_item_count | numeric | | 25 |
action_result.data.\*.metadata.results.index | numeric | | 0 |
action_result.data.\*.metadata.results.items_per_page | numeric | | 500 |
action_result.data.\*.metadata.results.total | numeric | | 25 |
action_result.data.\*.results.current_item_count | numeric | | 7 |
action_result.data.\*.results.index | numeric | | 0 |
action_result.data.\*.results.items_per_page | numeric | | 500 |
action_result.data.\*.results.total | numeric | | 7 |
action_result.data.\*.version | string | | |
action_result.summary.total_endpoints | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'get device info'

Get information about a device, given its connector GUID

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connector_guid** | required | Connector GUID on endpoint | string | `fireamp connector guid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.connector_guid | string | `fireamp connector guid` | |
action_result.data.\*.data.active | boolean | | |
action_result.data.\*.data.connector_guid | string | `fireamp connector guid` | |
action_result.data.\*.data.connector_version | string | | |
action_result.data.\*.data.external_ip | string | `ip` | |
action_result.data.\*.data.group_guid | string | | |
action_result.data.\*.data.hostname | string | `host name` | |
action_result.data.\*.data.internal_ips | string | `ip` | |
action_result.data.\*.data.links.computer | string | `url` | |
action_result.data.\*.data.demo | boolean | | True |
action_result.data.\*.data.orbital.status | string | | not_enabled |
action_result.data.\*.data.isolation.status | string | | not_isolated |
action_result.data.\*.data.isolation.available | boolean | | True |
action_result.data.\*.data.last_seen | string | | 2021-05-20T09:55:41Z |
action_result.data.\*.data.install_date | string | | 2021-04-20T09:55:41Z |
action_result.data.\*.data.is_compromised | boolean | | False |
action_result.data.\*.data.windows_processor_id | string | | 198a4d60e2f7b53 |
action_result.data.\*.data.links.group | string | `url` | |
action_result.data.\*.data.links.trajectory | string | `url` | |
action_result.data.\*.data.network_addresses.\*.ip | string | `ip` | |
action_result.data.\*.data.network_addresses.\*.mac | string | `mac address` | |
action_result.data.\*.data.operating_system | string | | |
action_result.data.\*.data.policy.guid | string | | |
action_result.data.\*.data.policy.name | string | | |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.version | string | | |
action_result.summary.total_endpoints | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'block hash'

Add a file hash (sha256 only) to a file list specified by GUID

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_list_guid** | required | File List GUID on FireAMP | string | `fireamp file list guid` |
**hash** | required | SHA256 of file to add to file list | string | `hash` `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.hash | string | `hash` `sha256` | 27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.data.description | string | | |
action_result.data.\*.data.links.file_list | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.data.sha256 | string | `hash` `sha256` | 27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.data.source | string | | Created by entering SHA-256 via Public api. |
action_result.data.\*.metadata.links.self | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e/files/27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.file_added_to_list | boolean | | True False |
action_result.summary.file_hash_added | boolean | | |
action_result.message | string | | Hash added to list |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unblock hash'

Remove a file hash (sha256 only) from a file list specified by GUID

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_list_guid** | required | File List GUID on FireAMP | string | `fireamp file list guid` |
**hash** | required | SHA256 of file to remove from file list | string | `hash` `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.hash | string | `hash` `sha256` | 27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.data.description | string | | |
action_result.data.\*.metadata.links.self | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e/files/27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.file_removed_from_list | boolean | | True False |
action_result.message | string | | Hash removed from list |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'allow hash'

Add a file hash (sha256 only) to a file list specified by GUID

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_list_guid** | required | File List GUID on FireAMP | string | `fireamp file list guid` |
**hash** | required | SHA256 of file to add to file list | string | `hash` `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.hash | string | `hash` `sha256` | 27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.data.description | string | | |
action_result.data.\*.data.links.file_list | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.data.sha256 | string | `hash` `sha256` | 27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.data.source | string | | Created by entering SHA-256 via Public api. |
action_result.data.\*.metadata.links.self | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e/files/27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.file_added_to_list | boolean | | True False |
action_result.summary.file_hash_added | boolean | | |
action_result.message | string | | Hash added to list |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'disallow hash'

Remove all sha256 file hashes from a file list specified by GUID

Type: **contain** <br>
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_list_guid** | required | File List GUID on FireAMP | string | `fireamp file list guid` |
**hash** | required | SHA256 of file to remove from file list | string | `hash` `sha256` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.hash | string | `hash` `sha256` | 27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.data.description | string | | |
action_result.data.\*.metadata.links.self | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e/files/27b10529a38e0fd3128a84a543de108dc83c2b0e786ea81df8a8dc4a9e47a2e4 |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.file_removed_from_list | boolean | | True False |
action_result.message | string | | Hash removed from list |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list filelists'

List all of the File Lists (application blocking & simple custom detections) in FireAMP

Type: **generic** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.data.\*.guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.links.file_list | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.name | string | | Test hash list |
action_result.data.\*.type | string | | application_blocking |
action_result.summary.total_lists | numeric | | 3 |
action_result.message | string | | Total lists: 3 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get filelist'

Get all of the hashes in a File List in FireAMP. Lists can be retrieved by UUID, or file list name and type

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_list_guid** | optional | File List GUID on FireAMP | string | `fireamp file list guid` |
**name** | optional | File list name | string | |
**type** | optional | File list type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | |
action_result.data.\*.data.guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.data.items.\*.description | string | | Manual add |
action_result.data.\*.data.items.\*.links.file_list | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.data.items.\*.sha256 | string | `sha256` | ad3f8b790a9012c3ab113501a0d31b6ca5af6a07f7ac5ee745c4bbd5757e2cb3 |
action_result.data.\*.data.name | string | | |
action_result.data.\*.data.policies.\*.guid | string | | |
action_result.data.\*.data.policies.\*.links.policy | string | `url` | |
action_result.data.\*.data.policies.\*.name | string | | Test hash list |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.metadata.results.current_item_count | numeric | | |
action_result.data.\*.metadata.results.index | numeric | | |
action_result.data.\*.metadata.results.items_per_page | numeric | | |
action_result.data.\*.metadata.results.total | numeric | | |
action_result.data.\*.version | string | | |
action_result.summary.file_count | numeric | | |
action_result.summary.file_list_guid | string | | |
action_result.summary.file_list_name | string | | |
action_result.summary.total_endpoints | numeric | | |
action_result.summary.total_hashes | numeric | | 1 |
action_result.message | string | | Total hashes: 2 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'remove listitem'

Removes file hash from file list

Type: **correct** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash (sha256) | string | `sha256` |
**file_list_guid** | optional | File List GUID on FireAMP | string | `fireamp file list guid` |
**name** | optional | File list name | string | |
**type** | optional | File list type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.hash | string | `sha256` | |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | |
action_result.data.\*.file_deleted | boolean | | |
action_result.message | string | | File deleted from list |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.summary.file_deleted | boolean | | True |

## action: 'add listitem'

Add file hash as listitem to file list

Type: **correct** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash (sha256) | string | `sha256` |
**file_list_guid** | optional | File List GUID on FireAMP | string | `fireamp file list guid` |
**name** | optional | File list name | string | |
**type** | optional | File list type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.hash | string | `sha256` | |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | |
action_result.data.\*.data.links.file_list | string | | https://api.amp.sourcefire.com/v1/file_lists/93265c88-0b72-40eb-8187-7fc58b5e31f8 |
action_result.data.\*.data.sha256 | string | | f69fc2fd5bd864916a3285f9e3a691f6f060d430d251d18944ce3e69066d04b7 |
action_result.data.\*.data.source | string | | Created by entering SHA-256 via Public api. |
action_result.data.\*.file_added | boolean | | True |
action_result.data.\*.metadata.links.self | string | | https://api.amp.sourcefire.com/v1/file_lists/93265c88-0b72-40eb-8187-7fc58b5e31f8/files/f69fc2fd5bd864916a3285f9e3a691f6f060d430d251d18944ce3e69066d04b7 |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.file_added | boolean | | True |
action_result.summary.file_deleted | boolean | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'find listitem'

Finds file hash in specified file list

Type: **generic** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash (sha256) | string | `sha256` |
**file_list_guid** | optional | File List GUID on FireAMP | string | `fireamp file list guid` |
**name** | optional | File list name to find the file list GUID | string | |
**type** | optional | File list type to find the file list GUID | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_list_guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.parameter.hash | string | `sha256` | |
action_result.parameter.name | string | | |
action_result.parameter.type | string | | |
action_result.data.\*.data.description | string | | Manual add |
action_result.data.\*.data.guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.data.links.file_list | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.data.sha256 | string | `sha256` | ad3f8b790a9012c3ab113501a0d31b6ca5af6a07f7ac5ee745c4bbd5757e2cb3 |
action_result.data.\*.data.source | string | | Created by entering SHA-256 via Web from 23.251.93.203. |
action_result.data.\*.metadata.links.self | string | `url` | |
action_result.data.\*.version | string | | |
action_result.summary.file_found | boolean | | |
action_result.message | string | | File found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get device trajectory'

Retrieve trajectory info about a device

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connector_guid** | required | Connector GUID on endpoint | string | `fireamp connector guid` |
**filter** | optional | Filter trajectory info | string | `sha256` `url` `ip` |
**days_back** | optional | Return events from a number of days back | numeric | |
**executed_only** | optional | Only retrieve events where the file has been executed | boolean | |
**limit** | optional | Limit number of results | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.connector_guid | string | `fireamp connector guid` | 0cdd56bc-e299-4547-ae1d-148aae71de03 |
action_result.parameter.days_back | numeric | | |
action_result.parameter.executed_only | boolean | | True False |
action_result.parameter.filter | string | `sha256` `url` `ip` | |
action_result.parameter.limit | numeric | | 100 |
action_result.data.\*.computer.active | boolean | | True False |
action_result.data.\*.computer.connector_guid | string | | 0cdd56bc-e299-4547-ae1d-148aae71de03 |
action_result.data.\*.computer.connector_version | string | | 7.2.3.11648 |
action_result.data.\*.computer.demo | boolean | | True |
action_result.data.\*.computer.external_ip | string | `ip` | 35.161.149.114 |
action_result.data.\*.computer.group_guid | string | | a0841d16-1b37-4eac-9154-8ed475534f9e |
action_result.data.\*.computer.hostname | string | `host name` | commando.skynet.lab |
action_result.data.\*.computer.install_date | string | | 2019-10-18T20:49:35Z |
action_result.data.\*.computer.internal_ips | string | | 172.18.85.49 |
action_result.data.\*.computer.is_compromised | boolean | | False |
action_result.data.\*.computer.isolation.available | boolean | | True False |
action_result.data.\*.computer.isolation.status | string | | not_isolated |
action_result.data.\*.computer.links.computer | string | `url` | https://api.amp.sourcefire.com/v1/computers/0cdd56bc-e299-4547-ae1d-148aae71de03 |
action_result.data.\*.computer.links.group | string | `url` | https://api.amp.sourcefire.com/v1/groups/a0841d16-1b37-4eac-9154-8ed475534f9e |
action_result.data.\*.computer.links.trajectory | string | `url` | https://api.amp.sourcefire.com/v1/computers/0cdd56bc-e299-4547-ae1d-148aae71de03/trajectory |
action_result.data.\*.computer.network_addresses.\*.ip | string | `ip` | 192.168.66.238 |
action_result.data.\*.computer.network_addresses.\*.mac | string | | 00:50:56:ac:80:e5 |
action_result.data.\*.computer.operating_system | string | | Windows 10 Enterprise |
action_result.data.\*.computer.orbital.status | string | | enabled |
action_result.data.\*.computer.policy.guid | string | | cbb3691a-db66-422f-b770-b79bd12653d8 |
action_result.data.\*.computer.policy.name | string | | Protect-No-Proxy |
action_result.data.\*.computer.windows_processor_id | string | | 1f8bfbff000306e4 |
action_result.data.\*.events.\*.file.parent.identity.md5 | string | | 38ae1b3c38faef56fe4907922f0385ba |
action_result.data.\*.events.\*.file.parent.identity.sha1 | string | | 84123a3decdaa217e3588a1de59fe6cee1998004 |
action_result.data.\*.events.\*.file.parent.file_name | string | | explorer.exe |
action_result.data.\*.events.\*.file.parent.process_id | numeric | | 2632 |
action_result.data.\*.events.\*.scan.clean | boolean | | True |
action_result.data.\*.events.\*.scan.description | string | | Flash Scan |
action_result.data.\*.events.\*.scan.scanned_files | numeric | | 2872 |
action_result.data.\*.events.\*.scan.scanned_paths | numeric | | 0 |
action_result.data.\*.events.\*.scan.scanned_processes | numeric | | 49 |
action_result.data.\*.events.\*.scan.malicious_detections | numeric | | 0 |
action_result.data.\*.data.description | string | | Manual add |
action_result.data.\*.data.guid | string | `fireamp file list guid` | 81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.data.sha256 | string | `sha256` | ad3f8b790a9012c3ab113501a0d31b6ca5af6a07f7ac5ee745c4bbd5757e2cb3 |
action_result.data.\*.data.source | string | | Created by entering SHA-256 via Web from 23.251.93.203. |
action_result.data.\*.events.\*.cloud_ioc.description | string | | PowerShell is a Windows utility that allows access to many Microsoft APIs within a shell environment. In this case, a script attempted to download a file or script to the local system and then execute it. Malware authors may use this to download items, rename them, execute and delete them with a single command. |
action_result.data.\*.events.\*.cloud_ioc.short_description | string | | W32.PowershellDownloadedExecutable.ioc |
action_result.data.\*.events.\*.command_line.arguments | string | | -Embedding |
action_result.data.\*.events.\*.command_line.environment.Path | string | `file path` | |
action_result.data.\*.events.\*.command_line.environment.USERNAME | string | `user name` | COMMANDO$ |
action_result.data.\*.events.\*.date | string | | 2020-04-22T18:49:34+00:00 |
action_result.data.\*.events.\*.detection | string | | W32.6A37D750F0-100.SBX.TG |
action_result.data.\*.events.\*.id | string | | 6812581201115613122 |
action_result.data.\*.events.\*.severity | string | | |
action_result.data.\*.events.\*.detection_id | string | | |
action_result.data.\*.events.\*.event_type | string | | |
action_result.data.\*.data.links.file_list | string | `url` | https://api.amp.sourcefire.com/v1/file_lists/81486554-e6ef-4a57-90ee-bc564a98a94e |
action_result.data.\*.events.\*.event_type_id | numeric | | 553648155 |
action_result.data.\*.events.\*.file.disposition | string | | Unknown |
action_result.data.\*.events.\*.file.file_name | string | `file name` `sha1` | prefs-1.js |
action_result.data.\*.events.\*.file.file_path | string | `file name` | /c:/users/maclemon/appdata/roaming/mozilla/firefox/profiles/x6berjvs.default-release/prefs-1.js |
action_result.data.\*.events.\*.file.file_type | string | | Script |
action_result.data.\*.events.\*.file.identity.md5 | string | | 41476df3138717868118d8542cf3d1d6 |
action_result.data.\*.events.\*.file.identity.sha1 | string | | 5ca4bef8de6def53519d4b22632675bb4c1e470b |
action_result.data.\*.events.\*.file.identity.sha256 | string | `sha256` | a36f0d4c081b86ecca210a64cf67c948bd3535e719e255638602a92c94eb9abc |
action_result.data.\*.events.\*.file.parent.disposition | string | | Unknown |
action_result.data.\*.events.\*.file.parent.identity.sha256 | string | `sha256` | 8bcfd8420d721cc0ca50c1bef653e63e013ce201dfcca5927228eb25c9abf606 |
action_result.data.\*.events.\*.group_guids | string | | a0841d16-1b37-4eac-9154-8ed475534f9e |
action_result.data.\*.events.\*.isolation.duration | numeric | | 46 |
action_result.data.\*.events.\*.network_info.dirty_url | string | `url` | http://settings-win.data.microsoft.com:443 |
action_result.data.\*.events.\*.network_info.local_ip | string | `ip` | 192.168.66.238 |
action_result.data.\*.events.\*.network_info.local_port | numeric | | 19734 |
action_result.data.\*.events.\*.network_info.nfm.direction | string | | Outgoing connection from |
action_result.data.\*.events.\*.network_info.nfm.protocol | string | | TCP |
action_result.data.\*.events.\*.network_info.parent.disposition | string | | Clean |
action_result.data.\*.events.\*.network_info.parent.identity.sha256 | string | `sha256` | dd191a5b23df92e12a8852291f9fb5ed594b76a28a5a464418442584afd1e048 |
action_result.data.\*.events.\*.network_info.remote_ip | string | `ip` | 192.168.66.215 |
action_result.data.\*.events.\*.network_info.remote_port | numeric | | 389 |
action_result.data.\*.events.\*.start_date | string | | 2018-01-07T04:12:27+00:00 |
action_result.data.\*.events.\*.start_timestamp | numeric | | 1515298347 |
action_result.data.\*.events.\*.timestamp | numeric | | 1587581374 |
action_result.data.\*.events.\*.timestamp_nanoseconds | numeric | | 13538365 |
action_result.data.\*.events.\*.vulnerabilities.\*.cve | string | | CVE-2014-0260 |
action_result.data.\*.events.\*.vulnerabilities.\*.name | string | | Microsoft Office |
action_result.data.\*.events.\*.vulnerabilities.\*.score | numeric | | 9.3 |
action_result.data.\*.events.\*.vulnerabilities.\*.url | string | | https://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2014-0260 |
action_result.data.\*.events.\*.vulnerabilities.\*.version | string | | 2013 |
action_result.data.\*.metadata.links.self | string | `url` | https://api.amp.sourcefire.com/v1/computers/0cdd56bc-e299-4547-ae1d-148aae71de03/trajectory?limit=100 |
action_result.data.\*.version | string | | v1.2.0 |
action_result.summary.file_found | boolean | | |
action_result.message | string | | File found |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get device events'

Retrieve device events

Type: **investigate** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connector_guid** | optional | Connector GUID on endpoint | string | `fireamp connector guid` |
**detection_sha256** | optional | Filter by detection sha256 | string | `hash` |
**application_sha256** | optional | Filter by application sha256 | string | `hash` |
**group_guid** | optional | Filter by group GUID | string | |
**start_date** | optional | Filter by event start date | string | |
**offset** | optional | Results offset | numeric | |
**event_type** | optional | Filter by event type | string | |
**limit** | optional | Limit number of results returned | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.application_sha256 | string | `hash` | |
action_result.parameter.connector_guid | string | `fireamp connector guid` | 71841cfb-1892-46b5-b7d7-b18d068246b4 |
action_result.parameter.detection_sha256 | string | `hash` | |
action_result.parameter.event_type | string | | |
action_result.parameter.group_guid | string | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.limit | numeric | | 10 |
action_result.parameter.offset | numeric | | |
action_result.parameter.start_date | string | | |
action_result.data.\*.events.\*.cloud_ioc.description | string | | A named pipe was created in a manner similar to that used for local privilege escalation through named pipe impersonation. Tools such as meterpreter often use this technique to escalate to NT Authority\\System. |
action_result.data.\*.events.\*.cloud_ioc.short_description | string | | W32.PossibleNamedPipeImpersonation.ioc |
action_result.data.\*.events.\*.computer.active | boolean | | True False |
action_result.data.\*.events.\*.computer.connector_guid | string | | 71841cfb-1892-46b5-b7d7-b18d068246b4 |
action_result.data.\*.events.\*.computer.external_ip | string | `ip` | 174.138.94.48 |
action_result.data.\*.events.\*.computer.links.computer | string | `ip` | https://api.amp.sourcefire.com/v1/computers/71841cfb-1892-46b5-b7d7-b18d068246b4 |
action_result.data.\*.events.\*.computer.links.group | string | `url` | https://api.amp.sourcefire.com/v1/groups/20701584-ff6f-4b78-afed-e2e801366a82 |
action_result.data.\*.events.\*.computer.links.trajectory | string | `url` | https://api.amp.sourcefire.com/v1/computers/71841cfb-1892-46b5-b7d7-b18d068246b4/trajectory |
action_result.data.\*.events.\*.computer.network_addresses.\*.ip | string | | 105.186.48.59 |
action_result.data.\*.events.\*.computer.network_addresses.\*.mac | string | | 0e:12:c4:de:70:ee |
action_result.data.\*.events.\*.event_type | string | | Uninstall |
action_result.data.\*.events.\*.computer.user | string | | pwned@W10-CUCKOO-MC |
action_result.data.\*.events.\*.computer.hostname | string | `host name` | W10-CUCKOO-MC |
action_result.data.\*.events.\*.id | numeric | | 17965765 |
action_result.data.\*.events.\*.connector_guid | string | | 71841cfb-1892-46b5-b7d7-b18d068246b4 |
action_result.data.\*.events.\*.date | string | | 2020-04-06T13:03:50+00:00 |
action_result.data.\*.events.\*.detection | string | | Doc.Dropper.Valyria::in03.talos |
action_result.data.\*.events.\*.detection_id | string | | 6812581201115613122 |
action_result.data.\*.events.\*.event_type_id | numeric | | 553648166 |
action_result.data.\*.events.\*.file.archived_file.disposition | string | | Malicious |
action_result.data.\*.events.\*.file.archived_file.identity.sha256 | string | | 0a99238e1ebebc47d7a89b2ccddfae537479f7f77322b5d4941315d3f7e5ca48 |
action_result.data.\*.events.\*.file.attack_details.application | string | | firefox.exe |
action_result.data.\*.events.\*.file.attack_details.attacked_module | string | | C:\\Program Files\\Mozilla Firefox\\xul.dll |
action_result.data.\*.events.\*.file.attack_details.base_address | string | | 0x7D1E0000 |
action_result.data.\*.events.\*.file.attack_details.indicators.\*.description | string | | DealPly is adware, which claims to improve your online shopping experience. It is often bundled into other legitimate installers and is difficult to uninstall. It creates pop-up advertisements and injects advertisements on webpages. Adware has also been known to download and install malware. |
action_result.data.\*.events.\*.file.attack_details.indicators.\*.id | string | | 44cfe1c4-3dc4-4619-be6b-88c9d69c2a97 |
action_result.data.\*.events.\*.file.attack_details.indicators.\*.severity | string | | medium |
action_result.data.\*.events.\*.file.attack_details.indicators.\*.short_description | string | | Dealply adware detected |
action_result.data.\*.events.\*.file.disposition | string | | Malicious |
action_result.data.\*.events.\*.file.file_name | string | `file name` | $RY69ASX.exe |
action_result.data.\*.events.\*.file.file_path | string | `file name` `file path` | \\\\?\\C:\\$Recycle.Bin\\S-1-5-21-2502938909-339922712-2837714241-1001\\$RY69ASX.exe |
action_result.data.\*.events.\*.file.identity.md5 | string | `md5` | 8b2bd6352e0ffe8b0e2bad20b49c8682 |
action_result.data.\*.events.\*.file.identity.sha1 | string | `sha1` | b307e0b8035287e15ac473d70e54566e462596c1 |
action_result.data.\*.events.\*.file.identity.sha256 | string | `sha256` | b81302bc5cbfeddf3b608a60b25f86944eddcef617e733cddf0fc93ee4ccc7ab |
action_result.data.\*.events.\*.file.parent.disposition | string | | Clean |
action_result.data.\*.events.\*.file.parent.file_name | string | `file name` | explorer.exe |
action_result.data.\*.events.\*.file.parent.identity.md5 | string | `md5` | f7dc8a74e30e08b9510380274cfb9288 |
action_result.data.\*.events.\*.file.parent.identity.sha1 | string | `sha1` | c893cf07e5f65749cd66e17d9523638b132c87b2 |
action_result.data.\*.events.\*.file.parent.identity.sha256 | string | `sha256` | c5e88d778c0b118d49bef467ed059c09b61deea505d2a3d5ca1dcc0a5cdf752f |
action_result.data.\*.events.\*.file.parent.process_id | numeric | | 3124 |
action_result.data.\*.events.\*.group_guids | string | | 20701584-ff6f-4b78-afed-e2e801366a82 |
action_result.data.\*.events.\*.isolation.duration | numeric | | 46 |
action_result.data.\*.events.\*.isolation.user | string | | User |
action_result.data.\*.events.\*.network_info.dirty_url | string | | http://dak1otavola1ndos.com/h/index.php |
action_result.data.\*.events.\*.network_info.local_ip | string | | 192.168.1.3 |
action_result.data.\*.events.\*.network_info.local_port | numeric | | 55810 |
action_result.data.\*.events.\*.network_info.nfm.direction | string | | Outgoing connection from |
action_result.data.\*.events.\*.network_info.nfm.protocol | string | | TCP |
action_result.data.\*.events.\*.network_info.parent.disposition | string | | Clean |
action_result.data.\*.events.\*.network_info.parent.file_name | string | | iexplore.exe |
action_result.data.\*.events.\*.network_info.parent.identity.md5 | string | | b3581f426dc500a51091cdd5bacf0454 |
action_result.data.\*.events.\*.network_info.parent.identity.sha1 | string | | 8de30174cebc8732f1ba961e7d93fe5549495a80 |
action_result.data.\*.events.\*.network_info.parent.identity.sha256 | string | | b4e5c2775de098946b4e11aba138b89d42b88c1dbd4d5ec879ef6919bf018132 |
action_result.data.\*.events.\*.network_info.parent.process_id | numeric | | 3136 |
action_result.data.\*.events.\*.network_info.remote_ip | string | | 75.102.25.76 |
action_result.data.\*.events.\*.network_info.remote_port | numeric | | 443 |
action_result.data.\*.events.\*.scan.clean | boolean | | True |
action_result.data.\*.events.\*.scan.description | string | | C:\\Program Files\\DVD Maker |
action_result.data.\*.events.\*.scan.malicious_detections | numeric | | 0 |
action_result.data.\*.events.\*.scan.scanned_files | numeric | | 9 |
action_result.data.\*.events.\*.scan.scanned_paths | numeric | | 2 |
action_result.data.\*.events.\*.scan.scanned_processes | numeric | | 0 |
action_result.data.\*.events.\*.severity | string | | Medium |
action_result.data.\*.events.\*.start_date | string | | 2016-09-22T19:39:33+00:00 |
action_result.data.\*.events.\*.start_timestamp | numeric | | 1474573173 |
action_result.data.\*.events.\*.tactics.\*.description | string | | <p>The adversary is trying to avoid being detected.</p> <p>Defense Evasion consists of techniques that adversaries use to avoid detection throughout their compromise. Techniques used for defense evasion include uninstalling/disabling security software or obfuscating/encrypting data and scripts. Adversaries also leverage and abuse trusted processes to hide and masquerade their malware. Other tactics’ techniques are cross-listed here when those techniques include the added benefit of subverting defenses.</p> |
action_result.data.\*.events.\*.tactics.\*.external_id | string | | TA0005 |
action_result.data.\*.events.\*.tactics.\*.mitre_name | string | | tactic |
action_result.data.\*.events.\*.tactics.\*.mitre_url | string | | https://attack.mitre.org/tactics/TA0005 |
action_result.data.\*.events.\*.tactics.\*.name | string | | Defense Evasion |
action_result.data.\*.events.\*.techniques.\*.data_sources | string | | File: File Content, File: File Metadata, File: File Creation, Process: Process Creation, Command: Command Execution, Command: Command Execution |
action_result.data.\*.events.\*.techniques.\*.description | string | | <p>Adversaries may attempt to make an executable or file difficult to discover or analyze by encrypting, encoding, or otherwise obfuscating its contents on the system or in transit. This is common behavior that can be used across different platforms and the network to evade defenses.</p> <p>Payloads may be compressed, archived, or encrypted in order to avoid detection. These payloads may be used during Initial Access or later to mitigate detection. Sometimes a user's action may be required to open and <a href="https://attack.mitre.org/techniques/T1140">Deobfuscate/Decode Files or Information</a> for <a href="https://attack.mitre.org/techniques/T1204">User Execution</a>. The user may also be required to input a password to open a password protected compressed/encrypted file that was provided by the adversary. (Citation: Volexity PowerDuke November 2016) Adversaries may also used compressed or archived scripts, such as JavaScript.</p> <p>Portions of files can also be encoded to hide the plain-text strings that would otherwise help defenders with discovery. (Citation: Linux/Cdorked.A We Live Security Analysis) Payloads may also be split into separate, seemingly benign files that only reveal malicious functionality when reassembled. (Citation: Carbon Black Obfuscation Sept 2016)</p> <p>Adversaries may also obfuscate commands executed from payloads or directly via a <a href="https://attack.mitre.org/techniques/T1059">Command and Scripting Interpreter</a>. Environment variables, aliases, characters, and other platform/language specific semantics can be used to evade signature based detections and application control mechanisms. (Citation: FireEye Obfuscation June 2017) (Citation: FireEye Revoke-Obfuscation July 2017)(Citation: PaloAlto EncodedCommand March 2017)</p> |
action_result.data.\*.events.\*.techniques.\*.external_id | string | | T1027 |
action_result.data.\*.events.\*.techniques.\*.mitre_name | string | | technique |
action_result.data.\*.events.\*.techniques.\*.mitre_url | string | | https://attack.mitre.org/techniques/T1027 |
action_result.data.\*.events.\*.techniques.\*.name | string | | Obfuscated Files or Information |
action_result.data.\*.events.\*.techniques.\*.permissions | string | | |
action_result.data.\*.events.\*.techniques.\*.platforms | string | | Linux, macOS, Windows |
action_result.data.\*.events.\*.techniques.\*.system_requirements | string | | |
action_result.data.\*.events.\*.techniques.\*.tactics_names | string | | Defense Evasion |
action_result.data.\*.events.\*.threat_hunting.incident_end_time | numeric | | 1621498185 |
action_result.data.\*.events.\*.threat_hunting.incident_hunt_guid | string | | 00712651-e534-4851-ac6d-d4017f9c1714 |
action_result.data.\*.events.\*.threat_hunting.incident_remediation | string | | We recommend the following:

- Isolation of the affected hosts from the network
- Perform forensic investigation
  - Review all activity performed by host users
  - Review all activities of affected hosts
  - Upload all files found under the following folders to ThreatGrid for analysis, then delete all malicious files
- Reimage the affected systems if necessary.

If you feel your organization needs assistance with any aspect of Incident Response, we do have Cisco Talos Incident Response available. Please reach out to your Cisco Account Manager about a Talos IR Retainer, or reach out to 1-844-831-7715 for emergencies 24 hours a day. For more information visit https://talosintelligence.com/incident_response. |
action_result.data.\*.events.\*.threat_hunting.incident_report_guid | string | | 54259a50-d6bf-483a-bc49-979f12cfa591 |
action_result.data.\*.events.\*.threat_hunting.incident_start_time | numeric | | 1621498117 |
action_result.data.\*.events.\*.threat_hunting.incident_summary | string | | The affected host executed schtasks.exe to schedule the launch of certutil.exe. The surrounding data of this hunt lead are as follows:

- The user opened a malicious Word document from a phishing email
- The Word document dropped two VBScripts
- Word created a scheduled task to launch certutil.exe, which is unusual for parent-child relationships
- Word executes one of the VBScripts it had dropped earlier using WMIC. (AMP detects launching of WScript by Word)
- WScript runs reconnaissance commands to discover the network information, domain controller list etc. and stores data in recon.txt
- WScript creates an archive called sweetz.cab of stolen data using makecab utility
- WScript uploads that cab file to a suspicious FTP server
- WScript starts collecting sensitive information such as passwords in a file called goodies.txt
- WScript makes an archive and uploads it via FTP
- Certutil.exe executes via the earlier scheduled task, due to COM hijacking, it launches a PowerShell script (simply shows a dialog box demonstrating arbitrary code execution) |
  action_result.data.\*.events.\*.threat_hunting.incident_title | string | | Certutil.exe Executed by Schtasks.exe (Demo Data) |
  action_result.data.\*.events.\*.threat_hunting.severity | string | | critical |
  action_result.data.\*.events.\*.threat_hunting.tactics.\*.description | string | | <p>The adversary is trying to avoid being detected.</p> <p>Defense Evasion consists of techniques that adversaries use to avoid detection throughout their compromise. Techniques used for defense evasion include uninstalling/disabling security software or obfuscating/encrypting data and scripts. Adversaries also leverage and abuse trusted processes to hide and masquerade their malware. Other tactics’ techniques are cross-listed here when those techniques include the added benefit of subverting defenses.</p> |
  action_result.data.\*.events.\*.threat_hunting.tactics.\*.external_id | string | | TA0005 |
  action_result.data.\*.events.\*.threat_hunting.tactics.\*.mitre_name | string | | tactic |
  action_result.data.\*.events.\*.threat_hunting.tactics.\*.mitre_url | string | | https://attack.mitre.org/tactics/TA0005 |
  action_result.data.\*.events.\*.threat_hunting.tactics.\*.name | string | | Defense Evasion |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.data_sources | string | | File: File Content, File: File Metadata, File: File Creation, Process: Process Creation, Command: Command Execution, Command: Command Execution |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.description | string | | <p>Adversaries may attempt to make an executable or file difficult to discover or analyze by encrypting, encoding, or otherwise obfuscating its contents on the system or in transit. This is common behavior that can be used across different platforms and the network to evade defenses.</p> <p>Payloads may be compressed, archived, or encrypted in order to avoid detection. These payloads may be used during Initial Access or later to mitigate detection. Sometimes a user's action may be required to open and <a href="https://attack.mitre.org/techniques/T1140">Deobfuscate/Decode Files or Information</a> for <a href="https://attack.mitre.org/techniques/T1204">User Execution</a>. The user may also be required to input a password to open a password protected compressed/encrypted file that was provided by the adversary. (Citation: Volexity PowerDuke November 2016) Adversaries may also used compressed or archived scripts, such as JavaScript.</p> <p>Portions of files can also be encoded to hide the plain-text strings that would otherwise help defenders with discovery. (Citation: Linux/Cdorked.A We Live Security Analysis) Payloads may also be split into separate, seemingly benign files that only reveal malicious functionality when reassembled. (Citation: Carbon Black Obfuscation Sept 2016)</p> <p>Adversaries may also obfuscate commands executed from payloads or directly via a <a href="https://attack.mitre.org/techniques/T1059">Command and Scripting Interpreter</a>. Environment variables, aliases, characters, and other platform/language specific semantics can be used to evade signature based detections and application control mechanisms. (Citation: FireEye Obfuscation June 2017) (Citation: FireEye Revoke-Obfuscation July 2017)(Citation: PaloAlto EncodedCommand March 2017)</p> |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.external_id | string | | T1027 |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.mitre_name | string | | technique |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.mitre_url | string | | https://attack.mitre.org/techniques/T1027 |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.name | string | | Obfuscated Files or Information |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.permissions | string | | |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.platforms | string | | Linux, macOS, Windows |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.system_requirements | string | | |
  action_result.data.\*.events.\*.threat_hunting.techniques.\*.tactics_names | string | | Defense Evasion |
  action_result.data.\*.events.\*.timestamp | numeric | | 1586178230 |
  action_result.data.\*.events.\*.timestamp_nanoseconds | numeric | | 619724887 |
  action_result.data.\*.events.\*.vulnerabilities.\*.cve | string | | CVE-2015-7204 |
  action_result.data.\*.events.\*.vulnerabilities.\*.name | string | | Mozilla Firefox |
  action_result.data.\*.events.\*.vulnerabilities.\*.score | string | | 6.8 |
  action_result.data.\*.events.\*.vulnerabilities.\*.url | string | | https://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2015-7204 |
  action_result.data.\*.events.\*.vulnerabilities.\*.version | string | | 41.0 |
  action_result.data.\*.metadata.links.next | string | `url` | https://api.amp.sourcefire.com/v1/events?limit=10&connector_guid=71841cfb-1892-46b5-b7d7-b18d068246b4&offset=10 |
  action_result.data.\*.metadata.links.self | string | `url` | https://api.amp.sourcefire.com/v1/events?limit=10&connector_guid=71841cfb-1892-46b5-b7d7-b18d068246b4 |
  action_result.data.\*.metadata.results.current_item_count | numeric | | 10 |
  action_result.data.\*.metadata.results.index | numeric | | 0 |
  action_result.data.\*.metadata.results.items_per_page | numeric | | 10 |
  action_result.data.\*.metadata.results.total | numeric | | 14595 |
  action_result.data.\*.version | string | | v1.2.0 |
  action_result.summary.file_found | boolean | | |
  action_result.message | string | | File found |
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
