# SignalFx

Publisher: Splunk \
Connector Version: 1.2.3 \
Product Vendor: Splunk \
Product Name: SignalFx \
Minimum Product Version: 6.0.0

This App uses the Splunk Infrastructure Monitoring (SignalFx) API to retrieve and send data

### Configuration variables

This table lists the configuration variables required to operate SignalFx. These variables are specified when configuring a SignalFx asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Splunk Infrastructure Monitoring (SignalFx) URL |
**token** | required | password | Go to SignalFx My Profile -> Access Tokens |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[run query](#action-run-query) - Retrieves dimensions based on a query \
[create observability event](#action-create-observability-event) - POST an event to Splunk observability containing any selected fields from SOAR \
[clear incident](#action-clear-incident) - Clears a specified incident \
[get incident](#action-get-incident) - Get details of a specified incident \
[list incidents](#action-list-incidents) - List all incidents

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'run query'

Retrieves dimensions based on a query

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**query** | required | 'Dimension name' or 'name and value' to search for (e.g: aws_region:region_name) | string | `signalfx query` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.query | string | `signalfx query` | aws_region:region_name |
action_result.data.\*.count | numeric | | 33 |
action_result.data.\*.results.\*.created | numeric | | 1612448904607 |
action_result.data.\*.results.\*.creator | string | | EtJfNWZAEAE |
action_result.data.\*.results.\*.customProperties.aws_account_id | string | | 102730102752 |
action_result.data.\*.results.\*.customProperties.aws_architecture | string | | x86_64 |
action_result.data.\*.results.\*.customProperties.aws_arn | string | | arn:aws:ec2:us-west-2:102730102752:instance/i-0872664e6358a5483 |
action_result.data.\*.results.\*.customProperties.aws_attachment_state | string | | attached |
action_result.data.\*.results.\*.customProperties.aws_availability_zone | string | | us-west-2a |
action_result.data.\*.results.\*.customProperties.aws_cluster_name | string | | myFirstEKS |
action_result.data.\*.results.\*.customProperties.aws_cluster_status | string | | ACTIVE |
action_result.data.\*.results.\*.customProperties.aws_create_time | string | | Thu Feb 11 08:35:13 UTC 2021 |
action_result.data.\*.results.\*.customProperties.aws_created_timestamp | string | | 1605092933 |
action_result.data.\*.results.\*.customProperties.aws_delete_on_termination | string | | true |
action_result.data.\*.results.\*.customProperties.aws_encrypted | string | | false |
action_result.data.\*.results.\*.customProperties.aws_fifo_queue | string | | false |
action_result.data.\*.results.\*.customProperties.aws_hypervisor | string | | xen |
action_result.data.\*.results.\*.customProperties.aws_image_id | string | | ami-0bc06212a56393ee1 |
action_result.data.\*.results.\*.customProperties.aws_instance_id | string | | i-0872664e6358a5483 |
action_result.data.\*.results.\*.customProperties.aws_instance_type | string | | t3.xlarge |
action_result.data.\*.results.\*.customProperties.aws_iops | string | | 100 |
action_result.data.\*.results.\*.customProperties.aws_launch_time | string | | Fri Mar 05 08:36:59 UTC 2021 |
action_result.data.\*.results.\*.customProperties.aws_maximum_message_size | string | | 262144 |
action_result.data.\*.results.\*.customProperties.aws_private_dns_name | string | | ip-10-0-1-5.us-west-2.compute.internal |
action_result.data.\*.results.\*.customProperties.aws_public_dns_name | string | | ec2-52-27-24-63.us-west-2.compute.test.com |
action_result.data.\*.results.\*.customProperties.aws_public_ip_address | string | | 52.27.24.63 |
action_result.data.\*.results.\*.customProperties.aws_queue_arn | string | | arn:aws:sqs:us-west-2:102730102752:cloud-attackrange-trail-SQS-Deadletter |
action_result.data.\*.results.\*.customProperties.aws_queue_url | string | | https://sqs.us-west-2.test.com/102730102752/cloud-attackrange-trail-SQS-Deadletter |
action_result.data.\*.results.\*.customProperties.aws_region | string | | us-west-2 |
action_result.data.\*.results.\*.customProperties.aws_reservation_id | string | | r-05d593207e739e6cb |
action_result.data.\*.results.\*.customProperties.aws_root_device_type | string | | ebs |
action_result.data.\*.results.\*.customProperties.aws_service_name | string | | service1 |
action_result.data.\*.results.\*.customProperties.aws_size | string | | 8 |
action_result.data.\*.results.\*.customProperties.aws_snapshot_id | string | | snap-0fddcbbd358fbd48c |
action_result.data.\*.results.\*.customProperties.aws_state | string | | {Code: 80,Name: stopped} |
action_result.data.\*.results.\*.customProperties.aws_state_reason | string | | {Code: Client.UserInitiatedShutdown,Message: Client.UserInitiatedShutdown: User initiated shutdown} |
action_result.data.\*.results.\*.customProperties.aws_tag_Name | string | | Tag Name |
action_result.data.\*.results.\*.customProperties.aws_visibility_timeout | string | | 30 |
action_result.data.\*.results.\*.customProperties.aws_volume_id | string | | vol-0a327b9f8122ee07e |
action_result.data.\*.results.\*.customProperties.aws_volume_type | string | | gp2 |
action_result.data.\*.results.\*.description | string | | |
action_result.data.\*.results.\*.key | string | | AWSUniqueId |
action_result.data.\*.results.\*.lastUpdated | numeric | | 1614953320349 |
action_result.data.\*.results.\*.lastUpdatedBy | string | | AAAAAAAAAAA |
action_result.data.\*.results.\*.value | string | | i-0872664e6358a5483_us-west-2_102730102752 |
action_result.summary.total_results | numeric | | 1 |
action_result.message | string | | Total results: 1 |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'create observability event'

POST an event to Splunk observability containing any selected fields from SOAR

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**title** | required | Title of your Splunk Observability Event | string | |
**dimensions** | optional | A set of key-value pairs defining event definitions | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.dimensions | string | | {"description": "test description", "tag": "test"} |
action_result.parameter.title | string | | test |
action_result.data | string | | |
action_result.summary | string | | |
action_result.message | string | | Observability event sent |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'clear incident'

Clears a specified incident

Type: **generic** \
Read only: **False**

This action clears (resolves) a specific incident that is identified by the parameter incidentid.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incidentid** | required | The ID of the incident to be cleared | string | `signalfx incidentid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incidentid | string | `signalfx incidentid` | Et6d4doAIAg |
action_result.data.\*.code | numeric | | 200 |
action_result.data.\*.message | string | | Already resolved |
action_result.summary | string | | |
action_result.message | string | | Resolved Incident successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'get incident'

Get details of a specified incident

Type: **investigate** \
Read only: **True**

This action pulls details of a specific incident that is identified by the parameter incidentid.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**incidentid** | required | The ID of the incident to get details about | string | `signalfx incidentid` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.incidentid | string | `signalfx incidentid` | Et6d4doAIAg |
action_result.data.\*.active | boolean | | True False |
action_result.data.\*.anomalyState | string | | MANUALLY_RESOLVED |
action_result.data.\*.detectLabel | string | | instance_state_change |
action_result.data.\*.detectorId | string | | EtNvxe4AEAA |
action_result.data.\*.detectorName | string | | instance_changed |
action_result.data.\*.displayBody | string | | us-west-2a t3.xlarge 102730102752 us-west-2 743229228294 instance.state_change Linux aws started t3 Shared EC2.Instances |
action_result.data.\*.duration | numeric | | 2169890345 |
action_result.data.\*.events.\*.anomalyState | string | | MANUALLY_RESOLVED |
action_result.data.\*.events.\*.detectLabel | string | | instance_state_change |
action_result.data.\*.events.\*.detectorId | string | | EtNvxe4AEAA |
action_result.data.\*.events.\*.detectorName | string | | instance_changed |
action_result.data.\*.events.\*.id | string | | Ev9ClaiAEAA |
action_result.data.\*.events.\*.incidentId | string | `signalfx incidentid` | Et6d4doAIAg |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_account_id | string | | 102730102752 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_availability_zone | string | | us-west-2a |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_instance_family | string | | t3 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_instance_type | string | | t3.xlarge |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_master_account_id | string | | 743229228294 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_platform | string | | Linux |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_region | string | | us-west-2 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_tenancy | string | | Shared |
action_result.data.\*.events.\*.inputs.\_S1.key.azure.resourcegroup.name | string | | PLUGINFRAMEWORK |
action_result.data.\*.events.\*.inputs.\_S1.key.azure.vm.size | string | | Standard_B2s |
action_result.data.\*.events.\*.inputs.\_S1.key.azure_resource_id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa/pluginframework/test.compute/virtualmachines/test |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.account.id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.platform | string | | azure_vm |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.provider | string | | azure |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.region | string | | eastus |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud_provider | string | | aws |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud_provider_service | string | | EC2.Instances |
action_result.data.\*.events.\*.inputs.\_S1.key.host.id | string | | e3d18363-xxxx-4d19-9b75-9ec2f5953aaa |
action_result.data.\*.events.\*.inputs.\_S1.key.host.name | string | | test |
action_result.data.\*.events.\*.inputs.\_S1.key.os.type | string | | windows |
action_result.data.\*.events.\*.inputs.\_S1.key.sf_metric | string | | instance.state_change |
action_result.data.\*.events.\*.inputs.\_S1.key.state | string | | started |
action_result.data.\*.events.\*.inputs.\_S1.value | string | | 0.0 |
action_result.data.\*.events.\*.inputs.\_S2.value | string | | 0 |
action_result.data.\*.events.\*.inputs.\_S3.key.azure.resourcegroup.name | string | | PLUGINFRAMEWORK |
action_result.data.\*.events.\*.inputs.\_S3.key.azure.vm.size | string | | Standard_B2s |
action_result.data.\*.events.\*.inputs.\_S3.key.azure_resource_id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa/pluginframework/test.compute/virtualmachines/test |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.account.id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.platform | string | | azure_vm |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.provider | string | | azure |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.region | string | | eastus |
action_result.data.\*.events.\*.inputs.\_S3.key.device | string | | C: |
action_result.data.\*.events.\*.inputs.\_S3.key.direction | string | | read |
action_result.data.\*.events.\*.inputs.\_S3.key.host.id | string | | e3d18363-806f-4d19-9b75-9ec2f5953cd4 |
action_result.data.\*.events.\*.inputs.\_S3.key.host.name | string | | test |
action_result.data.\*.events.\*.inputs.\_S3.key.os.type | string | | windows |
action_result.data.\*.events.\*.inputs.\_S3.key.sf_metric | string | | system.disk.operations |
action_result.data.\*.events.\*.inputs.\_S3.value | string | | 1 |
action_result.data.\*.events.\*.inputs.\_S7.value | string | | 5 |
action_result.data.\*.events.\*.linkedTeams | string | | |
action_result.data.\*.events.\*.severity | string | | Critical |
action_result.data.\*.events.\*.timestamp | numeric | | 1615203470345 |
action_result.data.\*.incidentId | string | `signalfx incidentid` | Et6d4doAIAg |
action_result.data.\*.isMuted | boolean | | True False |
action_result.data.\*.severity | string | | Critical |
action_result.data.\*.triggeredNotificationSent | boolean | | True False |
action_result.data.\*.triggeredWhileMuted | boolean | | True False |
action_result.summary | string | | |
action_result.message | string | | Incident details fetched successfully |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |

## action: 'list incidents'

List all incidents

Type: **investigate** \
Read only: **True**

This action can return incidents up to index 10000. If limit parameter is not provided then 100 will be taken as default value.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**include_resolved** | optional | Whether to fetch resolved incidents | boolean | |
**limit** | optional | Number of results to be returned | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.include_resolved | boolean | | True False |
action_result.parameter.limit | numeric | | |
action_result.data.\*.active | boolean | | True False |
action_result.data.\*.anomalyState | string | | MANUALLY_RESOLVED |
action_result.data.\*.detectLabel | string | | instance_state_change |
action_result.data.\*.detectorId | string | | EtNvxe4AEAA |
action_result.data.\*.detectorName | string | | instance_changed |
action_result.data.\*.displayBody | string | | us-west-2a t3.xlarge 102730102752 us-west-2 743229228294 instance.state_change Linux aws started t3 Shared EC2.Instances |
action_result.data.\*.duration | numeric | | 2169890345 |
action_result.data.\*.events.\*.anomalyState | string | | MANUALLY_RESOLVED |
action_result.data.\*.events.\*.detectLabel | string | | instance_state_change |
action_result.data.\*.events.\*.detectorId | string | | EtNvxe4AEAA |
action_result.data.\*.events.\*.detectorName | string | | instance_changed |
action_result.data.\*.events.\*.id | string | | Ev9ClaiAEAA |
action_result.data.\*.events.\*.incidentId | string | `signalfx incidentid` | Et6d4doAIAg |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_account_id | string | | 102730102752 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_availability_zone | string | | us-west-2a |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_instance_family | string | | t3 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_instance_type | string | | t3.xlarge |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_master_account_id | string | | 743229228294 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_platform | string | | Linux |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_region | string | | us-west-2 |
action_result.data.\*.events.\*.inputs.\_S1.key.aws_tenancy | string | | Shared |
action_result.data.\*.events.\*.inputs.\_S1.key.azure.resourcegroup.name | string | | PLUGINFRAMEWORK |
action_result.data.\*.events.\*.inputs.\_S1.key.azure.vm.size | string | | Standard_B2s |
action_result.data.\*.events.\*.inputs.\_S1.key.azure_resource_id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa/pluginframework/test.compute/virtualmachines/test |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.account.id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.platform | string | | azure_vm |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.provider | string | | azure |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud.region | string | | eastus |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud_provider | string | | aws |
action_result.data.\*.events.\*.inputs.\_S1.key.cloud_provider_service | string | | EC2.Instances |
action_result.data.\*.events.\*.inputs.\_S1.key.device | string | | C: |
action_result.data.\*.events.\*.inputs.\_S1.key.direction | string | | receive |
action_result.data.\*.events.\*.inputs.\_S1.key.host.id | string | | e3d18363-xxxx-4d19-9b75-9ec2f5953aaa |
action_result.data.\*.events.\*.inputs.\_S1.key.host.name | string | | test |
action_result.data.\*.events.\*.inputs.\_S1.key.mode | string | | rw |
action_result.data.\*.events.\*.inputs.\_S1.key.mountpoint | string | | C: |
action_result.data.\*.events.\*.inputs.\_S1.key.os.type | string | | windows |
action_result.data.\*.events.\*.inputs.\_S1.key.sf_metric | string | | instance.state_change |
action_result.data.\*.events.\*.inputs.\_S1.key.state | string | | started |
action_result.data.\*.events.\*.inputs.\_S1.key.type | string | | NTFS |
action_result.data.\*.events.\*.inputs.\_S1.value | string | | 0.0 |
action_result.data.\*.events.\*.inputs.\_S2.value | string | | 0 |
action_result.data.\*.events.\*.inputs.\_S3.key.azure.resourcegroup.name | string | | PLUGINFRAMEWORK |
action_result.data.\*.events.\*.inputs.\_S3.key.azure.vm.size | string | | Standard_B2s |
action_result.data.\*.events.\*.inputs.\_S3.key.azure_resource_id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa/pluginframework/test.compute/virtualmachines/test |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.account.id | string | | 4c357906-xxxx-aaaa-98aa-180d9a85aaaa |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.platform | string | | azure_vm |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.provider | string | | azure |
action_result.data.\*.events.\*.inputs.\_S3.key.cloud.region | string | | eastus |
action_result.data.\*.events.\*.inputs.\_S3.key.device | string | | Ethernet |
action_result.data.\*.events.\*.inputs.\_S3.key.direction | string | | transmit |
action_result.data.\*.events.\*.inputs.\_S3.key.host.id | string | | e3d18363-xxxx-4d19-9b75-9ec2f5953aaa |
action_result.data.\*.events.\*.inputs.\_S3.key.host.name | string | | test |
action_result.data.\*.events.\*.inputs.\_S3.key.os.type | string | | windows |
action_result.data.\*.events.\*.inputs.\_S3.key.sf_metric | string | | system.network.io |
action_result.data.\*.events.\*.inputs.\_S3.key.state | string | | free |
action_result.data.\*.events.\*.inputs.\_S3.value | string | | 1 |
action_result.data.\*.events.\*.inputs.\_S4.value | string | | 0 |
action_result.data.\*.events.\*.inputs.\_S5.value | string | | 50 |
action_result.data.\*.events.\*.inputs.\_S6.value | string | | 0 |
action_result.data.\*.events.\*.inputs.\_S7.value | string | | 5 |
action_result.data.\*.events.\*.linkedTeams | string | | |
action_result.data.\*.events.\*.severity | string | | Critical |
action_result.data.\*.events.\*.timestamp | numeric | | 1615203470345 |
action_result.data.\*.incidentId | string | `signalfx incidentid` | Et6d4doAIAg |
action_result.data.\*.isMuted | boolean | | True False |
action_result.data.\*.severity | string | | Critical |
action_result.data.\*.triggeredNotificationSent | boolean | | True False |
action_result.data.\*.triggeredWhileMuted | boolean | | True False |
action_result.summary.total_incidents | numeric | | 1 |
action_result.message | string | | Total incidents: 1 |
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
