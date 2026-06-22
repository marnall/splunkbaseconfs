import json
from pc_helpers import BaseFetcher
from datetime import datetime, timedelta, timezone
from time import sleep
import splunklib.results as results


class ClustersBaseFetcher(BaseFetcher):
    entity = "clusters"

    def data_exists_in_db(self, data):
        data = json.loads(data)
        extId = data.get("extId")
        vmCount = data.get("vmCount")
        numberOfNodes = data.get("nodes", {}).get("numberOfNodes")
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} extId="{extId}" vmCount={vmCount} nodes.numberOfNodes={numberOfNodes} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "-24h", "latest_time": "now"}

        job = self.service.search(search_query, **kwargs_time_search)
        self.logger.info(search_query)
        return self.get_exists_in_db_result(job)
    
    def manipulate_data(self, item):
        item["pc_ip"] = self.pc_ip
        return json.dumps(item)


class ClustersFetcher(ClustersBaseFetcher):
    sourcetype = "nutanixpc_clusters"

    def validate_dataset(self, dataset):
        filtered_data= [data for data in dataset.get("data") if 'PRISM_CENTRAL' not in data['config']['clusterFunction']] 
        return filtered_data
    

class PrismCentralsFetcher(ClustersBaseFetcher):
    sourcetype = "nutanixpc_prismCentrals"
    
    def validate_dataset(self, dataset):
        filtered_data= [data for data in dataset.get("data") if 'PRISM_CENTRAL' in data['config']['clusterFunction']] 
        return filtered_data


class HostsFetcher(BaseFetcher):
    entity = "hosts"
    sourcetype = "nutanixpc_hosts"

    def data_exists_in_db(self, data):
        data = json.loads(data)
        extId = data.get("extId")
        cpuFrequencyHz = data.get("cpuFrequencyHz")
        memorySizeBytes = data.get("memorySizeBytes")
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} extId="{extId}" cpuFrequencyHz={cpuFrequencyHz} memorySizeBytes={memorySizeBytes} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "-24h", "latest_time": "now"}

        job = self.service.search(search_query, **kwargs_time_search)
        self.logger.info(search_query)
        return self.get_exists_in_db_result(job)


class VMsFetcher(BaseFetcher):
    entity = "vms"
    sourcetype = "nutanixpc_vms"
    pagination_limit = 50

    def data_exists_in_db(self, data):
        data = json.loads(data)
        extId = data.get("extId")
        powerState = data.get("powerState")
        memorySizeBytes = data.get("memorySizeBytes")
        numSockets = data.get("numSockets")
        numCoresPerSocket = data.get("numCoresPerSocket")
        numThreadsPerCore = data.get("numThreadsPerCore")
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} extId="{extId}" powerState={powerState} memorySizeBytes={memorySizeBytes} numSockets={numSockets} numCoresPerSocket={numCoresPerSocket} numThreadsPerCore={numThreadsPerCore} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "-24h", "latest_time": "now"}

        job = self.service.search(search_query, **kwargs_time_search)
        self.logger.info(search_query)
        return self.get_exists_in_db_result(job)


class DisksFetcher(BaseFetcher):
    entity = "disks"
    sourcetype = "nutanixPC_disks"
    pagination_limit = 50

    def data_exists_in_db(self, data):
        data = json.loads(data)
        extId = data.get("extId")
        isOnline = data.get("diskAdvanceConfig", {}).get("isOnline")
        ipv4 = data.get("nodeIpAddress").get("ipv4").get("value")
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} extId="{extId}" diskAdvanceConfig.isOnline={isOnline} nodeIpAddress.ipv4.value={ipv4} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "-24h", "latest_time": "now"}

        job = self.service.search(search_query, **kwargs_time_search)
        self.logger.info(search_query)
        return self.get_exists_in_db_result(job)


