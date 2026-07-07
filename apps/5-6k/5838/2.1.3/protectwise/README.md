# ProtectWise

Publisher: Splunk <br>
Connector Version: 2.1.3 <br>
Product Vendor: ProtectWise <br>
Product Name: ProtectWise <br>
Minimum Product Version: 6.2.1

This app integrates with the ProtectWise cloud platform to implement ingestion and investigative actions

The ProtectWise app enables the collection of events and the corresponding related observations into
containers and artifacts in Phantom.

The first thing to do is create the ProtectWise asset in Phantom.\
It's good practice to set the Label of the objects from this source to a **NEW ENTRY** called
**Event** .\
Once the asset is saved, run Test Connectivity and make sure it passes.\
The Test connection action is successful only when the session is created and the REST API call is
made successfully.

## Containers created

The app will create a single container for each Event that it ingests from ProtectWise.

## Event Artifact

Every Event in ProtectWise is made up of Observations. Each Observation is ingested and added as an
Artifact into the created Container. [![](img/artifact.png)](img/artifact.png)

The fields that are present in the artifact greatly depend upon the type of Observation that was
ingested. Different Observations will have different types of values in the artifacts.\
The app supports two modes of ingestion, let's discuss the differences between them.

## POLL NOW

POLL NOW should be used to get a sense of the containers and artifacts that are created by the app.
The POLL NOW dialog allows the user to set the "Maximum containers" that should be ingested at this
instance. Since a single container is created for each event, this value equates to the maximum
events that are ingested by the app. The app will fetch the events in the order they were created in
ProtectWise. The time interval can be configured in hours using the **poll_hours** asset config,
E.g. to ingest events that have been generated in the last 2 hours, configure this value to be 2.
However, the query to ingest this data can be quite time-consuming.

## Scheduled Polling

This mode is used to schedule a polling action on the asset at regular intervals, which is
configured via the INGEST SETTINGS tab of the asset. It makes use of the following asset
configuration parameters (among others):

- Maximum events to poll the first time

  The app detects the first time it is polling an asset and will ingest this number of events (at
  the most). It will also use the **poll_hours** value.

- Maximum Containers for scheduled polling

  For all scheduled polls after the first, the app will ingest this number of events.

In case of Scheduled Polling, on every poll, the app remembers the time of the last event that it
has ingested and will pick up from the same time in the next polling cycle. For best results, keep
the poll interval and *Maximum Containers for scheduled polling* values close to the number of
events you would get within a time interval. This way, every poll will end up ingesting all the new
events.\
It is also very important that the *Maximum Container for scheduled polling* configured should be
greater than the maximum events that are generated **per second** . If the app detects it got the
maximum configured events and all occurred in the same second, it will start polling from the next
second in the next polling cycle.

### Configuration variables

This table lists the configuration variables required to operate ProtectWise. These variables are specified when configuring a ProtectWise asset in Splunk SOAR.

VARIABLE | REQUIRED | TYPE | DESCRIPTION
-------- | -------- | ---- | -----------
**auth_token** | required | password | Authentication Token |
**max_containers** | required | numeric | Maximum events for scheduled polling |
**first_run_max_events** | required | numeric | Maximum events to poll the first time (For scheduled polling) |
**poll_hours** | required | numeric | Ingest events in last N hours (Poll Now and First Run) |
**allow_duplicate_artifacts** | optional | boolean | Display duplicate artifacts from polling |
**allow_duplicate_containers** | optional | boolean | Display duplicate containers from polling |
**retry_count** | optional | numeric | Maximum attempts to retry the API call in case of rate limit (Default: 3) |

### Supported Actions

