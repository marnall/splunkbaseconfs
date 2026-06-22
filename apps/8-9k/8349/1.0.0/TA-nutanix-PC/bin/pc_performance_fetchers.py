import logger.log as log
from datetime import datetime
from pc_helpers import BaseFetcher


class ClusterPerformanceFetcher(BaseFetcher):
    entity = "cluster_performance"
    sourcetype = "nutanixpc_cluster_performance"
    source = "nutanixpc:pcperformance"
    logger = log.Logs().get_logger("PCPerformance")
    
    metrics = [
        'controllerAvgIoLatencyUsecs',
        'controllerAvgReadIoLatencyUsecs',
        'controllerAvgWriteIoLatencyUsecs',
        'controllerNumIops',
        'controllerNumReadIops',
        'controllerNumWriteIops',
        'ioBandwidthKbps',
        'controllerReadIoBandwidthKbps',
        'controllerWriteIoBandwidthKbps',
        'hypervisorCpuUsagePpm',
        'aggregateHypervisorMemoryUsagePpm',
        'storageUsageBytes',
        'storageCapacityBytes',
        'freePhysicalStorageBytes',
        'logicalStorageUsageBytes',
        'overallMemoryUsageBytes'
    ]
    extra_fields = ['extId']


    def get_events(self, events):
        return self.performance_statistics(metrics=self.metrics, extra_fields=self.extra_fields, json_list=events)

    def get_clusters_list(self):
        events, _ = self.collect_event_data(
            entity="clusters",
            pagination_limit=100,
        )
        return [event['extId'] for event in events  if 'PRISM_CENTRAL' not in event['config']['clusterFunction']]


class HostPerformanceFetcher(BaseFetcher):
    entity = "host_performance"
    sourcetype = "nutanixpc_host_performance"
    source = "nutanixpc:pcperformance"
    logger = log.Logs().get_logger("PCPerformance")

    metrics = [
        'controllerAvgIoLatencyUsecs',
        'controllerAvgReadIoLatencyUsecs',
        'controllerAvgWriteIoLatencyUsecs',
        'controllerNumIops',
        'controllerNumReadIops',
        'controllerNumWriteIops',
        'ioBandwidthKbps',
        'controllerReadIoBandwidthKbps',
        'controllerWriteIoBandwidthKbps',
        'hypervisorCpuUsagePpm',
        'aggregateHypervisorMemoryUsagePpm',
        'storageUsageBytes',
        'storageCapacityBytes',
        'freePhysicalStorageBytes',
        'memoryCapacityBytes',
        'cpuCapacityHz',
        'overollMemoryUsagePpm',
    ]
    extra_fields = ['extId']

    def get_events(self, events):
        return self.performance_statistics(metrics=self.metrics, extra_fields=self.extra_fields, json_list=events)

    def get_hosts_data(self):
        events, _ = self.collect_event_data(
            entity="hosts",
            pagination_limit=100,
        )
        return [(event['extId'], event['cluster']['uuid']) for event in events]


class DiskPerformanceFetcher(BaseFetcher):
    entity = "disk_performance"
    sourcetype = "nutanixpc_disk_performance"
    source = "nutanixpc:pcperformance"
    logger = log.Logs().get_logger("PCPerformance")

    metrics = [
        'diskUsagePpm',
        'diskCapacityBytes',
        'diskNumIops',
        'diskIoBandwidthkbps',
        'diskAvgIoLatencyMicrosec',
        'diskFreeBytes',
        'diskUsageBytes',
        'diskReadIops',
        'diskWriteIops',
        'diskReadIoBandwidthkbps',
        'diskWriteIoBandwidthkbps',
        'diskReadIoPpm',
        'diskWriteIoPpm',
    ]


    def performance_statistics(self, metrics, json_list, ext_id):
        output = []
        for json_data in json_list:
            metric_data = {metric: {} for metric in metrics}
            all_timestamps = set()

            for metric in metrics:
                for entry in json_data.get(metric, []):
                    try:
                        ts_obj = datetime.strptime(entry['timestamp'], "%Y-%m-%dT%H:%M:%SZ")
                    except ValueError:
                        ts_obj = datetime.strptime(entry['timestamp'], "%Y-%m-%dT%H:%M:%S.%fZ")
                    metric_data[metric][ts_obj] = entry['value']
                    all_timestamps.add(ts_obj)

            if not all_timestamps:
                continue

            all_timestamps = sorted(all_timestamps)

            for ts in all_timestamps:
                record = {'timestamp': ts.strftime("%Y-%m-%dT%H:%M:%SZ")}
                
                record['extId'] = ext_id

                for metric in metrics:
                    record[metric] = metric_data[metric].get(ts, 0)

                output.append(record)

        return output


    def get_events(self, events, ext_id):
        return self.performance_statistics(metrics=self.metrics, json_list=events, ext_id=ext_id)
    
    def write_events(self, events, url, entity=None, ext_id=None):
        """
        Write collected events into Splunk.
        """
        entity = entity or self.entity
        count = 0
        for item in self.get_events(events, ext_id=ext_id):
            event_error, uploaded = self.create_splunk_event(url, item)
            if event_error:
                self.logger.error(
                    f"Failed to write event for {entity}: {event_error}",
                    exc_info=True,
                )
            elif uploaded:
                count += 1
        self.logger.info(f"Wrote {count} events for {entity}")
        return count

    def fetch_and_write_event(self, ext_id=None, cl_ext_id=None, param=None, entity=None, pagination_limit=None):
        """
        Combined step: collect + write.
        """
        events, url = self.collect_event_data(
            ext_id=ext_id,
            cl_ext_id=cl_ext_id,
            param=param,
            entity=entity,
            pagination_limit=pagination_limit,
        )
        if events:
            return self.write_events(events, url, entity=entity, ext_id=ext_id)
        return 0

    def get_disks_list(self):
        events, _ = self.collect_event_data(
            entity="disks",
            pagination_limit=100,
        )
        return [event['extId'] for event in events]