class StorageContainersFetcher(BaseFetcher):
    entity = "storage-containers"
    sourcetype = "nutanixpc_storage_containers"

    def data_exists_in_db(self, data):
        data = json.loads(data)
        containerExtId = data.get("containerExtId")
        maxCapacityBytes = data.get("maxCapacityBytes")
        replicationFactor = data.get("replicationFactor")
        isCompressionEnabled = data.get("isCompressionEnabled")
        erasureCode = data.get("erasureCode")
        cacheDeduplication = data.get("cacheDeduplication")
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} containerExtId="{containerExtId}" maxCapacityBytes={maxCapacityBytes} replicationFactor={replicationFactor} isCompressionEnabled={isCompressionEnabled} erasureCode={erasureCode} cacheDeduplication={cacheDeduplication} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "-24h", "latest_time": "now"}

        job = self.service.search(search_query, **kwargs_time_search)
        self.logger.info(search_query)
        return self.get_exists_in_db_result(job)


class VolumeGroupsFetcher(BaseFetcher):
    entity = "volume-groups"
    sourcetype = "nutanixpc_volume_groups"

    def data_exists_in_db(self, data):
        data = json.loads(data)
        extId = data.get("extId")
        usageType = data.get("usageType")
        sharingStatus = data.get("sharingStatus")
        VmAttachments = data.get("shouldLoadBalanceVmAttachments")
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} extId="{extId}" usageType={usageType} sharingStatus={sharingStatus} shouldLoadBalanceVmAttachments={VmAttachments} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "-24h", "latest_time": "now"}

        job = self.service.search(search_query, **kwargs_time_search)
        self.logger.info(search_query)
        return self.get_exists_in_db_result(job)


class FileServersFetcher(BaseFetcher):
    entity = "file-servers"
    sourcetype = "nutanixpc_file_servers"

    def manipulate_data(self, item):
        item["pc_ip"] = self.pc_ip
        return json.dumps(item)
    
    def data_exists_in_db(self, data):
        data = json.loads(data)
        extId = data.get("extId")
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} extId="{extId}" | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "-24h", "latest_time": "now"}

        job = self.service.search(search_query, **kwargs_time_search)
        self.logger.info(search_query)
        return self.get_exists_in_db_result(job)


class AlertsFetcher(BaseFetcher):
    entity = "alerts"
    sourcetype = "nutanixpc_alerts"
    pagination_limit = 100

    def __init__(self, api_processor, ew, input_name, service, interval, pc_ip=None):
        super().__init__(api_processor, ew, input_name, service, pc_ip)
        self.interval = interval

    def manipulate_data(self, item):
        original_message = item.get("message", "")
        original_title = item.get("title", "")
        item["message"] = self.populate_message(
            original_message, item.get("parameters", [])
        )
        item["title"] = self.populate_message(
            original_title, item.get("parameters", [])
        )
        return json.dumps(item)
    
    def data_exists_in_db(self, data):
        if not self.interval:
            return False
        data = json.loads(data)
        lastUpdatedTime = data.get("lastUpdatedTime")
        self.logger.info(f"data_exists_in_db: {lastUpdatedTime}, {self.interval}")

        lastUpdatedTime = datetime.strptime(lastUpdatedTime, "%Y-%m-%dT%H:%M:%S.%fZ")
        lastUpdatedTime = lastUpdatedTime.replace(tzinfo=timezone.utc) 

        now_utc = datetime.now(timezone.utc)
        interval_delta = timedelta(seconds=int(self.interval))

        if lastUpdatedTime >= now_utc - interval_delta:
            return False
        else:
            return True

    def update_interval_if_needed(self, job):
        while not job.is_done():
            sleep(.2)
        rr = results.JSONResultsReader(job.results(output_mode='json'))
        for result in rr:
            if isinstance(result, results.Message):
                self.logger.info(f'{result.type}: {result.message}')
            elif isinstance(result, dict):
                last_utc_time_in_db = int(result["latest_time"]) #1764775830
                now_utc = int(datetime.now(timezone.utc).timestamp())
                diff_seconds = now_utc - last_utc_time_in_db
                if diff_seconds > int(self.interval):
                    self.logger.info(f"Adjusting interval from {self.interval}s to {diff_seconds}s")
                    self.interval = str(diff_seconds)
                else:
                    self.logger.info(f"Interval {self.interval}s is fine (difference: {diff_seconds}s)")

    def update_interval(self):
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "0", "latest_time": "now"}
        job = self.service.search(search_query, **kwargs_time_search)
        if not self.get_exists_in_db_result(job):
            self.interval=None
        #
        self.logger.info(f"update_interval sourcetype {self.sourcetype} not empty")
        #
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} | stats max(_time) as latest_time | table latest_time'
        job = self.service.search(search_query, **kwargs_time_search)
        self.update_interval_if_needed(job)
        
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
        self.update_interval()
        self.logger.info(f"Current interval: {self.interval}")
        if events:
            return self.write_events(events, url, entity=entity)
        return 0


