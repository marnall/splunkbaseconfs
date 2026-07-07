# Cybereason

Publisher: Cybereason \
Connector Version: 2.4.2 \
Product Vendor: Cybereason \
Product Name: Cybereason \
Minimum Product Version: 5.3.5

This app integrates with the Cybereason platform to perform investigative, contain, and corrective actions on Malop and Malware events

### Configuration variables

This table lists the configuration variables required to operate Cybereason. These variables are specified when configuring a Cybereason asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | The URL of the Cybereason server to connect to. This should be of the form 'https://<server name or ip>:<port>' |
**verify_server_cert** | optional | boolean | If checked, will verify the SSL certificate of the Cybereason server |
**username** | required | string | A valid username for connecting to the Cybereason server |
**password** | required | password | A valid password for connecting to the Cybereason server |
**malop_historical_days** | required | numeric | The number of days for which we want to get Malops (This parameter will be used for the first-time poll only, and will be ignored in subsequent polls) |
**malware_historical_days** | required | numeric | The number of days for which we want to get Malware (This parameter will be used for the first-time poll only, and will be ignored in subsequent polls) |
**override_malop_severity_map** | optional | string | A JSON string that the user can add to override the default severity mapping for different malop types |
**malware_severity** | optional | string | The severity to apply for all malware events |
**enable_epp_poll** | optional | boolean | If checked, will poll for EPP/Detection Malops |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[on poll](#action-on-poll) - Callback action for the on_poll ingest functionality \
[delete registry key](#action-delete-registry-key) - Deletes the specified registry key for a given malop ID and machine name \
[get sensor status](#action-get-sensor-status) - Get the connectivity status for all machine sensors in a Malop \
[add malop comment](#action-add-malop-comment) - Add a comment to the provided Malop ID \
[update malop status](#action-update-malop-status) - Update status for the provided Malop ID such as Under Investigation, To review, etc \
[isolate machine](#action-isolate-machine) - Blocks all communication to and from the machine. Communication with the Cybereason platform is not affected \
[unisolate machine](#action-unisolate-machine) - Unblocks all communication to and from the machine \
[isolate specific machine](#action-isolate-specific-machine) - Blocks all communication to and from the machine identified by the given Name or IP. Communication with the Cybereason platform is not affected \
[unisolate specific machine](#action-unisolate-specific-machine) - Unblocks all communication to and from the machine identified by the given Name or IP. Communication with the Cybereason platform is not affected \
[kill process](#action-kill-process) - Kills the active process on the machine \
[get remediation status](#action-get-remediation-status) - Gets the remediation status for a previously executed remediation action like Kill Process \
[set reputation](#action-set-reputation) - Blacklists / Whitelists / Removes a file hash reputation so that future malop detections can quickly identify the hash \
[query processes](#action-query-processes) - Queries a given malop to retrieve all processes \
[query machine](#action-query-machine) - Queries a given machine name to retrieve all that machine's information \
[query machine ip](#action-query-machine-ip) - Queries a given machine IP to retrieve all that machine's information \
[query users](#action-query-users) - Queries a given user to retrieve all user-related details \
[query files](#action-query-files) - Queries a given filename to retrieve all file details \
[query domain](#action-query-domain) - Queries a given domain name to retrieve all details of that domain \
[query connections](#action-query-connections) - Queries a given name to retrieve all details of that connection \
[upgrade sensor](#action-upgrade-sensor) - Upgrade a sensor \
[restart sensor](#action-restart-sensor) - Restart a sensor

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

Test the connectivity with the Cybereason server configured by the user.

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Callback action for the on_poll ingest functionality

Type: **ingest** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_count** | optional | Maximum number of containers to ingest | numeric | |
**container_id** | optional | Parameter ignored in this app | string | |
**start_time** | optional | Parameter ignored in this app | numeric | |
**end_time** | optional | Parameter ignored in this app | numeric | |
**artifact_count** | optional | Parameter ignored in this app | numeric | |

#### Action Output

No Output

## action: 'delete registry key'

Deletes the specified registry key for a given malop ID and machine name

Type: **correct** \
Read only: **False**

A malop can contain processes that write to Windows registry keys. This action will fire a remediation action on the Cybereason console that will delete the registry key using the Cybereason sensor installed on the machine.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The ID of the malop for deleting the registry key | string | `cybereason malop id` |
**machine_name** | required | The name of the machine on which we want to delete the registry key | string | `cybereason machine name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.machine_name | string | `cybereason machine name` | |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.data.\*.initiating_user | string | `cybereason user` | |
action_result.data.\*.remediation_id | string | `cybereason remediation id` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get sensor status'

Get the connectivity status for all machine sensors in a Malop

Type: **investigate** \
Read only: **True**

Each machine covered by Cybereason will have a sensor installed on it. This action will extract the sensor status for all machines in a Malop.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The malop ID for which we will get sensor status information | string | `cybereason malop id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.data.\*.machine_id | string | `cybereason machine id` | |
action_result.data.\*.machine_name | string | `cybereason machine name` | |
action_result.data.\*.status | string | `cybereason sensor status` | Online Offline |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'add malop comment'

Add a comment to the provided Malop ID

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The malop ID for which we want to add a comment | string | `cybereason malop id` |
**comment** | optional | The comment that we want to add to the malop | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.comment | string | | |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'update malop status'

Update status for the provided Malop ID such as Under Investigation, To review, etc

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The malop ID for which we want to update the status | string | `cybereason malop id` |
**status** | required | The status that will be assigned to the malop | string | `cybereason malop status` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.parameter.status | string | `cybereason malop status` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'isolate machine'

Blocks all communication to and from the machine. Communication with the Cybereason platform is not affected

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The malop ID for which we want to isolate the machine | string | `cybereason malop id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unisolate machine'

Unblocks all communication to and from the machine

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The malop ID for which we want to unisolate the machine | string | `cybereason malop id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'isolate specific machine'

Blocks all communication to and from the machine identified by the given Name or IP. Communication with the Cybereason platform is not affected

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**machine_name_or_ip** | required | Name or IP of the machine that needs to be isolated | string | `cybereason machine name or ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.machine_name_or_ip | string | `cybereason machine name or ip` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'unisolate specific machine'

Unblocks all communication to and from the machine identified by the given Name or IP. Communication with the Cybereason platform is not affected

Type: **correct** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**machine_name_or_ip** | required | Name or IP of the machine that needs to be unisolated | string | `cybereason machine name or ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.machine_name_or_ip | string | `cybereason machine name or ip` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'kill process'

Kills the active process on the machine

Type: **contain** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The malop ID for which we want to kill the active process | string | `cybereason malop id` |
**remediation_user** | required | The user-id who is killing the process | string | `cybereason user` |
**machine_id** | required | Machine ID associated with that malop ID | string | `cybereason machine id` |
**process_id** | required | Cybereason Process ID of the process to kill | string | `cybereason process id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.machine_id | string | `cybereason machine id` | |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.parameter.process_id | string | `cybereason process id` | |
action_result.parameter.remediation_user | string | `cybereason user` | |
action_result.data.\*.remediation_id | string | `cybereason remediation id` | |
action_result.data.\*.remediation_status | string | `cybereason remediation status` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get remediation status'

Gets the remediation status for a previously executed remediation action like Kill Process

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The malop ID for which we want to get the remediation status | string | `cybereason malop id` |
**remediation_user** | required | The user ID that has requested the remediation action | string | `cybereason user` |
**remediation_id** | required | An ID that specifies a previously executed remediation action like Kill Process | string | `cybereason remediation id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.parameter.remediation_id | string | `cybereason remediation id` | |
action_result.parameter.remediation_user | string | `cybereason user` | |
action_result.data.\*.remediation_message | string | | |
action_result.data.\*.remediation_status | string | `cybereason remediation status` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'set reputation'

Blacklists / Whitelists / Removes a file hash reputation so that future malop detections can quickly identify the hash

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**reputation_item_hash** | required | The item (hash, IP) for which we want to set the reputation | string | `hash` |
**custom_reputation** | required | The custom reputation that we want to set for the reputation item | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.custom_reputation | string | | |
action_result.parameter.reputation_item_hash | string | `hash` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query processes'

Queries a given malop to retrieve all processes

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**malop_id** | required | The ID of the malop for which we want to get process details | string | `cybereason malop id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.malop_id | string | `cybereason malop id` | |
action_result.data.\*.owner_machine_id | string | `cybereason machine id` | |
action_result.data.\*.owner_machine_name | string | `cybereason machine name` | |
action_result.data.\*.process_id | string | `cybereason process id` | |
action_result.data.\*.process_name | string | `cybereason process name` | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query machine'

Queries a given machine name to retrieve all that machine's information

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | The name of the machine | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.name | string | | |
action_result.data.\*.is_connected_to_cybereason | string | | |
action_result.data.\*.machine_id | string | `cybereason machine id` | |
action_result.data.\*.machine_name | string | | |
action_result.data.\*.os_version | string | | |
action_result.data.\*.platform_architecture | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query machine ip'

Queries a given machine IP to retrieve all that machine's information

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**machine_ip** | required | The IP of a machine | string | `ip` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.machine_ip | string | `ip` | |
action_result.data.\*.is_connected_to_cybereason | string | | |
action_result.data.\*.machine_id | string | `cybereason machine id` | |
action_result.data.\*.machine_name | string | | |
action_result.data.\*.os_version | string | | |
action_result.data.\*.platform_architecture | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query users'

Queries a given user to retrieve all user-related details

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**user** | required | The name of the user | string | `cybereason user` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.user | string | `cybereason user` | |
action_result.data.\*.domain | string | `domain` | |
action_result.data.\*.element_name | string | | |
action_result.data.\*.last_machine_logged_into | string | | |
action_result.data.\*.local_system | string | | |
action_result.data.\*.organization | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query files'

Queries a given filename to retrieve all file details

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**file_name** | required | The name of the file | string | `file name` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.file_name | string | `file name` | |
action_result.data.\*.SHA1_signature | string | | |
action_result.data.\*.company_name | string | | |
action_result.data.\*.element_name | string | | |
action_result.data.\*.path | string | | |
action_result.data.\*.product_name | string | | |
action_result.data.\*.signed | string | | |
action_result.data.\*.size | string | | |
action_result.data.\*.suspicion_count | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query domain'

Queries a given domain name to retrieve all details of that domain

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain_name** | required | The name of the domain | string | `domain` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain_name | string | `domain` | |
action_result.data.\*.element_name | string | | |
action_result.data.\*.is_internal_domain | string | | |
action_result.data.\*.malicious_classification_type | string | | |
action_result.data.\*.was_ever_resolved | string | | |
action_result.data.\*.was_ever_resolved_as_second_level_domain | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'query connections'

Queries a given name to retrieve all details of that connection

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**connection_name** | required | The name of the connection | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.connection_name | string | | |
action_result.data.\*.direction | string | | |
action_result.data.\*.dns_query | string | | |
action_result.data.\*.element_name | string | | |
action_result.data.\*.owner_machine | string | | |
action_result.data.\*.owner_process | string | | |
action_result.data.\*.port_type | string | `port` | |
action_result.data.\*.received_bytes | string | | |
action_result.data.\*.remote_address | string | | |
action_result.data.\*.server_address | string | | |
action_result.data.\*.server_port | string | | |
action_result.data.\*.transmitted_bytes | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'upgrade sensor'

Upgrade a sensor

Type: **generic** \
Read only: **False**

Upgrade a sensor using the Cybereason sensor pylum ID provided as an input.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**pylumid** | required | The Cybereason sensor pylum ID targeted for upgrade (comma-separated IDs allowed) | string | `cybereason sensor pylum id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.pylumid | string | `cybereason sensor pylum id` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'restart sensor'

Restart a sensor

Type: **generic** \
Read only: **False**

Restart a sensor using the Cybereason sensor pylum ID provided as an input.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**pylumid** | required | The Cybereason sensor pylum ID targeted for restart (comma-separated IDs allowed) | string | `cybereason sensor pylum id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.pylumid | string | `cybereason sensor pylum id` | |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

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