class VMPerformanceFetcher(BaseFetcher):
    entity = "vm_performance"
    sourcetype = "nutanixpc_vm_performance"
    source = "nutanixpc:pcperformance"
    logger = log.Logs().get_logger("PCPerformance")

    metrics = [
        "controllerAvgIoLatencyMicros",
        "controllerAvgReadIoLatencyMicros",
        "controllerAvgReadIoSizeKb",
        "controllerAvgWriteIoLatencyMicros",
        "controllerAvgWriteIoSizeKb",
        "controllerIoBandwidthKbps",
        "controllerNumIo",
        "controllerNumIops",
        "controllerNumReadIo",
        "controllerNumReadIops",
        "controllerNumWriteIo",
        "controllerNumWriteIops",
        "controllerOplogDrainDestHddBytes",
        "controllerOplogDrainDestSsdBytes",
        "controllerReadIoBandwidthKbps",
        "controllerReadIoPpm",
        "controllerReadSourceEstoreHddLocalBytes",
        "controllerReadSourceEstoreSsdLocalBytes",
        "controllerReadSourceEstoreHddRemoteBytes",
        "controllerReadSourceEstoreSsdRemoteBytes",
        "controllerReadSourceOplogBytes",
        "controllerSharedUsageBytes",
        "controllerSnapshotUsageBytes",
        "controllerStorageTierSsdUsageBytes",
        "controllerTimespanMicros",
        "controllerTotalIoSizeKb",
        "controllerTotalIoTimeMicros",
        "controllerTotalReadIoSizeKb",
        "controllerTotalReadIoTimeMicros",
        "controllerTotalTransformedUsageBytes",
        "controllerUserBytes",
        "controllerWriteDestEstoreSsdBytes",
        "controllerWriteDestEstoreHddBytes",
        "controllerWriteIoBandwidthKbps",
        "controllerWriteIoPpm",
        "controllerWss120SecondUnionMb",
        "controllerWss120SecondReadMb",
        "controllerWss120SecondWriteMb",
        "controllerWss3600SecondUnionMb",
        "controllerWss3600SecondReadMb",
        "controllerWss3600SecondWriteMb",
        "guestMemoryUsagePpm",
        "hypervisorAvgIoLatencyMicros",
        "hypervisorCpuReadyTimePpm",
        "hypervisorCpuUsagePpm",
        "hypervisorIoBandwidthKbps",
        "hypervisorMemoryUsagePpm",
        "hypervisorNumIo",
        "hypervisorNumIops",
        "hypervisorNumReadIops",
        "hypervisorNumReadIo",
        "hypervisorNumReceivedBytes",
        "hypervisorNumReceivePacketsDropped",
        "hypervisorNumTransmittedBytes",
        "hypervisorNumTransmitPacketsDropped",
        "hypervisorNumWriteIo",
        "hypervisorNumWriteIops",
        "hypervisorReadIoBandwidthKbps",
        "hypervisorTimespanMicros",
        "hypervisorTotalIoSizeKb",
        "hypervisorTotalIoTimeMicros",
        "hypervisorTotalReadIoSizeKb",
        "hypervisorVmRunningTimeUsecs",
        "hypervisorWriteIoBandwidthKbps",
        "memoryUsagePpm",
        "numVcpusUsedPpm",
        "diskUsagePpm",
        "diskCapacityBytes"
    ]
    extra_fields = ['extId']

    def performance_statistics(self, metrics, extra_fields, json_list):
        output = []
        extra_fields = ["cluster", "hypervisorType", "memoryReservedBytes", "extId"]

        for json_data in json_list:
            extra_data = {field: json_data.get(field, '') for field in extra_fields}

            for stat in json_data.get("stats", []):
                for field in extra_fields:
                    if field in stat and not extra_data.get(field):
                        extra_data[field] = stat[field]

                if all(extra_data.get(f) for f in extra_fields):
                    break

            for stat in json_data.get("stats", []):
                ts_str = stat.get("timestamp")
                if not ts_str:
                    continue

                for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
                    try:
                        ts_obj = datetime.strptime(ts_str, fmt)
                        break
                    except ValueError:
                        continue
                else:
                    continue

                record = {
                    "timestamp": ts_obj.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    **extra_data,
                    **{metric: stat.get(metric, 0) for metric in metrics}
                }
                output.append(record)
        return output
    
    def get_events(self, events):
        return self.performance_statistics(metrics=self.metrics, extra_fields=self.extra_fields, json_list=events)

    def get_vvms_list(self):
        events, _ = self.collect_event_data(
            entity="vms",
            pagination_limit=100,
        )
        return [event['extId'] for event in events]


class VolumeGroupsStatsFetcher(BaseFetcher):
    entity = "volume_groups_stats"
    sourcetype = "nutanixpc_volume_groups_stats"
    source = "nutanixpc:pcperformance"
    logger = log.Logs().get_logger("PCPerformance")

    def get_volume_groups_data(self):
        events, _ = self.collect_event_data(
            entity="volume-groups",
            pagination_limit=100,
        )
        return [event['extId'] for event in events]