[test connectivity](#action-test-connectivity) - Validate the asset configuration for connectivity <br>
[get pcap](#action-get-pcap) - Download pcap for an event or observation <br>
[hunt ip](#action-hunt-ip) - Hunt an IP in the network <br>
[hunt domain](#action-hunt-domain) - Hunt a domain in the network <br>
[hunt file](#action-hunt-file) - Hunt for a file in the network <br>
[on poll](#action-on-poll) - Query ProtectWise for Events and Observables and ingest into Splunk SOAR

## action: 'test connectivity'

Validate the asset configuration for connectivity

Type: **test** <br>
Read only: **True**

#### Action Parameters

No parameters are required for this action

#### Action Output

No Output

## action: 'get pcap'

Download pcap for an event or observation

Type: **investigate** <br>
Read only: **True**

A few things to note:<ul><li>Valid values for the <b>type</b> parameter are: <ul><li>Event</li><li>Observation</li></ul></li><li>The app adds the <i>Event ID</i> to every container as its <b>Source ID</b>(source_data_identifier)<a href="/app_resource/protectwise_e8f8d8dc-916f-4267-be15-e9b697dd58c5/img/sdi.png"><img src="/app_resource/protectwise_e8f8d8dc-916f-4267-be15-e9b697dd58c5/img/sdi.png"/></a><br>Unfortunately, this value can get clipped in the UI. Instead, use the download button to download the container json and extract the source_data_identifier key value<a href="/app_resource/protectwise_e8f8d8dc-916f-4267-be15-e9b697dd58c5/img/sdi2.png"><img src="/app_resource/protectwise_e8f8d8dc-916f-4267-be15-e9b697dd58c5/img/sdi2.png"/></a><br></li><li>The app adds the <i>Observation ID</i> to every Artifact in a key named <b>observationId</b> of the cef dictionary<a href="/app_resource/protectwise_e8f8d8dc-916f-4267-be15-e9b697dd58c5/img/artifact.png"><img src="/app_resource/protectwise_e8f8d8dc-916f-4267-be15-e9b697dd58c5/img/artifact.png"/></a><br></li><li>The <b>sensorid</b> parameter is only required if the <b>type</b> is <b>Observation</b></li><li>The pcap file is added to the vault with a file name of \<<b>id</b>>.pcap</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**type** | required | The ID type | string | |
**id** | required | ID Value (Event or Observation ) | string | `protectwise event id` `protectwise observation id` |
**sensorid** | optional | Sensor ID | string | `protectwise sensor id` |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.id | string | `protectwise event id` `protectwise observation id` | 0005c39404209a9874014a71c6e384a16aa520474614f1a7ca781955 |
action_result.parameter.sensorid | string | `protectwise sensor id` | 3100 |
action_result.parameter.type | string | | Event Observation |
action_result.data.\*.estimatedSize | numeric | | |
action_result.data.\*.id | string | | |
action_result.data.\*.netflows.\*.endTime | numeric | | |
action_result.data.\*.netflows.\*.flowId | string | | |
action_result.data.\*.netflows.\*.sensorId | numeric | `protectwise sensor id` | |
action_result.data.\*.netflows.\*.startTime | numeric | | |
action_result.data.\*.vault_info.container | numeric | | |
action_result.data.\*.vault_info.file_name | string | | |
action_result.data.\*.vault_info.hash | string | | |
action_result.data.\*.vault_info.message | string | | |
action_result.data.\*.vault_info.succeeded | boolean | | |
action_result.data.\*.vault_info.vault_id | string | `vault id` | |
action_result.summary.vault_id | string | `vault id` | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |

## action: 'hunt ip'

Hunt an IP in the network

Type: **investigate** <br>
Read only: **True**

To get info within a time range specify the <b>start_time</b> and <b>end_time</b>. These parameters take time in the Zulu format which can be expressed as %Y-%m-%dT%H:%M:%S.%fZ e.g. 2016-12-30T13:00:00.0000Z.<br><ul><li>If <b>start_time</b> and <b>end_time</b> both are not specified, then the app defaults to last 5 days</li><li>If <b>start_time</b> is specified and <b>end_time</b> is not, then the app will default the <b>end_time</b> to <i>current</i></li><li>If <b>start_time</b> is not specified and <b>end_time</b> is, the app will throw an error</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**ip** | required | IP Address | string | `ip` `ipv6` |
**start_time** | optional | Start time (Zulu format) | string | |
**end_time** | optional | End time (Zulu format) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.end_time | string | | 2016-12-30T13:00:00.0000Z |
action_result.parameter.ip | string | `ip` `ipv6` | 8.8.8.8 |
action_result.parameter.start_time | string | | 2016-12-30T13:00:00.0000Z |
action_result.data.\*.ip.host | string | | |
action_result.data.\*.ip.organization | string | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.end | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.interval | string | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.intervalSize | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.start | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.values.\*.count | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.values.\*.timestamp | numeric | | |
action_result.data.\*.threat.events.count.total | numeric | | |
action_result.data.\*.threat.events.maxThreatLevel | string | | |
action_result.data.\*.threat.events.maxThreatScore | numeric | | |
action_result.data.\*.threat.events.threatCategory.MaliciousHost | numeric | | |
action_result.data.\*.threat.events.threatSubCategory.MachineGeneratedDomain | numeric | `domain` | |
action_result.data.\*.threat.events.top.\*.\_original.agentId | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.category | string | | |
action_result.data.\*.threat.events.top.\*.\_original.cid | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.confidence | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.endedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.id | string | | |
action_result.data.\*.threat.events.top.\*.\_original.isUpdate | boolean | | |
action_result.data.\*.threat.events.top.\*.\_original.killChainStage | string | | |
action_result.data.\*.threat.events.top.\*.\_original.message | string | | |
action_result.data.\*.threat.events.top.\*.\_original.netflowCount | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.observationCount | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.observedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.observedStage | string | | |
action_result.data.\*.threat.events.top.\*.\_original.sensorIds | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.startedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.threatLevel | string | | |
action_result.data.\*.threat.events.top.\*.\_original.threatScore | numeric | | |
action_result.data.\*.threat.events.top.\*.\_original.threatSubCategory | string | | |
action_result.data.\*.threat.events.top.\*.\_original.type | string | | |
action_result.data.\*.threat.events.top.\*.\_state.agentId | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.category | string | | |
action_result.data.\*.threat.events.top.\*.\_state.cid | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.confidence | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.endedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.id | string | | |
action_result.data.\*.threat.events.top.\*.\_state.isUpdate | boolean | | |
action_result.data.\*.threat.events.top.\*.\_state.killChainStage | string | | |
action_result.data.\*.threat.events.top.\*.\_state.message | string | | |
action_result.data.\*.threat.events.top.\*.\_state.netflowCount | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.observationCount | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.observedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.observedStage | string | | |
action_result.data.\*.threat.events.top.\*.\_state.sensorIds | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.startedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.threatLevel | string | | |
action_result.data.\*.threat.events.top.\*.\_state.threatScore | numeric | | |
action_result.data.\*.threat.events.top.\*.\_state.threatSubCategory | string | | |
action_result.data.\*.threat.events.top.\*.\_state.type | string | | |
action_result.data.\*.threat.events.top.\*.agentId | numeric | | |
action_result.data.\*.threat.events.top.\*.category | string | | |
action_result.data.\*.threat.events.top.\*.cid | numeric | | |
action_result.data.\*.threat.events.top.\*.confidence | numeric | | |
action_result.data.\*.threat.events.top.\*.endedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.id | string | | |
action_result.data.\*.threat.events.top.\*.isUpdate | boolean | | |
action_result.data.\*.threat.events.top.\*.killChainStage | string | | |
action_result.data.\*.threat.events.top.\*.message | string | | |
action_result.data.\*.threat.events.top.\*.netflowCount | numeric | | |
action_result.data.\*.threat.events.top.\*.observationCount | numeric | | |
action_result.data.\*.threat.events.top.\*.observedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.observedStage | string | | |
action_result.data.\*.threat.events.top.\*.priority | boolean | | |
action_result.data.\*.threat.events.top.\*.sensorId | numeric | | |
action_result.data.\*.threat.events.top.\*.sensorIds | numeric | | |
action_result.data.\*.threat.events.top.\*.startedAt | numeric | | |
action_result.data.\*.threat.events.top.\*.threatLevel | string | | |
action_result.data.\*.threat.events.top.\*.threatScore | numeric | | |
action_result.data.\*.threat.events.top.\*.threatSubCategory | string | | |
action_result.data.\*.threat.events.top.\*.type | string | | |
action_result.data.\*.threat.observations.maxThreatLevel | string | | |
action_result.data.\*.threat.observations.maxThreatScore | numeric | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.end | numeric | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.interval | string | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.intervalSize | numeric | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.start | numeric | | |
action_result.data.\*.threat.observations.timeSeries.values.\*.count | numeric | | |
action_result.data.\*.threat.observations.timeSeries.values.\*.timestamp | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.agentId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.direction | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.dstGeo.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.dstGeo.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.dstIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.dstMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.dstPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.layer3Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.layer4Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.srcIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.srcMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.ip.srcPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.key | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.associatedId.flowId.startTime | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.category | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.cid | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.confidence | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.dstIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.dstMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.dstPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.layer3Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.layer4Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.srcIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.srcMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.connectionInfo.srcPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.dnsReputation.category | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.dnsReputation.dns | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.dnsReputation.partnerCategory | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.classification | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.description | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.generatorId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.priorityId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.revision | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.signatureId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.timestampMicros | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.data.idsEvent.timestampSeconds | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.dstGeo.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.dstGeo.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.id | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.info.coordinates.\*.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.info.coordinates.\*.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.info.ips | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.info.ports | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.killChainStage | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.netflowId | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.observationDirection | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.observedAt | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.observedStage | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.occurredAt | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.severity | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.source | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.threatLevel | string | | |
action_result.data.\*.threat.observations.top.\*.\_original.threatScore | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_original.threatSubCategory | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.agentId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.direction | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.dstGeo.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.dstGeo.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.dstIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.dstMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.dstPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.layer3Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.layer4Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.srcIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.srcMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.ip.srcPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.key | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.associatedId.flowId.startTime | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.category | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.cid | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.confidence | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.dstIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.dstMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.dstPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.layer3Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.layer4Proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.proto | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.srcIp | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.srcMac | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.connectionInfo.srcPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.dnsReputation.category | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.dnsReputation.dns | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.dnsReputation.partnerCategory | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.classification | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.description | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.generatorId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.priorityId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.revision | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.signatureId | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.timestampMicros | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.data.idsEvent.timestampSeconds | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.dstGeo.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.dstGeo.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.id | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.info.coordinates.\*.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.info.coordinates.\*.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.info.ips | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.info.ports | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.killChainStage | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.netflowId | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.observationDirection | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.observedAt | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.observedStage | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.occurredAt | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.severity | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.source | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.threatLevel | string | | |
action_result.data.\*.threat.observations.top.\*.\_state.threatScore | numeric | | |
action_result.data.\*.threat.observations.top.\*.\_state.threatSubCategory | string | | |
action_result.data.\*.threat.observations.top.\*.agentId | numeric | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.direction | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.dstGeo.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.dstGeo.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.dstIp | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.dstMac | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.dstPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.layer3Proto | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.layer4Proto | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.proto | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.srcIp | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.srcMac | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.ip.srcPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.key | string | | |
action_result.data.\*.threat.observations.top.\*.associatedId.flowId.startTime | numeric | | |
action_result.data.\*.threat.observations.top.\*.category | string | | |
action_result.data.\*.threat.observations.top.\*.cid | numeric | | |
action_result.data.\*.threat.observations.top.\*.confidence | numeric | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.dstIp | string | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.dstMac | string | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.dstPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.layer3Proto | string | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.layer4Proto | string | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.proto | string | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.srcIp | string | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.srcMac | string | | |
action_result.data.\*.threat.observations.top.\*.connectionInfo.srcPort | numeric | | |
action_result.data.\*.threat.observations.top.\*.data.dnsReputation.category | string | | |
action_result.data.\*.threat.observations.top.\*.data.dnsReputation.dns | string | | |
action_result.data.\*.threat.observations.top.\*.data.dnsReputation.partnerCategory | string | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.classification | string | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.description | string | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.generatorId | numeric | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.priorityId | numeric | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.revision | numeric | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.signatureId | numeric | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.timestampMicros | numeric | | |
action_result.data.\*.threat.observations.top.\*.data.idsEvent.timestampSeconds | numeric | | |
action_result.data.\*.threat.observations.top.\*.dstGeo.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.dstGeo.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.id | string | | |
action_result.data.\*.threat.observations.top.\*.info.coordinates.\*.lat | numeric | | |
action_result.data.\*.threat.observations.top.\*.info.coordinates.\*.lon | numeric | | |
action_result.data.\*.threat.observations.top.\*.info.ips | string | | |
action_result.data.\*.threat.observations.top.\*.info.ports | numeric | | |
action_result.data.\*.threat.observations.top.\*.killChainStage | string | | |
action_result.data.\*.threat.observations.top.\*.netflowId | string | | |
action_result.data.\*.threat.observations.top.\*.observationDirection | string | | |
action_result.data.\*.threat.observations.top.\*.observedAt | numeric | | |
action_result.data.\*.threat.observations.top.\*.observedStage | string | | |
action_result.data.\*.threat.observations.top.\*.occurredAt | numeric | | |
action_result.data.\*.threat.observations.top.\*.sensorId | numeric | | |
action_result.data.\*.threat.observations.top.\*.severity | numeric | | |
action_result.data.\*.threat.observations.top.\*.source | string | | |
action_result.data.\*.threat.observations.top.\*.threatLevel | string | | |
action_result.data.\*.threat.observations.top.\*.threatScore | numeric | | |
action_result.data.\*.threat.observations.top.\*.threatSubCategory | string | | |
action_result.data.\*.threat.observations.types.DnsReputation | numeric | | |
action_result.data.\*.threat.observations.types.Ids | numeric | | |
action_result.summary.event_count | numeric | | |
action_result.summary.ip_organization | string | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.ph | ph | | |

## action: 'hunt domain'

Hunt a domain in the network

Type: **investigate** <br>
Read only: **True**

To get info within a time range specify the <b>start_time</b> and <b>end_time</b>. These parameters take time in the Zulu format which can be expressed as %Y-%m-%dT%H:%M:%S.%fZ e.g. 2016-12-30T13:00:00.0000Z.<br><ul><li>If <b>start_time</b> and <b>end_time</b> both are not specified, then the app defaults to last 5 days</li><li>If <b>start_time</b> is specified and <b>end_time</b> is not, then the app will default the <b>end_time</b> to <i>current</i></li><li>If <b>start_time</b> is not specified and <b>end_time</b> is, the app will throw an error</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**domain** | required | Domain | string | `domain` |
**start_time** | optional | Start time (Zulu format) | string | |
**end_time** | optional | End time (Zulu format) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.domain | string | `domain` | test.com |
action_result.parameter.end_time | string | | 2016-12-30T13:00:00.0000Z |
action_result.parameter.start_time | string | | 2016-12-30T13:00:00.0000Z |
action_result.data.\*.domain.resolveData.\*.firstSeen | numeric | | |
action_result.data.\*.domain.resolveData.\*.lastSeen | numeric | | |
action_result.data.\*.domain.resolveData.\*.resolvesTo | string | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.end | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.interval | string | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.intervalSize | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.timeRange.start | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.values.\*.count | numeric | | |
action_result.data.\*.threat.events.count.timeSeries.values.\*.timestamp | numeric | | |
action_result.data.\*.threat.events.count.total | numeric | | |
action_result.data.\*.threat.ipAddresses | string | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.end | numeric | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.interval | string | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.intervalSize | numeric | | |
action_result.data.\*.threat.observations.timeSeries.timeRange.start | numeric | | |
action_result.data.\*.threat.observations.timeSeries.values.\*.count | numeric | | |
action_result.data.\*.threat.observations.timeSeries.values.\*.timestamp | numeric | | |
action_result.summary.domain_organization | string | | |
action_result.summary.event_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.ph | ph | | |

## action: 'hunt file'

Hunt for a file in the network

Type: **investigate** <br>
Read only: **True**

To get info within a time range specify the <b>start_time</b> and <b>end_time</b>. These parameters take time in the Zulu format which can be expressed as %Y-%m-%dT%H:%M:%S.%fZ e.g. 2016-12-30T13:00:00.0000Z.<br><ul><li>If <b>start_time</b> and <b>end_time</b> both are not specified, then the app defaults to last 5 days</li><li>If <b>start_time</b> is specified and <b>end_time</b> is not, then the app will default the <b>end_time</b> to <i>current</i></li><li>If <b>start_time</b> is not specified and <b>end_time</b> is, the app will throw an error</li></ul>.

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**hash** | required | File Hash | string | `sha256` |
**start_time** | optional | Start time (Zulu format) | string | |
**end_time** | optional | End time (Zulu format) | string | |

#### Action Output

DATA PATH | TYPE | CONTAINS | EXAMPLE VALUES
--------- | ---- | -------- | --------------
action_result.status | string | | success failed |
action_result.parameter.end_time | string | | 2016-12-30T13:00:00.0000Z |
action_result.parameter.hash | string | `sha256` | e3545e19f5f74d733306991ce232ad4ee7556ca1c47cb07740dda148be3d05c2 |
action_result.parameter.start_time | string | | 2016-12-30T13:00:00.0000Z |
action_result.data.\*.behavior.network.dns.\*.hostname | string | `host name` | |
action_result.data.\*.behavior.network.dns.\*.ip | string | `ip` `ipv6` | |
action_result.data.\*.behavior.network.hosts | string | | |
action_result.data.\*.behavior.network.http.\*.body | string | | |
action_result.data.\*.behavior.network.http.\*.data | string | | |
action_result.data.\*.behavior.network.http.\*.host | string | | |
action_result.data.\*.behavior.network.http.\*.method | string | | |
action_result.data.\*.behavior.network.http.\*.path | string | | |
action_result.data.\*.behavior.network.http.\*.port | numeric | | |
action_result.data.\*.behavior.network.http.\*.uri | string | | |
action_result.data.\*.behavior.network.http.\*.user-agent | string | | |
action_result.data.\*.behavior.network.http.\*.version | string | | |
action_result.data.\*.behavior.network.tcp.\*.dport | numeric | `port` | |
action_result.data.\*.behavior.network.tcp.\*.dst | string | `ip` `ipv6` | |
action_result.data.\*.behavior.network.tcp.\*.sport | numeric | `port` | |
action_result.data.\*.behavior.network.tcp.\*.src | string | `ip` `ipv6` | |
action_result.data.\*.behavior.network.udp.\*.dport | numeric | | |
action_result.data.\*.behavior.network.udp.\*.dst | string | | |
action_result.data.\*.behavior.network.udp.\*.sport | numeric | | |
action_result.data.\*.behavior.network.udp.\*.src | string | | |
action_result.data.\*.info.detectedFileSize | numeric | | |
action_result.data.\*.info.detectedType | string | | |
action_result.data.\*.info.hashes.md5 | string | `md5` | |
action_result.data.\*.info.hashes.sha1 | string | `sha1` | |
action_result.data.\*.info.hashes.sha256 | string | `sha256` | |
action_result.data.\*.info.hashes.sha512 | string | `sha512` | |
action_result.data.\*.info.id | string | | |
action_result.data.\*.info.isArchive | boolean | | |
action_result.data.\*.info.isEncrypted | boolean | | |
action_result.data.\*.info.type | string | | |
action_result.data.\*.observations.count | numeric | | |
action_result.data.\*.observations.facets.fields.fileExtractedName | string | | |
action_result.data.\*.observations.facets.fields.fileExtractedName.23.exe | numeric | | |
action_result.data.\*.observations.nextOffset | string | | |
action_result.data.\*.observations.results.\*.agentId | numeric | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.direction | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.dstGeo.lat | numeric | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.dstGeo.lon | numeric | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.dstIp | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.dstMac | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.dstPort | numeric | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.layer3Proto | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.layer4Proto | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.proto | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.srcIp | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.srcMac | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.ip.srcPort | numeric | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.key | string | | |
action_result.data.\*.observations.results.\*.associatedId.flowId.startTime | numeric | | |
action_result.data.\*.observations.results.\*.category | string | | |
action_result.data.\*.observations.results.\*.cid | numeric | | |
action_result.data.\*.observations.results.\*.confidence | numeric | | |
action_result.data.\*.observations.results.\*.connectionInfo.dstIp | string | | |
action_result.data.\*.observations.results.\*.connectionInfo.dstMac | string | | |
action_result.data.\*.observations.results.\*.connectionInfo.dstPort | numeric | | |
action_result.data.\*.observations.results.\*.connectionInfo.layer3Proto | string | | |
action_result.data.\*.observations.results.\*.connectionInfo.layer4Proto | string | | |
action_result.data.\*.observations.results.\*.connectionInfo.proto | string | | |
action_result.data.\*.observations.results.\*.connectionInfo.srcIp | string | | |
action_result.data.\*.observations.results.\*.connectionInfo.srcMac | string | | |
action_result.data.\*.observations.results.\*.connectionInfo.srcPort | numeric | | |
action_result.data.\*.observations.results.\*.data.fileReputation.advertisedType | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.category | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.detectedFileSize | numeric | | |
action_result.data.\*.observations.results.\*.data.fileReputation.detectedType | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.end | numeric | | |
action_result.data.\*.observations.results.\*.data.fileReputation.extractedName | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.extractedPath | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.finding.score | numeric | | |
action_result.data.\*.observations.results.\*.data.fileReputation.hashes.md5 | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.hashes.sha1 | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.hashes.sha256 | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.hashes.sha512 | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.id | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.isArchive | boolean | | |
action_result.data.\*.observations.results.\*.data.fileReputation.isEncrypted | boolean | | |
action_result.data.\*.observations.results.\*.data.fileReputation.isTruncated | boolean | | |
action_result.data.\*.observations.results.\*.data.fileReputation.isTypeMismatched | boolean | | |
action_result.data.\*.observations.results.\*.data.fileReputation.serviceType | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.start | numeric | | |
action_result.data.\*.observations.results.\*.data.fileReputation.transportProtocol | string | | |
action_result.data.\*.observations.results.\*.data.fileReputation.type | string | | |
action_result.data.\*.observations.results.\*.dstGeo.lat | numeric | | |
action_result.data.\*.observations.results.\*.dstGeo.lon | numeric | | |
action_result.data.\*.observations.results.\*.id | string | | |
action_result.data.\*.observations.results.\*.info.coordinates.\*.lat | numeric | | |
action_result.data.\*.observations.results.\*.info.coordinates.\*.lon | numeric | | |
action_result.data.\*.observations.results.\*.info.ips | string | | |
action_result.data.\*.observations.results.\*.info.ports | numeric | | |
action_result.data.\*.observations.results.\*.killChainStage | string | | |
action_result.data.\*.observations.results.\*.netflowId | string | | |
action_result.data.\*.observations.results.\*.observationDirection | string | | |
action_result.data.\*.observations.results.\*.observedAt | numeric | | |
action_result.data.\*.observations.results.\*.observedStage | string | | |
action_result.data.\*.observations.results.\*.occurredAt | numeric | | |
action_result.data.\*.observations.results.\*.sensorId | numeric | | |
action_result.data.\*.observations.results.\*.severity | numeric | | |
action_result.data.\*.observations.results.\*.source | string | | |
action_result.data.\*.observations.results.\*.threatLevel | string | | |
action_result.data.\*.observations.results.\*.threatScore | numeric | | |
action_result.data.\*.observations.results.\*.threatSubCategory | string | | |
action_result.summary.detected_type | string | | |
action_result.summary.file_type | string | | |
action_result.summary.id | string | | |
action_result.summary.observation_count | numeric | | |
action_result.message | string | | |
summary.total_objects | numeric | | |
summary.total_objects_successful | numeric | | |
action_result.parameter.ph | ph | | |

## action: 'on poll'

Query ProtectWise for Events and Observables and ingest into Splunk SOAR

Type: **ingest** <br>
Read only: **True**

#### Action Parameters

PARAMETER | REQUIRED | DESCRIPTION | TYPE | CONTAINS
--------- | -------- | ----------- | ---- | --------
**container_id** | optional | Container IDs to limit the ingestion to | string | |
**start_time** | optional | Start of time range, in epoch time (milliseconds), if not specified, the default is past 10 days | numeric | |
**end_time** | optional | End of time range, in epoch time (milliseconds), if not specified, the default is now | numeric | |
**container_count** | optional | Maximum number of container records to query for | numeric | |
**artifact_count** | optional | Maximum number of artifact records to query for | numeric | |

#### Action Output

No Output

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
