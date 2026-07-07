# FortiNDRCloud

Publisher: Fortinet Inc. \
Connector Version: 1.1.1 \
Product Vendor: Fortinet Inc. \
Product Name: FortiNDR Cloud \
Minimum Product Version: 6.2.1

This app allows the use of the information provided by the FortiNDR Cloud Service to perform containment and investigative actions on Splunk SOAR

### Configuration variables

This table lists the configuration variables required to operate FortiNDRCloud. These variables are specified when configuring a FortiNDR Cloud asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**api_key** | required | password | API Token to connect to FortiNDR Cloud RESTful APIs |
**domain** | optional | string | Domain to where direct any API request. |
**first_poll** | optional | string | First Poll (<number> <time unit>, e.g., 12 hours, 7 days) |
**muted** | optional | boolean | Set to true to include muted detections. Default to false |
**polling_delay** | optional | numeric | Polling delay in minute. This is required to allow time for the detections to be added before polling them |
**muted_rule** | optional | boolean | Set to true to include muted rules. Default to false |
**account_uuid** | optional | string | Account UUID to filter retrieved detections |
**muted_device** | optional | boolean | Set to true to include muted devices. Default to false |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration \
[on poll](#action-on-poll) - Retrieve latest Detections from the FortiNDR Cloud Service \
[get sensors](#action-get-sensors) - Get a list of all sensors \
[get devices](#action-get-devices) - Get a list of all devices \
[get tasks](#action-get-tasks) - Get a list of all the PCAP tasks \
[create task](#action-create-task) - Create a new PCAP task \
[get telemetry events](#action-get-telemetry-events) - Get event telemetry data grouped by time \
[get telemetry packetstats](#action-get-telemetry-packetstats) - Get packetstats telemetry data grouped by time \
[get telemetry network](#action-get-telemetry-network) - Get network telemetry data grouped by time \
[get entity summary](#action-get-entity-summary) - Get summary information about an IP or domain \
[get entity pdns](#action-get-entity-pdns) - Get passive DNS information about an IP or domain \
[get entity dhcp](#action-get-entity-dhcp) - Get DHCP information about an IP address \
[get entity file](#action-get-entity-file) - Get information about a file \
[get detections](#action-get-detections) - Get information about the detections \
[get detection rules](#action-get-detection-rules) - Get a list of detection rules \
[resolve detection](#action-resolve-detection) - Resolve a specific detection \
[get rule events](#action-get-rule-events) - Get a list of the events that matched on a specific rule \
[get detection events](#action-get-detection-events) - Get a list of the events associated with a specific detection \
[create detection rule](#action-create-detection-rule) - Create a new detection rule

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** \
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'on poll'

Retrieve latest Detections from the FortiNDR Cloud Service

Type: **ingest** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_time** | optional | First Poll (<number> <time unit>, e.g., 12 hours, 7 days) | string | |
**end_time** | optional | Parameter Ignored in this app | numeric | |
**container_id** | optional | Parameter Ignored in this app | numeric | |
**container_count** | optional | Parameter Ignored in this app | numeric | |
**artifact_count** | optional | Parameter Ignored in this app | numeric | |

#### Action Output

No Output

## action: 'get sensors'

Get a list of all sensors

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account_uuid** | optional | UUID of account to filter by | string | |
**account_code** | optional | Account code to filter by | string | |
**sensor_id** | optional | ID of the sensor to filter by | string | |
**include** | optional | Include additional metadata such as status, interfaces, admin.sensor, admin.zeek, admin.suricata, and network_usage | string | |
**enabled** | optional | Filter by true or false. If not provided, all the sensors are returned | boolean | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Sensors retrieved successfully. |
action_result.parameter.account_uuid | string | | |
action_result.parameter.account_code | string | | |
action_result.parameter.sensor_id | string | | |
action_result.parameter.include | string | | |
action_result.parameter.enabled | string | | |
action_result.data.\*.sensors.\*.sensor_id | string | | sen1 |
action_result.data.\*.sensors.\*.account_code | string | | gig |
action_result.data.\*.sensors.\*.created | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.sensors.\*.updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.sensors.\*.location | string | | { "latitude": 0, "longitude": 0 } |
action_result.data.\*.sensors.\*.subdivison | string | | USA |
action_result.data.\*.sensors.\*.city | string | | San Jose |
action_result.data.\*.sensors.\*.country | string | | USA |
action_result.data.\*.sensors.\*.tags | string | | Demo Sensor |
action_result.data.\*.sensors.\*.pcap_enabled | boolean | | True False |
action_result.data.\*.sensors.\*.serial_number | string | | |
action_result.data.\*.sensors.\*.status | string | | |
action_result.data.\*.sensors.\*.interfaces | string | | |
action_result.data.\*.sensors.\*.admin | string | | |

## action: 'get devices'

Get a list of all devices

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**start_date** | optional | Filter devices based on when they were seen | string | |
**end_date** | optional | Filter devices based on when they were seen | string | |
**cidr** | optional | Filter devices that are under a specific CIDR | string | |
**sensor_id** | optional | Filter devices that were observed by a specific sensor | string | |
**traffic_direction** | optional | Filter devices that have been noted to only have a certain directionality of traffic ("external" vs "internal") | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Devices retrieved successfully. |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.parameter.cidr | string | | |
action_result.parameter.sensor_id | string | | |
action_result.parameter.traffic_direction | string | | |
action_result.data.\*.devices.\*.ip_address | string | | 8.8.8.8 |
action_result.data.\*.devices.\*.date | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.devices.\*.external | boolean | | True False |
action_result.data.\*.devices.\*.internal | boolean | | True False |

## action: 'get tasks'

Get a list of all the PCAP tasks

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**task_uuid** | optional | Filter to a specific task | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Tasks retrieved successfully. |
action_result.parameter.task_uuid | string | | |
action_result.data.\*.tasks.\*.task_uuid | string | | 32329e78-c51f-4da4-bd56-6bfb35d84a9c |
action_result.data.\*.tasks.\*.name | string | | Meh-Ike phone 10001 |
action_result.data.\*.tasks.\*.description | string | | |
action_result.data.\*.tasks.\*.status | string | | inactive |
action_result.data.\*.tasks.\*.account_code | string | | gig |
action_result.data.\*.tasks.\*.sensor_ids | string | | ["sen1"] |
action_result.data.\*.tasks.\*.bpf | string | | src host x.x.x.x and dst port 10001 |
action_result.data.\*.tasks.\*.created | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.tasks.\*.created_uuid | string | | 32329e78-c51f-4da4-bd56-6bfb35d84a9c |
action_result.data.\*.tasks.\*.created_email | string | | test@test.com |
action_result.data.\*.tasks.\*.updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.tasks.\*.updated_uuid | string | | 32329e78-c51f-4da4-bd56-6bfb35d84a9c |
action_result.data.\*.tasks.\*.updated_email | string | | test@test.com |
action_result.data.\*.tasks.\*.requested_start_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.tasks.\*.actual_start_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.tasks.\*.requested_end_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.tasks.\*.actual_end_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.tasks.\*.has_files | boolean | | True False |
action_result.data.\*.tasks.\*.files | string | | |

## action: 'create task'

Create a new PCAP task

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**name** | required | The name of the task | string | |
**account_uuid** | required | Account where the task will be created | string | |
**description** | required | A description for the task | string | |
**bpf** | required | The Berkeley Packet Filter for capture filtering | string | |
**requested_start_date** | required | The date the task will become active. (2019-01-30T00:00:00.000Z) | string | |
**requested_end_date** | required | The date the task will become inactive. (2019-12-31T23:59:59.000Z) | string | |
**sensor_ids** | optional | List of sensor IDs, separated by ',', on which this task will run (separate multiple accounts by comma) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Detection Rule created successfully |
action_result.parameter.name | string | | |
action_result.parameter.account_uuid | string | | |
action_result.parameter.description | string | | |
action_result.parameter.bpf | string | | |
action_result.parameter.requested_start_date | string | | |
action_result.parameter.requested_end_date | string | | |
action_result.parameter.sensor_ids | string | | |
action_result.data.\*.task.task_uuid | string | | 32329e78-c51f-4da4-bd56-6bfb35d84a9c |
action_result.data.\*.task.name | string | | Meh-Ike phone 10001 |
action_result.data.\*.task.description | string | | |
action_result.data.\*.task.status | string | | inactive |
action_result.data.\*.task.account_code | string | | gig |
action_result.data.\*.task.sensor_ids | string | | ["sen1"] |
action_result.data.\*.task.bpf | string | | src host x.x.x.x and dst port 10001 |
action_result.data.\*.task.created | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.task.created_uuid | string | | 32329e78-c51f-4da4-bd56-6bfb35d84a9c |
action_result.data.\*.task.created_email | string | | test@test.com |
action_result.data.\*.task.updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.task.updated_uuid | string | | 32329e78-c51f-4da4-bd56-6bfb35d84a9c |
action_result.data.\*.task.updated_email | string | | test@test.com |
action_result.data.\*.task.requested_start_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.task.actual_start_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.task.requested_end_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.task.actual_end_time | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.task.has_files | boolean | | True False |
action_result.data.\*.task.files | string | | |

## action: 'get telemetry events'

Get event telemetry data grouped by time

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**interval** | optional | Interval to group by: hour (default) or day | string | |
**start_date** | optional | Start date/time to query for. The default is 1 day ago for interval=hour or 30 days ago for interval=day | string | |
**end_date** | optional | End date/time to query for. The default is the current time | string | |
**account_uuid** | optional | Account uuid to filter by | string | |
**account_code** | optional | Account code to filter by | string | |
**sensor_id** | optional | Sensor id to filter by | string | |
**event_type** | optional | The type of event | string | |
**group_by** | optional | Optionally group results by: sensor_id, event_type | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Telemetry events retrieved successfully. |
action_result.parameter.interval | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.parameter.account_uuid | string | | |
action_result.parameter.account_code | string | | |
action_result.parameter.sensor_id | string | | |
action_result.parameter.event_type | string | | |
action_result.parameter.group_by | string | | |
action_result.data.\*.telemetry_events.\*.timestamp | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.telemetry_events.\*.event_count | numeric | | 1000 |
action_result.data.\*.telemetry_events.\*.sensor_id | string | | sen1 |
action_result.data.\*.telemetry_events.\*.event_type | string | | flow |
action_result.data.\*.telemetry_events.\*.account_code | string | | act |

## action: 'get telemetry packetstats'

Get packetstats telemetry data grouped by time

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**interval** | optional | Aggregation interval. default by hour if not specified | string | |
**start_date** | optional | Scopes the returned metrics to dates after the given start_date. If empty returns most current packet stats | string | |
**end_date** | optional | Scopes the returned metrics to dates before the given end_date. If empty returns most current packet stats | string | |
**account_code** | optional | Account code to filter by | string | |
**sensor_id** | optional | Scopes the returned metrics to the interfaces of the specified sensor ID | string | |
**group_by** | optional | Option to group by the following fields: interface_name, sensor_id, account_code | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Telemetry packet stats retrieved successfully. |
action_result.parameter.interval | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.parameter.account_code | string | | |
action_result.parameter.sensor_id | string | | |
action_result.parameter.group_by | string | | |
action_result.data.\*.packetstats.\*.timestamp | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.packetstats.\*.account_code | string | | gig |
action_result.data.\*.packetstats.\*.sensor_id | string | | sen1 |
action_result.data.\*.packetstats.\*.interface_name | string | | |
action_result.data.\*.packetstats.\*.tx_bytes | numeric | | 1380372603073006 |
action_result.data.\*.packetstats.\*.tx_errors | numeric | | 0 |
action_result.data.\*.packetstats.\*.tx_packets | numeric | | 963173536282 |
action_result.data.\*.packetstats.\*.rx_bytes | numeric | | 1044065401242303200 |
action_result.data.\*.packetstats.\*.rx_errors | numeric | | 543523121859 |
action_result.data.\*.packetstats.\*.rx_packets | numeric | | 1511658249026538 |
action_result.data.\*.packetstats.\*.rx_bits_per_second | numeric | | 168359035095 |

## action: 'get telemetry network'

Get network telemetry data grouped by time

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account_code** | optional | Account code to filter by | string | |
**interval** | optional | The interval to filter by (day, month_to_day) | string | |
**latest_each_month** | optional | Filters out all but the latest day and month_to_date for each month | boolean | |
**sort_order** | optional | Sorts by account code first, then timestamp. asc or desc. The default is desc | string | |
**limit** | optional | The maximum number of records to return, default: 100, max: 1000 | numeric | |
**offset** | optional | The number of records to skip past. Default: 0 | numeric | |
**start_date** | optional | Start date to filter by | string | |
**end_date** | optional | End date to filter by | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Telemetry network retrieved successfully |
action_result.parameter.account_code | string | | |
action_result.parameter.interval | string | | |
action_result.parameter.latest_each_month | string | | |
action_result.parameter.sort_order | string | | |
action_result.parameter.limit | string | | |
action_result.parameter.offset | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.data.\*.network_usage.\*.timestamp | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.network_usage.\*.account_code | string | | gig |
action_result.data.\*.network_usage.\*.interval | string | | day |
action_result.data.\*.network_usage.\*.percentile | numeric | | 95 |
action_result.data.\*.network_usage.\*.percentile_bps | numeric | | 6050493542 |

## action: 'get entity summary'

Get summary information about an IP or domain

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | Entity name to retrieve summary information for | string | |
**entity_type** | optional | Type of the entity we are searching. Allowed values are: ip, domain or file | string | |
**account_uuid** | optional | Account uuid to filter by. If absent, all the caller's allowed accounts will be queried | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Entity summary retrieved successfully |
action_result.parameter.entity | string | | |
action_result.parameter.entity_type | string | | |
action_result.parameter.account_uuid | string | | |
action_result.data.\*.entity_summary.entity | string | | 8.8.8.8 |
action_result.data.\*.entity_summary.first_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_summary.last_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_summary.prevalence_count_internal | numeric | | 8 |
action_result.data.\*.entity_summary.tags.\*.text | string | | external |
action_result.data.\*.entity_summary.tags.\*.account_code | string | | act |
action_result.data.\*.entity_summary.tags.\*.user_uuid | string | | dc9ab97f-9cdf-46af-8ca2-e71e8e8243c8 |
action_result.data.\*.entity_summary.tags.\*.create_date | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_summary.tags.\*.entity | string | | 8.8.8.8 |
action_result.data.\*.entity_summary.tags.\*.public | boolean | | |

## action: 'get entity pdns'

Get passive DNS information about an IP or domain

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | IP or Domain to get passive DNS data for | string | |
**record_type** | optional | Limit results to the specified DNS query type(s). Supported types are: A, AAAA, CNAME, MX, NS. Case insensitive | string | |
**source** | optional | Limit the results to the specified data source(s). Note that not all Sources populate all fields. Supported sources are: ICEBRG_DNS. Case insensitive | string | |
**resolve_external** | optional | When true, the service will query non-ICEBRG data sources. false by default | boolean | |
**start_date** | optional | The earliest date before which to exclude results. Day granularity, inclusive | string | |
**end_date** | optional | The latest date after which to exclude results. Day granularity, inclusive | string | |
**account_uuid** | optional | Limit results to the specified account UUID(s). Defaults to all accounts for which the user has permission | string | |
**limit** | optional | Maximum number of records to be returned. Default 1000 | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Entity pdns retrieved successfully |
action_result.parameter.entity | string | | |
action_result.parameter.record_type | string | | |
action_result.parameter.source | string | | |
action_result.parameter.resolve_external | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.parameter.account_uuid | string | | |
action_result.parameter.limit | string | | |
action_result.data.\*.entity_pdns.\*.source | string | | icebrg_dns |
action_result.data.\*.entity_pdns.\*.account_uuid | string | | dc9ab97f-9cdf-46af-8ca2-e71e8e8243c8 |
action_result.data.\*.entity_pdns.\*.sensor_id | string | | sen1 |
action_result.data.\*.entity_pdns.\*.customer_id | string | | cust |
action_result.data.\*.entity_pdns.\*.first_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_pdns.\*.last_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_pdns.\*.resolved | string | | 8.8.8.8 |
action_result.data.\*.entity_pdns.\*.record_type | string | | a |

## action: 'get entity dhcp'

Get DHCP information about an IP address

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**entity** | required | IP to get DHCP data for | string | |
**start_date** | optional | The earliest date before which to exclude results. Day granularity, inclusive | string | |
**end_date** | optional | The latest date after which to exclude results. Day granularity, inclusive | string | |
**account_uuid** | optional | Limit results to the specified account UUID(s). Defaults to all accounts for which the user has permission | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Entity dhcp retrieved successfully |
action_result.parameter.entity | string | | |
action_result.parameter.start_date | string | | |
action_result.parameter.end_date | string | | |
action_result.parameter.account_uuid | string | | |
action_result.data.\*.entity_dhcp.\*.customer_id | string | | gig |
action_result.data.\*.entity_dhcp.\*.sensor_id | string | | sen1 |
action_result.data.\*.entity_dhcp.\*.ip | string | | 8.8.8.8 |
action_result.data.\*.entity_dhcp.\*.hostnames | string | | Somebody-iPhone |
action_result.data.\*.entity_dhcp.\*.mac | string | | e3:84:2f:8e:50:e4 |
action_result.data.\*.entity_dhcp.\*.lease_start | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_dhcp.\*.lease_end | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_dhcp.\*.start_lease_as_long | numeric | | 1618939557975 |

## action: 'get entity file'

Get information about a file

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File hash. Can be an MD5, SHA1, or SHA256 hash of the file | string | `hash` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Entity file retrieved successfully. |
action_result.parameter.hash | string | `hash` | |
action_result.data.\*.entity_file.entity | string | | 75ce20257379b1d8bd88f7bfb01c6a6e3a32221212c623fbf10de61e8c379ff8 |
action_result.data.\*.entity_file.customer_id | string | | gig |
action_result.data.\*.entity_file.names | string | | ["TIAgentSetup.exe"] |
action_result.data.\*.entity_file.mime_type | string | | ["application/x-dosexec"] |
action_result.data.\*.entity_file.bytes | numeric | | 0 |
action_result.data.\*.entity_file.first_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_file.last_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.entity_file.sha1 | string | | 8965f4209f82bb13e15172bdf672912eebc2132d |
action_result.data.\*.entity_file.sha256 | string | | 75ce20257379b1d8bd88f7bfb01c6a6e3a32221212c623fbf10de61e8c379ff8 |
action_result.data.\*.entity_file.md5 | string | | 95fcad6ceaefd749aa23fc5476863bb4 |
action_result.data.\*.entity_file.pe | string | | |
action_result.data.\*.entity_file.prevalence_count_internal | numeric | | 0 |

## action: 'get detections'

Get information about the detections

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_uuid** | optional | Filter to a specific rule | string | |
**account_uuid** | optional | For those with access to multiple accounts, specify a single account to return results from | string | |
**status** | optional | Filter by detection status: active, resolved | string | |
**device_ip** | optional | Device IP to filter by | string | |
**sensor_id** | optional | Sensor ID to filter by | string | |
**muted** | optional | List detections that a user muted: true / false | boolean | |
**muted_device** | optional | List detections for muted devices: true / false | boolean | |
**muted_rule** | optional | List detections for muted rules | boolean | |
**include** | optional | Include additional information in the response (i.e. 'rules,indicators' add the rules and the indicators to the response) | string | |
**sort_by** | optional | Field to sort by (first_seen, last_seen, status, device_ip, indicator_count) | string | |
**sort_order** | optional | Sort direction ('asc' vs 'desc') | string | |
**offset** | optional | The number of records to skip past | numeric | |
**limit** | optional | The number of records to return, default: 100, max: 10000 | numeric | |
**created_start_date** | optional | Created start date to filter by (inclusive) | string | |
**created_end_date** | optional | Created end date to filter by (exclusive) | string | |
**created_or_shared_start_date** | optional | Created or shared start date to filter by (inclusive) | string | |
**created_or_shared_end_date** | optional | Created or shared end date to filter by (exclusive) | string | |
**active_start_date** | optional | Active start date to filter by (inclusive) | string | |
**active_end_date** | optional | Active end date to filter by (exclusive) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Detections retrieved successfully. |
action_result.parameter.rule_uuid | string | | |
action_result.parameter.account_uuid | string | | |
action_result.parameter.status | string | | |
action_result.parameter.device_ip | string | | |
action_result.parameter.sensor_id | string | | |
action_result.parameter.muted | string | | |
action_result.parameter.muted_device | string | | |
action_result.parameter.muted_rule | string | | |
action_result.parameter.include | string | | |
action_result.parameter.sort_by | string | | |
action_result.parameter.sort_order | string | | |
action_result.parameter.offset | string | | |
action_result.parameter.limit | string | | |
action_result.parameter.created_start_date | string | | |
action_result.parameter.created_end_date | string | | |
action_result.parameter.created_or_shared_start_date | string | | |
action_result.parameter.created_or_shared_end_date | string | | |
action_result.parameter.active_start_date | string | | |
action_result.parameter.active_end_date | string | | |
action_result.data.\*.detections.\*.uuid | string | | cf576032-2f42-4b3e-90be-3c51e5128b03 |
action_result.data.\*.detections.\*.rule_uuid | string | | 58c2e22d-8b64-43ac-89a2-6c82ce66935e |
action_result.data.\*.detections.\*.device_ip | string | | 10.70.43.58 |
action_result.data.\*.detections.\*.sensor_id | string | | sen1 |
action_result.data.\*.detections.\*.account_uuid | string | | 1e5dbd92-9dca-4f36-bec5-c292172cbeaa |
action_result.data.\*.detections.\*.status | string | | active resolved |
action_result.data.\*.detections.\*.created | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.detections.\*.updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.detections.\*.resolution | string | | auto_resolved |
action_result.data.\*.detections.\*.resolution_timestamp | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.detections.\*.resolution_user_uuid | string | | b92cd6e0-dd24-4bee-838a-d0dfbeda621a |
action_result.data.\*.detections.\*.resolution_comment | string | | |
action_result.data.\*.detections.\*.first_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.detections.\*.last_seen | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.detections.\*.muted | boolean | | True False |
action_result.data.\*.detections.\*.muted_rule | boolean | | True False |
action_result.data.\*.detections.\*.muted_device_uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.detections.\*.muted_user_uuid | string | | d025f073-c01e-4ee9-a89b-72f972a75a16 |
action_result.data.\*.detections.\*.muted_comment | string | | |

## action: 'get detection rules'

Get a list of detection rules

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account_uuid** | optional | For those with access to multiple accounts, specify a single account to return results from | string | |
**search** | optional | Filter name or category | string | |
**has_detections** | optional | Include rules that have unmuted, unresolved detections | boolean | |
**severity** | optional | Filter by severity: high, moderate, low | string | |
**confidence** | optional | Filter by confidence: high, moderate, low | string | |
**category** | optional | Category to filter by | string | |
**rule_account_muted** | optional | Include muted rules: true / false | boolean | |
**enabled** | optional | Enabled rules only | boolean | |
**sort_by** | optional | The field to sort by: created, updated, detections, severity, confidence, category, last_seen, detections_muted. Defaults to updated | string | |
**sort_order** | optional | Sort direction ('asc' vs 'desc') | string | |
**offset** | optional | The number of records to skip past | numeric | |
**limit** | optional | The number of records to return, default: 100, max: 1000 | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Detection Rules retrieved successfully. |
action_result.parameter.account_uuid | string | | |
action_result.parameter.search | string | | |
action_result.parameter.has_detections | string | | |
action_result.parameter.severity | string | | |
action_result.parameter.confidence | string | | |
action_result.parameter.category | string | | |
action_result.parameter.rule_account_muted | string | | |
action_result.parameter.enabled | string | | |
action_result.parameter.sort_by | string | | |
action_result.parameter.sort_order | string | | |
action_result.parameter.offset | string | | |
action_result.parameter.limit | string | | |
action_result.data.\*.rules.\*.uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rules.\*.account_uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rules.\*.name | string | | AR T1595 |
action_result.data.\*.rules.\*.category | string | | Attack:Infection Vector |
action_result.data.\*.rules.\*.description | string | | |
action_result.data.\*.rules.\*.severity | string | | high moderate low |
action_result.data.\*.rules.\*.confidence | string | | high moderate low |
action_result.data.\*.rules.\*.auto_resolution_minutes | numeric | | 10080 |
action_result.data.\*.rules.\*.enabled | boolean | | True False |
action_result.data.\*.rules.\*.query_signature | string | | ip IN ('1.1.1.1','2.2.2.2') AND event_type = 'dns' |
action_result.data.\*.rules.\*.created | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.rules.\*.created_user_uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rules.\*.updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.rules.\*.updated_user_uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rules.\*.shared_account_uuids | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rules.\*.run_account_uuids | string | | ["55f39b72-2622-4137-9051-bc2ff364f059"] |
action_result.data.\*.rules.\*.rule_accounts | string | | |
action_result.data.\*.rules.\*.critical_updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.rules.\*.primary_attack_id | string | | |
action_result.data.\*.rules.\*.secondary_attack_id | string | | |
action_result.data.\*.rules.\*.specificity | string | | |
action_result.data.\*.rules.\*.device_ip_fields | string | | DEFAULT |
action_result.data.\*.rules.\*.indicator_fields | string | | src.ip |
action_result.data.\*.rules.\*.source_excludes | string | | Zscaler |

## action: 'resolve detection'

Resolve a specific detection

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**detection_uuid** | required | Detection UUID to resolve | string | |
**resolution** | required | Resolution state. Options: true_positive_mitigated, true_positive_no_action, false_positive, unknown' | string | |
**resolution_comment** | optional | Optional comment for the resolution | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Detection resolved successfully. |
action_result.parameter.detection_uuid | string | | |
action_result.parameter.resolution | string | | |
action_result.parameter.resolution_comment | string | | |
action_result.data | string | | |

## action: 'get rule events'

Get a list of the events that matched on a specific rule

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**rule_uuid** | required | Rule UUID to get events for | string | |
**account_uuid** | optional | Account uuid to filter by | string | |
**offset** | optional | The number of records to skip past | numeric | |
**limit** | optional | The number of records to return, default: 100, max: 1000 | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Detection Rule Events retrieved successfully. |
action_result.parameter.rule_uuid | string | | |
action_result.parameter.account_uuid | string | | |
action_result.parameter.offset | string | | |
action_result.parameter.limit | string | | |
action_result.data.\*.rule_events.\*.uuid | string | | a7015381-0484-11ee-a43f-067ff9e63f5b |
action_result.data.\*.rule_events.\*.event_type | string | | dns |
action_result.data.\*.rule_events.\*.sensor_id | string | | sen1 |
action_result.data.\*.rule_events.\*.customer_id | string | | gig |
action_result.data.\*.rule_events.\*.timestamp | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.rule_events.\*.host_domain | string | | |
action_result.data.\*.rule_events.\*.src_ip | string | | 8.8.8.8 |
action_result.data.\*.rule_events.\*.src_port | numeric | | 53 |
action_result.data.\*.rule_events.\*.dst_ip | string | | 9.9.9.9 |
action_result.data.\*.rule_events.\*.dst_port | numeric | | 32 |
action_result.data.\*.rule_events.\*.flow_id | string | | Cpv6xc2a3gA6fA8WE |

## action: 'get detection events'

Get a list of the events associated with a specific detection

Type: **investigate** \
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**detection_uuid** | required | Detection uuid to filter by | string | |
**offset** | optional | The number of records to skip past | numeric | |
**limit** | optional | The number of records to return, default: 100, max: 1000 | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Detection Events retrieved successfully. |
action_result.parameter.detection_uuid | string | | |
action_result.parameter.offset | string | | |
action_result.parameter.limit | string | | |
action_result.data.\*.detection_events.\*.detection_uuid | string | | a7015381-0484-11ee-a43f-067ff9e63f5b |
action_result.data.\*.detection_events.\*.rule_uuid | string | | a7015381-0484-11ee-a43f-067ff9e63f5b |
action_result.data.\*.detection_events.\*.uuid | string | | a7015381-0484-11ee-a43f-067ff9e63f5b |
action_result.data.\*.detection_events.\*.event_type | string | | dns |
action_result.data.\*.detection_events.\*.sensor_id | string | | sen1 |
action_result.data.\*.detection_events.\*.customer_id | string | | gig |
action_result.data.\*.detection_events.\*.timestamp | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.ruldetection_eventse_events.\*.host_domain | string | | |
action_result.data.\*.detection_events.\*.src_ip | string | | 8.8.8.8 |
action_result.data.\*.detection_events.\*.src_port | numeric | | 53 |
action_result.data.\*.detection_events.\*.dst_ip | string | | 9.9.9.9 |
action_result.data.\*.detection_events.\*.dst_port | numeric | | 32 |
action_result.data.\*.detection_events.\*.flow_id | string | | Cpv6xc2a3gA6fA8WE |

## action: 'create detection rule'

Create a new detection rule

Type: **generic** \
Read only: **False**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**account_uuid** | required | Account where the rule will be created | string | |
**name** | required | The name of the rule | string | |
**category** | required | The category of the rule | string | |
**query_signature** | required | The IQL query for the rule | string | |
**description** | optional | A description for the rule | string | |
**severity** | required | The severity of the rule | string | |
**confidence** | required | The confidence of the rule | string | |
**primary_attack_id** | optional | Primary Attack ID | string | |
**secondary_attack_id** | optional | Secondary Attack ID | string | |
**specificity** | optional | Specificity | string | |
**device_ip_fields** | optional | List, separated by ',', of the fields to check for impacted devices. Using 'DEFAULT' if not provided | string | |
**indicator_fields** | optional | List, separated by ',' of the indicator's fields | string | |
**run_account_uuids** | required | Account UUIDs on which this rule will run. This will usually be just your own account UUID. (separate multiple accounts by comma) | string | |
**auto_resolution_minutes** | optional | The number of minutes after which detections will be auto-resolved. If 0 then detections have to be manually resolved | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.response_count | numeric | | |
action_result.summary.request | string | | |
summary.total_objects | numeric | | 1 |
summary.total_objects_successful | numeric | | 1 |
action_result.message | string | | Detection Rule created successfully. |
action_result.parameter.account_uuid | string | | |
action_result.parameter.name | string | | |
action_result.parameter.category | string | | |
action_result.parameter.query_signature | string | | |
action_result.parameter.description | string | | |
action_result.parameter.severity | string | | |
action_result.parameter.confidence | string | | |
action_result.parameter.primary_attack_id | string | | |
action_result.parameter.secondary_attack_id | string | | |
action_result.parameter.specificity | string | | |
action_result.parameter.device_ip_fields | string | | |
action_result.parameter.indicator_fields | string | | |
action_result.parameter.run_account_uuids | string | | |
action_result.parameter.auto_resolution_minutes | string | | |
action_result.data.\*.rule.uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rule.account_uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rule.name | string | | AR T1595 |
action_result.data.\*.rule.category | string | | Attack:Infection Vector |
action_result.data.\*.rule.description | string | | |
action_result.data.\*.rule.severity | string | | high moderate low |
action_result.data.\*.rule.confidence | string | | high moderate low |
action_result.data.\*.rule.auto_resolution_minutes | numeric | | 10080 |
action_result.data.\*.rule.enabled | boolean | | True False |
action_result.data.\*.rule.query_signature | string | | ip IN ('1.1.1.1','2.2.2.2') AND event_type = 'dns' |
action_result.data.\*.rule.created | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.rule.created_user_uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rule.updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.rule.updated_user_uuid | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rule.shared_account_uuids | string | | 55f39b72-2622-4137-9051-bc2ff364f059 |
action_result.data.\*.rule.run_account_uuids | string | | ["55f39b72-2622-4137-9051-bc2ff364f059"] |
action_result.data.\*.rule.rule_accounts | string | | |
action_result.data.\*.rule.critical_updated | string | | 2019-01-30T00:00:00.000Z |
action_result.data.\*.rule.primary_attack_id | string | | |
action_result.data.\*.rule.secondary_attack_id | string | | |
action_result.data.\*.rule.specificity | string | | |
action_result.data.\*.rule.device_ip_fields | string | | DEFAULT |
action_result.data.\*.rule.indicator_fields | string | | src.ip |
action_result.data.\*.rule.source_excludes | string | | Zscaler |

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
