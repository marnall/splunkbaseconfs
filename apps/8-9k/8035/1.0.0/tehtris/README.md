# Tehtris

Publisher: Splunk <br>
Connector Version: 1.0.0 <br>
Product Vendor: Tehtris <br>
Product Name: Tehtris <br>
Minimum Product Version: 6.3.0

This app integrates with Tehtris XDR platform endpoints

### Configuration variables

This table lists the configuration variables required to operate Tehtris. These variables are specified when configuring a Tehtris asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**base_url** | required | string | Tehtris XDR base url |
**api_key** | required | password | Tehtris XDR api key |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity using supplied configuration <br>
[get events](#action-get-events) - Fetch XDR events <br>
[send for isolation](#action-send-for-isolation) - Send a host to the isolation module <br>
[remove from isolation](#action-remove-from-isolation) - Remove a host from isolation <br>
[list processes](#action-list-processes) - Get process tree from a process <br>
[update tag](#action-update-tag) - Update endpoints tags <br>
[create app policy](#action-create-app-policy) - Create new application policy based on sha256

## action: 'test connectivity'

Validate the asset configuration for connectivity using supplied configuration

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get events'

Fetch XDR events

Type: **contain** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**from_date** | required | Seconds since EPOCH in UTC timezone of the starting date from when fetch the events. | numeric | |
**to_date** | optional | Seconds since EPOCH in UTC timezone of the ending date to fetch the events. Leave blank to fetch events until now | numeric | |
**limit** | optional | Maximum number of fetched events. Can not be greater than 100. | numeric | |
**offset** | optional | Number of events to skip before starting to collect the result set. | numeric | |
**filter_id** | optional | The Filter ID used to retrieve events, if no filterId is specified in query the first filter Id store with API Key is used. | string | |
**hostname** | required | Hostname to filter results by | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.num_events | string | | 10 |
action_result.data.\*.id | string | | |
action_result.data.\*.lvl | string | | |
action_result.data.\*.pid | string | | |
action_result.data.\*.tag | string | | |
action_result.data.\*.uid | string | | |
action_result.data.\*.os\_\_ | string | | |
action_result.data.\*.path | string | | |
action_result.data.\*.ppid | string | | |
action_result.data.\*.time | string | | |
action_result.data.\*.ipDst | string | | |
action_result.data.\*.ipSrc | string | | |
action_result.data.\*.rflId | string | | |
action_result.data.\*.egKBId | string | | |
action_result.data.\*.module | string | | |
action_result.data.\*.action | string | | |
action_result.data.\*.sha256 | string | | |
action_result.data.threat.framework | string | | |
action_result.data.\*.threat.id | string | | |
action_result.data.\*.threat.name | string | | |
action_result.data.\*.uuid | string | | |
action_result.data.\*.cmdline | string | | |
action_result.data.\*.mitre | string | | |
action_result.data.\*.cmdline | string | | |
action_result.data.\*.tehtris.file.hash.sha256 | string | | |
action_result.data.\*.tehtris.file.hash.original | string | | |
action_result.data.\*.tehtris.host.id.\* | string | | |
action_result.data.\*.tehtris.host.name.\* | string | | |
action_result.data.\*.tehtris.user.name.\* | string | | |
action_result.data.\*.tehtris.even.ingested | string | | |
action_result.data.\*.tehtris.source.ip | string | | |
action_result.data.\*.tehtris.process.pid | string | | |
action_result.data.\*.tehtris.process.parent.pid | string | | |
action_result.data.\*.tehtris.process.executable | string | | |
action_result.data.\*.tehtris.process.command_line | string | | |
action_result.data.\*.tehtris.groupIds.\* | string | | |
action_result.data.\*.tehtris.enrichment.tags.\* | string | | |
action_result.data.\*.tehtris.destination.ip | string | | |
action_result.data.\*.domain | string | | |
action_result.data.\*.location | string | | |
action_result.data.\*.username | string | | |
action_result.data.\*.eventName | string | | |
action_result.data.\*.hostname\_\_ | string | | |
action_result.data.\*.description | string | | |
action_result.data.\*.os_server\_\_ | boolean | | |
action_result.data.\*.submodule\_\_ | string | | |
action_result.data.\*.os_release\_\_ | string | | |
action_result.data.\*.os_version\_\_ | string | | |
action_result.data.\*.fileVersion\_\_ | string | | |
action_result.data.\*.productName\_\_ | string | | |
action_result.data.\*.pCreateDatetime | string | | |
action_result.data.\*.publisherName\_\_ | string | | |
action_result.data.\*.signatureType\_\_ | string | | |
action_result.data.\*.os_architecture\_\_ | string | | |
action_result.data.\*.signatureStatus\_\_ | string | | |
action_result.data.\*.originalFilename\_\_ | string | | |
action_result.parameter.from_date | numeric | | |
action_result.parameter.to_date | numeric | | |
action_result.parameter.limit | numeric | | |
action_result.parameter.offset | numeric | | |
action_result.parameter.filter_id | string | | |
action_result.parameter.hostname | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

## action: 'send for isolation'

Send a host to the isolation module

Type: **contain** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | required | Hostname to be sent for isolation | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.result | string | | Successfully posted uuid ffdf773d-b124-4387-b772-a87ec08640c2 for isolation |
action_result.parameter.hostname | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

## action: 'remove from isolation'

Remove a host from isolation

Type: **contain** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | required | Hostname to be removed from isolation | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.result | string | | Successfully removed uuid ffdf773d-b124-4387-b772-a87ec08640c2 from isolation |
action_result.parameter.hostname | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

## action: 'list processes'

Get process tree from a process

Type: **contain** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | required | Hostname | string | |
**create_time** | required | Local created time of the process | string | |
**pid** | required | Database id of the process to use to build the tree | string | |
**number_of_parents** | required | Number of parents to retrieve | numeric | |
**limit** | required | Maximum number of results | numeric | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.num_events | string | | 10 |
action_result.data.\*.id | string | | |
action_result.data.\*.pid | string | | |
action_result.data.\*.uid | string | | |
action_result.data.\*.ppid | string | | |
action_result.data.\*.cmdline | string | | |
action_result.data.\*.created | string | | |
action_result.data.\*.logonId | string | | |
action_result.data.\*.stopped | string | | |
action_result.data.\*.binaries.\*.md5 | string | | |
action_result.data.\*.binaries.\*.flag | string | | |
action_result.data.\*.binaries.\*.path | string | | |
action_result.data.\*.binaries.\*.sha1 | string | | |
action_result.data.\*.binaries.\*.size | numeric | | |
action_result.data.\*.binaries.\*.tags | string | | |
action_result.data.\*.binaries.\*.atime | string | | |
action_result.data.\*.binaries.\*.ctime | string | | |
action_result.data.\*.binaries.\*.mtime | string | | |
action_result.data.\*.binaries.\*.sha256 | string | | |
action_result.data.\*.binaries.\*.avScore | numeric | | |
action_result.data.\*.binaries.\*.avTotal | numeric | | |
action_result.data.\*.binaries.\*.lastSeen | string | | |
action_result.data.\*.binaries.\*.malicious | numeric | | |
action_result.data.\*.binaries.\*.lastUpdate | string | | |
action_result.data.\*.binaries.\*.signatures.\*.C | string | | |
action_result.data.\*.binaries.\*.signatures.\*.L | string | | |
action_result.data.\*.binaries.\*.signatures.\*.O | string | | |
action_result.data.\*.binaries.\*.signatures.\*.S | string | | |
action_result.data.\*.binaries.\*.signatures.\*.CN | string | | |
action_result.data.\*.binaries.\*.signatures.\*.OU | string | | |
action_result.data.\*.binaries.\*.signatures.\*.type | string | | |
action_result.data.\*.binaries.\*.signatures.\*.notAfter | string | | |
action_result.data.\*.binaries.\*.signatures.\*.notBefore | string | | |
action_result.data.\*.binaries.\*.signatures.\*.issuers_fp.\* | string | | |
action_result.data.\*.binaries.\*.signatures.\*.fingerprint | string | | |
action_result.data.\*.binaries.\*.remediation | numeric | | |
action_result.data.\*.binaries.\*.sandboxScore | numeric | | |
action_result.data.\*.bootTime | string | | |
action_result.data.\*.children.\* | string | | |
action_result.data.\*.parentId | string | | |
action_result.data.\*.username | string | | |
action_result.data.\*.domainName | string | | |
action_result.data.\*.processFlag | numeric | | |
action_result.data.\*.remediation | numeric | | |
action_result.data.\*.createdServer | string | | |
action_result.data.\*.stoppedServer | string | | |
action_result.parameter.hostname | string | | |
action_result.parameter.create_time | string | | |
action_result.parameter.pid | string | | |
action_result.parameter.number_of_parents | numeric | | |
action_result.parameter.limit | numeric | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

## action: 'update tag'

Update endpoints tags

Type: **contain** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostname** | required | Hostname | string | |
**tag** | required | Tag to be applied, should follow 'XXX_tags pattern | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.result | string | | Successfully added tag 'example_tag for uuid ffdf773d-b124-4387-b772-a87ec08640c2 |
action_result.parameter.hostname | string | | |
action_result.parameter.tag | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

## action: 'create app policy'

Create new application policy based on sha256

Type: **contain** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hostnames** | required | Comma separated hostnames | string | |
**sha256** | required | Comma spearated sha256 values | string | |
**order** | required | Order to be attached to the policy | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.summary.result | string | | Successfully posted new app policy for ffdf773d-b124-4387-b772-a87ec08640c2 |
action_result.parameter.hostnames | string | | |
action_result.parameter.sha256 | string | | |
action_result.parameter.order | string | | |
action_result.message | string | | |
summary.total_objects_successful | numeric | | |
summary.total_objects | numeric | | |

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