class EventsFetcher(BaseFetcher):
    entity = "events"
    sourcetype = "nutanixpc_events"
    pagination_limit = 100

    def __init__(self, api_processor, ew, input_name, service, interval, pc_ip=None):
        super().__init__(api_processor, ew, input_name, service, pc_ip)
        self.interval = interval

    def manipulate_data(self, item):
        original_message = item.get("message", "")
        item["message"] = self.populate_message(
            original_message, item.get("parameters", [])
        )
        return json.dumps(item)

    def data_exists_in_db(self, data):
        if not self.interval:
            return False
        data = json.loads(data)
        creationTime = data.get("creationTime")
        self.logger.info(f"data_exists_in_db: {creationTime}, {self.interval}")

        creationTime = datetime.strptime(creationTime, "%Y-%m-%dT%H:%M:%S.%fZ")
        creationTime = creationTime.replace(tzinfo=timezone.utc) 

        now_utc = datetime.now(timezone.utc)
        interval_delta = timedelta(seconds=int(self.interval))

        if creationTime >= now_utc - interval_delta:
            return False
        else:
            return True

    def update_interval_if_needed(self, job):
        while not job.is_done():
            sleep(.2)
        rr = results.JSONResultsReader(job.results(output_mode='json'))
        for result in rr:
            if isinstance(result, results.Message):
                self.logger.info(f'{result.type}: {result.message}')
            elif isinstance(result, dict):
                last_utc_time_in_db = int(result["latest_time"]) #1764775830
                now_utc = int(datetime.now(timezone.utc).timestamp())
                diff_seconds = now_utc - last_utc_time_in_db
                if diff_seconds > int(self.interval):
                    self.logger.info(f"Adjusting interval from {self.interval}s to {diff_seconds}s")
                    self.interval = str(diff_seconds)
                else:
                    self.logger.info(f"Interval {self.interval}s is fine (difference: {diff_seconds}s)")

    def update_interval(self):
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} | stats count'
        kwargs_time_search = {"output_mode":"json", "earliest_time": "0", "latest_time": "now"}
        job = self.service.search(search_query, **kwargs_time_search)
        if not self.get_exists_in_db_result(job):
            self.interval=None
        #
        self.logger.info(f"update_interval sourcetype {self.sourcetype} not empty")
        #
        search_query = f'search index="nutanixpc" sourcetype={self.sourcetype} | stats max(_time) as latest_time | table latest_time'
        job = self.service.search(search_query, **kwargs_time_search)
        self.update_interval_if_needed(job)
        
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
        self.update_interval()
        self.logger.info(f"Current interval: {self.interval}")
        if events:
            return self.write_events(events, url, entity=entity)
        return 0


class HostNICsFetcher(BaseFetcher):
    entity = "host_nics"
    sourcetype = "nutanixpc_host_nics"
