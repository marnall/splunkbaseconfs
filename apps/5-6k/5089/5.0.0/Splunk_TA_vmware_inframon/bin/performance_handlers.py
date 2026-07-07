# -*-  indent-tabs-mode:nil;  -*-
# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.
# Core Python Imports
from __future__ import division
import sys
import datetime
import math
import re
import random
# from test_autoeventgen import performance_autogen_data
from splunk import util
from suds import WebFault

# Append SA-Hydra-inframon/bin to the Python path

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))

# Import TA-VMware-inframon collection code

from vim25.performance import PerfCollector
from vim25.vcenter_performance import VCPerfCollector
from vim25.connection import Connection
from vim25 import utils
from vim25 import hostvm_metrics
from vim25.mo import ManagedObjectReference
from vim25.mo import ManagedObject
from vim25.mo import object_content_prop_set
import hydra_inframon
import json
import os
DBG_SUFFIX = ""
SEP = '\t'
HEADER_LIM = 100
NUM_VMS_SINGLE_COLLECTION = 80
# Collect 100 events into single collection
NUM_EVENTS_SINGLE_COLLECTION = 100
# This dictionary will keep mapping of host/vm moid and their datastore moids.
host_vm_ds_map = {}
# The dictionary will keep the inventory data of host required for metrics data
host_dic = {}
# The dictionary will keep the inventory data of vms required for metrics data
vm_dic = {}
# The dictionary will keep the inventory data of cluster required for metrics data
cluster_dic = {}
# Flag to check if IP is missing in any of the vms
ip_missing = False
buf = []
datastore_buf = []
metricstoprune = {
    'host':
        [
            "cpu.average.reservedAllocation.percent",
            "cpu.average.unreservedAllocation.percent",
            "mem.average.reservedAllocation.percent",
            "mem.average.swapped.kiloBytes"
        ],
    'vm':
        [
            "datastore.average.storage_committed.bytes",
            "datastore.average.storage_uncommitted.bytes",
            "datastore.average.storage_used_percent.percent"
        ]
}
# The dictionary will keep the flag for VM storage metrics mentioned in metricstoprune list
metric_allowdeny_flag = {'vm': {}, 'host': {}}
# This boolean variable will indicate whether the "aggregated" instance collection for VM entity is enabled or not
is_vm_aggregated_instance_enabled = True

class BasePerfHandler(hydra_inframon.HydraHandler):
    def _is_entity_excluded(self, e, perf_entity_denylist):
        return any(re.search(x, e) is not None for x in perf_entity_denylist)

    def _prepare_timestamps(self, *args):
        """
        Input: varargs list of datetime objects (assumed UTC).
        Output: UTC datetime(s) corresponding to the server clock that are guaranteed to have
                correct tzinfo field. Outputs single object for a single input argument, a list
                for multiple input arguments.
        """
        results = utils.AddUtcTzinfo(utils.ConvertToServerTime(args, Connection.svcInstance, zone="UTC"))
        return results[0] if len(results) == 1 else results

    def _create_counter_from_id(self, metricid, instanced=False):
        '''
        Takes a single "id" and will return a PerfMetricId with instance set to * or ""

        @metricid = a number referring to the counter id on a vc
        @int
        @instanced = boolean based on if the metric is to be used in instanced level collection
        @bool
        '''
        if bool(instanced):
            return Connection.vim25client.new('PerfMetricId', counterId=metricid, instance="*")
        else:
            return Connection.vim25client.new('PerfMetricId', counterId=metricid, instance="")

    def _merged_host_vm_cache(self, metricscache):
        '''
        takes a metric cache with hostmetrics and vmmetrics set and will return 1 list of dicts with the unique
        counters in both
        '''
        mergedcache = metricscache['hostmetrics']
        for item in metricscache['vmmetrics']:
            if not item in mergedcache:
                mergedcache.append(item)
        return mergedcache

    def _check_format_type(self, format_type):
        '''
            Check if performance performance type, raise exception is not correct.
            @param format_type: specified peformance type in str format

            @return: Exception, if it is not supported format, otherwise None
        '''
        if not format_type in ['csv', 'normal']:
            self.logger.error("[Performance Handler] Specified performance format is incorrect. Specified format type should be either csv or normal.")
            raise Exception("[Performance Handler] Specified performance format is incorrect. Specified format type should be either csv or normal.")

    def _process_timestamps(self, perfdata, format):
        '''
            Get list of timestamps value in %Y-%m-%dT%H:%M:%SZ format of perfdata

            @return list of timestamps in %Y-%m-%dT%H:%M:%SZ format
        '''
        if format == 'csv':
            return perfdata.sampleInfoCSV.split(',')[1::2]
        else:
            timestamps = []
            for sampleInfo in perfdata.sampleInfo:
                # same time format as csv type
                timestamps.append(sampleInfo.timestamp.strftime('%Y-%m-%dT%H:%M:%SZ'))
            return timestamps

    def _prune_entity_allowdeny_list(self, metricstoprune, entity, allowlist, denylist):
        '''
        Flag for metric that match the allowlist AND are not
        in the denylist will be set as True. A blank allowlist will assume that all entries are allowed.
        a blank denylist will assume no entries are denied.
        '''
        global metric_allowdeny_flag
        for metric in metricstoprune[entity]:
            processmetric=True
            if allowlist and denylist:
                #There is a allowlist pattern specified and a denylist pattern
                processmetric=False
                if [regexmatch for regexmatch in allowlist if regexmatch.match(metric)] and not [regexmatch for regexmatch in denylist if regexmatch.match(metric)]:
                    processmetric=True
            elif allowlist and not denylist:
                #There is a allowlist and no denylist
                processmetric=False
                if [regexmatch for regexmatch in allowlist if regexmatch.match(metric)]:
                    processmetric=True
            elif not allowlist and denylist:
                #There is no allowlist and there is a denylist
                if [regexmatch for regexmatch in denylist if regexmatch.match(metric)]:
                    processmetric=False
            metric_allowdeny_flag[entity][metric] = processmetric

    def _get_host_inventory_data(self, entity_name, host_mor):
        """
            Make the inventory calls required for the metrics data

            Input: the moid of the host

            Output: Stores the result in the global dictionaries
        """

        host_required_properties = {"name": "name", "summary.config.product.osType": "os", "summary.config.product.version": "os_version"}
        global host_vm_ds_map
        global host_dic
        host_dic[entity_name] = {}
        try:
            host_mo = Connection.vim25client.createExactManagedObject(host_mor)
        except Exception as e:
            self.logger.warn("Unable to get managed object of entity : {}".format(entity_name))
            return
        try:
            uuid = host_mo.getCurrentProperty("hardware.systemInfo.uuid")
            host_dic[entity_name]['uuid'] = uuid
        except Exception as e:
            self.logger.warn("Configuration of hostsystem - uuid: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            objContent = host_mo.retrieveObjectProperties(list(host_required_properties))
            _ps = object_content_prop_set(objContent)
            if objContent != None and _ps != None and len(_ps) > 0:
                for dynaprops in _ps:
                    host_dic[entity_name][host_required_properties[dynaprops.name]] = dynaprops.val
        except Exception as e:
            self.logger.warn("Configuration of hostsystem - name: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            cluster_id = host_mo.getCurrentProperty("parent")
            if(cluster_id._type == 'ClusterComputeResource'):
                    host_dic[entity_name]['parent'] = str(cluster_id.value)
                    try:
                        if cluster_id.value not in cluster_dic:
                            cluster_mor = ManagedObjectReference(value=cluster_id.value, _type="ClusterComputeResource")
                            cluster_mo = Connection.vim25client.createExactManagedObject(cluster_mor)
                            host_dic[entity_name]['cluster_name'] = cluster_mo.getCurrentProperty("name")
                            cluster_dic[cluster_id.value] = host_dic[entity_name]['cluster_name']
                    except Exception as e:
                        self.logger.warn("Configuration of hostsystem - cluster name: {0} is not available, Error: {1}.".format(entity_name, e))
        except Exception as e:
            self.logger.warn("Configuration of hostsystem - cluster: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            vnic = host_mo.getCurrentProperty("config.network.vnic")
            host_dic[entity_name]['ip'] = ','.join(str(i['spec']['ip']['ipAddress']) for i in vnic.HostVirtualNic)
        except Exception as e:
            self.logger.warn("Configuration of hostsystem - ip: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            if entity_name not in host_vm_ds_map:
                if host_mo == None:
                    host_mor = ManagedObjectReference(value=entity_name, _type="HostSystem")
                    host_mo = Connection.vim25client.createExactManagedObject(host_mor)
                host_ds_moid_list = []
                datastore_mor_list = host_mo.getCurrentProperty("datastore")
                for datastore_mor in datastore_mor_list.ManagedObjectReference:
                    host_ds_moid_list.append(datastore_mor.value)
                host_vm_ds_map[entity_name] = host_ds_moid_list
                host_dic[entity_name]['datastore'] = ','.join(host_ds_moid_list)
        except Exception as e:
            self.logger.warn("Configuration of hostsystem like reference to datastore object : {0} is not available, Error: {1}.".format(entity_name, e))

    def _get_vm_inventory_data(self, entity_name, vm_mor, host_moid):
        """
            Make the inventory calls required for the metrics data

            Input: the moid of the VM, moid of the host.

            Output: Stores the result in the global dictionaries
        """
        vm_required_properties = {"name": "name", "config.guestFullName": "os"}
        global host_dic
        global ip_missing
        global vm_dic
        global cluster_dic
        global metric_allowdeny_flag
        vm_dic[entity_name] = {}
        try:
            vm_mo = Connection.vim25client.createExactManagedObject(vm_mor)
        except Exception as e:
            self.logger.warn("Unable to get managed object of entity : {}".format(entity_name))
            return
        try:
            uuid = vm_mo.getCurrentProperty("config.instanceUuid")
            vm_dic[entity_name]['uuid'] = uuid
        except Exception as e:
            self.logger.warn("Configuration of virtual machine: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            objContent = vm_mo.retrieveObjectProperties(list(vm_required_properties))
            _ps = object_content_prop_set(objContent)
            if objContent != None and _ps != None and len(_ps) > 0:

                for dynaprops in _ps:
                    vm_dic[entity_name][vm_required_properties[dynaprops.name]] = dynaprops.val
                match= re.match('.*?\s(\d.*)?\s\(', vm_dic[entity_name]['os'])
                if match:
                    vm_dic[entity_name]['os_version'] = match.group(1)
        except Exception as e:
            self.logger.warn("Configuration of virtual machine - name: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            vm_ds_moid_list = []
            datastore_mor_list = vm_mo.getCurrentProperty("datastore")
            for datastore_mor in datastore_mor_list.ManagedObjectReference:
                vm_ds_moid_list.append(datastore_mor.value)
            vm_dic[entity_name]['datastore'] = ','.join(vm_ds_moid_list)
        except Exception as e:
            self.logger.warn("Configuration of virtual machine like reference to datastore object : {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            resourcepool_mor = vm_mo.getCurrentProperty("resourcePool")
            vm_dic[entity_name]['resourcepool'] = resourcepool_mor.value
        except Exception as e:
            self.logger.warn("Configuration of virtual machine like reference to resourcePool object : {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            objContent = vm_mo.retrieveObjectProperties(["summary.guest.ipAddress"])
            _ps = object_content_prop_set(objContent)
            if objContent != None and _ps != None and len(_ps) > 0:
                for dynaprops in _ps:
                    vm_dic[entity_name]['ip'] = dynaprops.val
            else:
                ip_missing = True
        except Exception as e:
            ip_missing = True
            self.logger.warn("Configuration of virtual machine - ip: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            if host_dic.get(host_moid, None):
                vm_dic[entity_name]['hypervisor_name'] = host_dic[host_moid].get('name', None)
        except Exception as e:
            self.logger.warn("Configuration of virtual machine - hypervisorname: {0} is not available, Error: {1}.".format(entity_name, e))
        try:
            if host_dic.get(host_moid, None):
                vm_dic[entity_name]['cluster'] = host_dic[host_moid].get('parent', None)
                if vm_dic[entity_name]['cluster']:
                    vm_dic[entity_name]['cluster_name'] = cluster_dic.get(vm_dic[entity_name]['cluster'], None)
        except Exception as e:
            self.logger.warn("Configuration of virtual machine - cluster: {0} is not available, Error: {1}.".format(entity_name, e))
        # The metrics are only used from dictionary and indexed if aggregated instance is enabled for VM entity
        if is_vm_aggregated_instance_enabled:
            try:
                committed = None
                uncommitted = None
                if metric_allowdeny_flag['vm']['datastore.average.storage_committed.bytes']:
                    committed = vm_mo.getCurrentProperty("summary.storage.committed")
                    vm_dic[entity_name]['storage_committed'] = committed
                if metric_allowdeny_flag['vm']['datastore.average.storage_uncommitted.bytes']:
                    uncommitted = vm_mo.getCurrentProperty("summary.storage.uncommitted")
                    vm_dic[entity_name]['storage_uncommitted'] = uncommitted
                if metric_allowdeny_flag['vm']['datastore.average.storage_used_percent.percent'] and committed is not None and uncommitted is not None:
                    vm_dic[entity_name]['storage_used_percent'] = (committed/(committed+uncommitted))*100
            except Exception as e:
                self.logger.warn("Storage details of virtual machine: {0} is not available, Error: {1}.".format(entity_name, e))


    def _process_perf_data(self, perfdata_array, format, host_moid, config):
        """
        @param perfdata_array: Performance data in raw format
        @param format: Define perfdata format type. Possible values for this: 'csv' or 'normal'

        Table keys are formed by the (timestamp, group, entity_type) tuples.
        For each table key, the entries include moid, counter instance, and a list of metrics;
        this information is stored in a nested dictionary.

        Expects that metric cache has been set on the handler.
        """

        res = {}
        required_fields = ["cpu.average.reservedCapacity.megaHertz", "cpu.average.totalCapacity.megaHertz", "mem.average.reservedCapacity.megaBytes", "mem.average.totalCapacity.megaBytes", "mem.average.swapin.kiloBytes", "mem.average.swapout.kiloBytes"]
        global ip_missing
        global buf
        global vm_dic
        global is_vm_aggregated_instance_enabled
        buf = []
        host_metrics_dict = {}
        metrics_method = self._prepare_host_metrics_data
        host_instance_denylist = [re.compile(x) for x in config['host_instance_denylist']]
        host_instance_allowlist = [re.compile(x) for x in config['host_instance_allowlist']]
        vm_instance_denylist = [re.compile(x) for x in config['vm_instance_denylist']]
        vm_instance_allowlist = [re.compile(x) for x in config['vm_instance_allowlist']]
        for perfdata in perfdata_array: # entities
            if (format == 'csv' and perfdata.sampleInfoCSV is None) or (format == 'normal' and perfdata.sampleInfo is None):
                self.logger.debug("[Performance Handler] Missing sample info for entity=%s of type=%s, skipping record",
                    perfdata.entity.value, perfdata.entity._type)
                continue
            mergedcache = self._merged_host_vm_cache(self.metricscache)
            timestamps = self._process_timestamps(perfdata, format)
            for pmser in perfdata.value: # counters (group, instance, name)
                processmetric=True
                if format == 'csv':
                    data_values = list(map(int, pmser.value.split(',')))
                else:
                    # normal format type has value in array format
                    data_values = pmser.value
                pc = pmser.id.counterId
                fqname, group, indexing_name, rollup, unit = [(x['name'], x['group'], x['indexing_name'], x['vmware_metric_aggregation'], x['unit']) for x in mergedcache if x['id']==pc][0]
                #group = pc.groupInfo.key
                entity_name = perfdata.entity.value
                # instance value of None or "" means this is an aggregated metric
                inst = pmser.id.instance if pmser.id.instance else "aggregated"
                # need to add logic to process the instance allowlist / denylist
                if entity_name.startswith("host"):
                    metrics_method = self._prepare_host_metrics_data
                    # check if there is no allowlist but a denylist, if so, process everything that's not on the denylist
                    if not host_instance_allowlist and host_instance_denylist:
                        if [regexmatch for regexmatch in host_instance_denylist if regexmatch.match(inst)]:
                            processmetric=False
                    # check if there is no denylist but an allowlist, if so, process everything that's only in the allowlist
                    elif host_instance_allowlist and not host_instance_denylist:
                        processmetric=False
                        if [regexmatch for regexmatch in host_instance_allowlist if regexmatch.match(inst)]:
                            processmetric=True
                    # there is both a allowlist and denylist, process the items only in the allowlist and exclude the ones in the denylist
                    elif host_instance_allowlist and host_instance_denylist:
                        processmetric=False
                        if [regexmatch for regexmatch in host_instance_allowlist if regexmatch.match(inst)] and not [regexmatch for regexmatch in host_instance_denylist if regexmatch.match(inst)]:
                            processmetric=True
                    if fqname in required_fields and processmetric:
                        host_metrics_dict[fqname] = {'data_values' : data_values, 'timestamps' : timestamps, 'perfdata_entity' : perfdata.entity, 'group' : group}
                elif entity_name.startswith("vm"):
                    metrics_method = self._prepare_vm_metrics_data
                    # check if there is no allowlist but a denylist, if so, process everything that's not on the denylist
                    if not vm_instance_allowlist and vm_instance_denylist:
                        if [regexmatch for regexmatch in vm_instance_denylist if regexmatch.match(inst)]:
                            processmetric=False
                    # check if there is no denylist but a allowlist, if so, process everything that's only in the allowlist
                    elif vm_instance_allowlist and not vm_instance_denylist:
                        processmetric=False
                        if [regexmatch for regexmatch in vm_instance_allowlist if regexmatch.match(inst)]:
                            processmetric=True
                    # there is both a allowlist and denylist, process the items only in the allowlist and exclude the ones in the denylist
                    elif vm_instance_allowlist and vm_instance_denylist:
                        processmetric=False
                        if [regexmatch for regexmatch in vm_instance_allowlist if regexmatch.match(inst)] and not [regexmatch for regexmatch in vm_instance_denylist if regexmatch.match(inst)]:
                            processmetric=True
                if processmetric:
                    # values labeled percent are actually in units of % * 100, so must convert
                    data_values = [float(x) / 100 if fqname.endswith("percent") else x for x in data_values]
                    metrics_method(res=res, indexing_name=indexing_name, timestamps=timestamps, group=group, type=perfdata.entity._type, entity_name=entity_name, inst=inst, data=data_values, host_moid=host_moid, rollup=rollup, unit=unit)
                else:
                    self.logger.debug("[Performance Handler] {task} Current instance ("+inst+") does not meet allowlist/denylist and will be ignored.")

        # Calculate fields using default metrics
        if 'cpu.average.reservedCapacity.megaHertz' in host_metrics_dict.keys() and 'cpu.average.totalCapacity.megaHertz' in host_metrics_dict.keys():
            timestamps = host_metrics_dict['cpu.average.reservedCapacity.megaHertz']['timestamps']
            group = host_metrics_dict['cpu.average.reservedCapacity.megaHertz']['group']
            perfdata_entity = host_metrics_dict['cpu.average.reservedCapacity.megaHertz']['perfdata_entity']

            if metric_allowdeny_flag['host'].get('cpu.average.reservedAllocation.percent', False):
                reserved_perc_data_values = [round((float(host_metrics_dict['cpu.average.reservedCapacity.megaHertz']['data_values'][i])/float(host_metrics_dict['cpu.average.totalCapacity.megaHertz']['data_values'][i]))*100, 2) for i in range(len(timestamps))]
                self._prepare_host_metrics_data(indexing_name="cpu.reservedAllocation", timestamps=timestamps, group=group, type=perfdata_entity._type, entity_name=perfdata_entity.value, inst="aggregated", data=reserved_perc_data_values, host_moid=host_moid, rollup="average", unit="percent")

            if metric_allowdeny_flag['host'].get('cpu.average.unreservedAllocation.percent', False):
                unreserved_perc_data_values = [round(((float(host_metrics_dict['cpu.average.totalCapacity.megaHertz']['data_values'][i]) - float(host_metrics_dict['cpu.average.reservedCapacity.megaHertz']['data_values'][i]))/float(host_metrics_dict['cpu.average.totalCapacity.megaHertz']['data_values'][i]))*100, 2) for i in range(len(timestamps))]
                self._prepare_host_metrics_data(indexing_name="cpu.unreservedAllocation", timestamps=timestamps, group=group, type=perfdata_entity._type, entity_name=perfdata_entity.value, inst="aggregated", data=unreserved_perc_data_values, host_moid=host_moid, rollup="average", unit="percent")

        if metric_allowdeny_flag['host'].get('mem.average.reservedAllocation.percent', False) and 'mem.average.reservedCapacity.megaBytes' in host_metrics_dict.keys() and 'mem.average.totalCapacity.megaBytes' in host_metrics_dict.keys():
            timestamps = host_metrics_dict['mem.average.reservedCapacity.megaBytes']['timestamps']
            group = host_metrics_dict['mem.average.reservedCapacity.megaBytes']['group']
            perfdata_entity = host_metrics_dict['mem.average.reservedCapacity.megaBytes']['perfdata_entity']

            reserved_perc_data_values = [round((float(host_metrics_dict['mem.average.reservedCapacity.megaBytes']['data_values'][i])/float(host_metrics_dict['mem.average.totalCapacity.megaBytes']['data_values'][i]))*100, 2) for i in range(len(timestamps))]
            self._prepare_host_metrics_data(indexing_name="mem.reservedAllocation", timestamps=timestamps, group=group, type=perfdata_entity._type, entity_name=perfdata_entity.value, inst="aggregated", data=reserved_perc_data_values, host_moid=host_moid, rollup="average", unit="percent")

        if metric_allowdeny_flag['host'].get('mem.average.swapped.kiloBytes', False) and 'mem.average.swapin.kiloBytes' in host_metrics_dict.keys() and 'mem.average.swapout.kiloBytes' in host_metrics_dict.keys():
            timestamps = host_metrics_dict['mem.average.swapin.kiloBytes']['timestamps']
            group = host_metrics_dict['mem.average.swapin.kiloBytes']['group']
            perfdata_entity = host_metrics_dict['mem.average.swapin.kiloBytes']['perfdata_entity']

            swapped_kiloBytes_data_values = [host_metrics_dict['mem.average.swapin.kiloBytes']['data_values'][i]+host_metrics_dict['mem.average.swapout.kiloBytes']['data_values'][i] for i in range(len(timestamps))]
            self._prepare_host_metrics_data(indexing_name="mem.swapped", timestamps=timestamps, group=group, type=perfdata_entity._type, entity_name=perfdata_entity.value, inst="aggregated", data=swapped_kiloBytes_data_values, host_moid=host_moid, rollup="average", unit="kiloBytes")

        if is_vm_aggregated_instance_enabled:
            for entity_name in vm_dic.keys():
                if('storage_committed' in vm_dic[entity_name]):
                    self._prepare_vm_metrics_data(indexing_name="datastore.storage_committed", timestamps=[self.storage_collection_time], group="datastore", entity_name=entity_name, inst="aggregated", data=[vm_dic[entity_name]['storage_committed']], host_moid=host_moid, rollup="average", unit="bytes")

                if('storage_uncommitted' in vm_dic[entity_name]):
                    self._prepare_vm_metrics_data(indexing_name="datastore.storage_uncommitted", timestamps=[self.storage_collection_time], group="datastore", entity_name=entity_name, inst="aggregated", data=[vm_dic[entity_name]['storage_uncommitted']], host_moid=host_moid, rollup="average", unit="bytes")

                if('storage_used_percent' in vm_dic[entity_name]):
                    self._prepare_vm_metrics_data(indexing_name="datastore.storage_used_percent", timestamps=[self.storage_collection_time], group="datastore", entity_name=entity_name, inst="aggregated", data=[vm_dic[entity_name]['storage_used_percent']], host_moid=host_moid, rollup="average", unit="percent")

        if len(buf) > 0:
            num_collections = int(math.ceil(len(buf) / float(NUM_EVENTS_SINGLE_COLLECTION)))
            for i in range(num_collections):
                self.output.sendChunkData(buf[i * NUM_EVENTS_SINGLE_COLLECTION: (i+1) * NUM_EVENTS_SINGLE_COLLECTION], host=Connection.domain, index=self.dest_index)
        if ip_missing:
            self.logger.warn("[Performance Handler] Some of the vms may not have their IP property set.")

    def _prepare_vm_metrics_data(self, **kwargs):
        """
        Parses VM Performance data for metrics index and make the required inventory calls for vms

        Creates a buf(event) and writes the data to stdout in json format
        """

        timestamps = kwargs['timestamps']
        indexing_name = 'vsphere.vm.{metric_name}'.format(metric_name=kwargs['indexing_name'])
        entity_name = kwargs['entity_name']
        inst = kwargs['inst']
        data_values = kwargs['data']
        group = kwargs['group']
        host_moid = kwargs['host_moid']
        sourcetype = 'vmware_inframon:perf:{group}'.format(group=group)
        rollup = kwargs['rollup']
        unit = kwargs['unit']
        global buf

        for tsi in range(len(timestamps)): # times
            # timestamps are returned as UTC: 2013-04-01T23:06:00Z
            ts = timestamps[tsi]
            data = {'_time': utils.ConvertIsoUtcDate(ts), 'metric_name': indexing_name, 'value': data_values[tsi], 'uuid': vm_dic[entity_name].get('uuid', None), 'moid': entity_name, 'instance': inst, 'name': vm_dic[entity_name].get('name', None), 'os': vm_dic[entity_name].get('os', None), 'hypervisor': host_moid, 'hypervisor_name': vm_dic[entity_name].get('hypervisor_name', None), 'cluster': vm_dic[entity_name].get('cluster', None), 'resourcepool': vm_dic[entity_name].get('resourcepool', None), 'entity_type': 'vsphere.vm', 'os_version': vm_dic[entity_name].get('os_version', None), 'ip': vm_dic[entity_name].get('ip', None), 'cluster_name': vm_dic[entity_name].get('cluster_name', None), 'vcenter': Connection.domain, 'pool_name': self.pool_name, 'source': 'VMPerf:VirtualMachine', 'sourcetype': sourcetype, 'vmware_metric_aggregation': rollup, 'unit': unit}
            if group == 'datastore':
                if inst == "aggregated":
                    data.update({'datastore': vm_dic[entity_name].get('datastore', None), 'datastore_name': 'Aggregated'})
                else:
                    ds_info = self.ds_info_by_uuid.get(inst, (None, None))
                    data.update({'datastore': ds_info[0], 'datastore_name': ds_info[1]})
            buf.append(data)

            # Uncomment the following lines if you want to generate dummy events using autoeventgen (large scale testing purpose only)
            '''
            auto_generatedids = self.runtime_adapter.get_cache("autogenertedid:" + Connection.domain)
            if auto_generatedids is None:
                self.logger.error("[autoeventgen] Could not find out generated ids in the runtime cache")
            else:
                performance_autogen_data(auto_generatedids=auto_generatedids, output=self.output, data=data,
                                         itr_len=len(vm_dic)+1, entity_type="VirtualMachine", index=self.dest_index)
            '''

    def _prepare_host_metrics_data(self, **kwargs):
        """
        Parses host Performance data for metrics index

        Creates a buf(event) and writes the data to stdout in json format
        """

        timestamps = kwargs['timestamps']
        indexing_name = 'vsphere.esxihost.{metric_name}'.format(metric_name=kwargs['indexing_name'])
        entity_name = kwargs['entity_name']
        inst = kwargs['inst']
        data_values = kwargs['data']
        group = kwargs['group']
        sourcetype = 'vmware_inframon:perf:{group}'.format(group=group)
        rollup = kwargs['rollup']
        unit = kwargs['unit']
        global host_dic
        global cluster_dic
        global buf

        for tsi in range(len(timestamps)):
            ts = timestamps[tsi]
            data = {'_time': utils.ConvertIsoUtcDate(ts), 'metric_name': indexing_name, 'value': data_values[tsi], 'uuid': host_dic[entity_name].get('uuid', None), 'moid': entity_name, 'instance': inst, 'name': host_dic[entity_name].get('name', None), 'os': host_dic[entity_name].get('os', None), 'os_version': host_dic[entity_name].get('os_version', None), 'cluster': host_dic[entity_name].get('parent', None), 'ip': host_dic[entity_name].get('ip', None), 'cluster_name': cluster_dic.get(host_dic[entity_name].get('parent', None), None), 'entity_type': 'vsphere.esxihost', 'vcenter': Connection.domain, 'pool_name': self.pool_name, 'source': 'VMPerf:HostSystem', 'sourcetype': sourcetype, 'vmware_metric_aggregation': rollup, 'unit': unit}
            if group == 'datastore':
                if inst == "aggregated":
                    data.update({'datastore': host_dic[entity_name].get('datastore', None), 'datastore_name': 'Aggregated'})
                else:
                    ds_info = self.ds_info_by_uuid.get(inst, (None, None))
                    data.update({'datastore': ds_info[0], 'datastore_name': ds_info[1]})
            buf.append(data)

            # Uncomment the following lines if you want to generate dummy events using autoeventgen (large scale testing purpose only)
            '''
            auto_generatedids = self.runtime_adapter.get_cache("autogenertedid:" + Connection.domain)
            if auto_generatedids is None:
                self.logger.error("[autoeventgen] Could not find out generated ids in the runtime cache")
            else:
                performance_autogen_data(auto_generatedids=auto_generatedids, output=self.output, data=data,
                                         itr_len=len(vm_dic)+1, entity_type="HostSystem", index=self.dest_index)
            '''

    def _is_vm_aggregated_instance_collection_enabled(self, config_vm_instance_allowlist, config_vm_instance_denylist):
        """
        Based on the VM instance configuration parameters, it sets the value of global variable.
        The value is True when the "aggregated" instance collection for VM entity is enabled and
        False when the "aggregated" instance collection for VM entity is not enabled
        :config_vm_instance_allowlist: User's vm_instance_allowlist configuration of the vCenter server
        :config_vm_instance_denylist: User's vm_instance_denylist configuration of the vCenter server
        """
        global is_vm_aggregated_instance_enabled
        vm_instance_denylist = [re.compile(x) for x in config_vm_instance_denylist]
        vm_instance_allowlist = [re.compile(x) for x in config_vm_instance_allowlist]
        inst = "aggregated"
        if not vm_instance_allowlist and vm_instance_denylist:
            if [regexmatch for regexmatch in vm_instance_denylist if regexmatch.match(inst)]:
                is_vm_aggregated_instance_enabled=False
        # check if there is no denylist but a allowlist, if so, process everything that's only in the allowlist
        elif vm_instance_allowlist and not vm_instance_denylist:
            is_vm_aggregated_instance_enabled=False
            if [regexmatch for regexmatch in vm_instance_allowlist if regexmatch.match(inst)]:
                is_vm_aggregated_instance_enabled=True
        # there is both a allowlist and denylist, process the items only in the allowlist and exclude the ones in the denylist
        elif vm_instance_allowlist and vm_instance_denylist:
            is_vm_aggregated_instance_enabled=False
            if [regexmatch for regexmatch in vm_instance_allowlist if regexmatch.match(inst)] and not [regexmatch for regexmatch in vm_instance_denylist if regexmatch.match(inst)]:
                is_vm_aggregated_instance_enabled=True

    def _prepare_datastore_metrics_data(self, **kwargs):
        """
        Parses datastore Performance data for metrics index
        Creates a datastore_buf(event) and writes the data to stdout in json format
        """
        global datastore_buf
        timestamp = kwargs['timestamp']
        indexing_name = 'vsphere.datastore.{metric_name}'.format(metric_name=kwargs['metric_name'])
        entity_name = kwargs['entity_name']
        name = kwargs['name']
        data_values = kwargs['data']
        group = kwargs['group']
        sourcetype = 'vmware_inframon:perf:{group}'.format(group=group)
        unit = kwargs['unit']
        data = {
            '_time': timestamp,
            'metric_name': indexing_name,
            'value': data_values,
            'moid': entity_name,
            'name': name,
            'entity_type': 'vsphere.datastore',
            'vcenter': Connection.domain,
            'pool_name': self.pool_name,
            'source': 'VMPerf:Datastore',
            'sourcetype': sourcetype,
            'unit': unit
        }
        datastore_buf.append(data)

class HostVMPerfHandler(BasePerfHandler):
    """
    Handler for running host/vm perf collection
    Quasi-real-time, 20-second performance samples are collected from host systems and VMs;
    """
    # all functionality currently captured by the base handler
    def run(self, session, config, create_time, last_time):
        """
        create_time - the time this task was created/scheduled to run (datetime object)
        last_time - the last time this task was created/scheduler to run (datetime object)
        RETURNS True if successful, False otherwise
        """

        try:
            self.pool_name = config.get("pool_name", None)
            self.dest_index = config.get("perf_index", None)
            entity_metric_allow_deny_list = {
                'vm_metric_allowlist': config.get("vm_metric_allowlist", []),
                'vm_metric_denylist': config.get("vm_metric_denylist", []),
                'host_metric_allowlist': config.get("host_metric_allowlist", []),
                'host_metric_denylist': config.get("host_metric_denylist", []),
            }
            # grab an existing cache if it already exists
            self.metricscachedict = self.runtime_adapter.get_cache(Connection.domain+':hostvmperf:metrics')
            if self.metricscachedict:
                self.metricscache = self.metricscachedict.get('metric_cache', None)
                self.entity_metric_allow_deny_list_cache = self.metricscachedict.get('entity_metric_allow_deny_list_cache', {})
                if not entity_metric_allow_deny_list == self.entity_metric_allow_deny_list_cache:
                    self.logger.debug("[Performance Handler] Found different metric allow/deny lists, blowing caches away.")
                    self.metricscache = None
            else:
                self.metricscache = None

            # Grab the hierarchy from runtime cache.
            target_host_cache = "perfhierarchy:"+Connection.domain+":"+config['perf_target_hosts'][0]
            self.vms_on_host = self.runtime_adapter.get_cache(target_host_cache)
            target_dsinfo_cache = "dsinfo:"+Connection.domain
            self.ds_info_by_uuid = self.runtime_adapter.get_cache(target_dsinfo_cache)
            if not self.ds_info_by_uuid:
                    self.logger.info("[Performance Handler] {task} No datastore uuid-info mapping in dsinfo cache. Cache Target: {target}".format(task=config['perf_collection_type'], target=target_dsinfo_cache))
                    self.ds_info_by_uuid = {}
            if not self.vms_on_host:
                    self.logger.info("[Performance Handler] {task} No hierarchy with vm's in hierarchy cache. Cache Target: {target}".format(task=config['perf_collection_type'], target=target_host_cache))
                    self.logger.info("[Performance Handler] {task} Running collection on host only.".format(task=config['perf_collection_type']))
            # check if cache was returned valid
            if not self.metricscache:
                # Couldn't find metrics, need to populate the cache
                if not self.vms_on_host:
                    self.logger.info("[Performance Handler] {task} Running metrics cache creation without vms.  This will need to be updated once a host is processed with vms.".format(task=config['perf_collection_type']))
                    self.metricscache = hostvm_metrics.MetricsCache(hostmoid=config["perf_target_hosts"][0], vmmoid=[], host_metric_allow_list=entity_metric_allow_deny_list['host_metric_allowlist'], host_metric_deny_list=entity_metric_allow_deny_list['host_metric_denylist']).fullcounters
                else:
                    self.metricscache = hostvm_metrics.MetricsCache(hostmoid=config["perf_target_hosts"][0], vmmoid=self.vms_on_host[config["perf_target_hosts"][0]], vm_metric_allow_list=entity_metric_allow_deny_list['vm_metric_allowlist'], vm_metric_deny_list=entity_metric_allow_deny_list['vm_metric_denylist'], host_metric_allow_list=entity_metric_allow_deny_list['host_metric_allowlist'], host_metric_deny_list=entity_metric_allow_deny_list['host_metric_denylist']).fullcounters
                if self.metricscache:
                    metric_dict = {"metric_cache" : self.metricscache, "entity_metric_allow_deny_list_cache" : entity_metric_allow_deny_list}
                    set_cache_returncode = self.runtime_adapter.set_cache(name=Connection.domain+':hostvmperf:metrics', value=metric_dict, expiration=172800)
                    if set_cache_returncode != 200:
                        self.logger.error("[Performance Handler] {task} Failed updating metrics cache raising an exception.")
                        return False
                else:
                    self.logger.error("[Performance Handler] {task} There was an error returning metrics from the vc for the selected host ( vc={vc} target_host={host} ).".format(task=config['perf_collection_type'], vc=Connection.domain, host=config["perf_target_hosts"][0]))
                    return False

            if not self.metricscache['vmmetrics'] and self.vms_on_host:
                self.logger.error("[Performance Handler] {task} Metrics cache is missing vmmetrics and this host has active vms.  Updating cache.".format(task=config['perf_collection_type']))
                self.metricscache = hostvm_metrics.MetricsCache(hostmoid=config["perf_target_hosts"][0], vmmoid=self.vms_on_host[config["perf_target_hosts"][0]], vm_metric_allow_list=entity_metric_allow_deny_list['vm_metric_allowlist'], vm_metric_deny_list=entity_metric_allow_deny_list['vm_metric_denylist'], host_metric_allow_list=entity_metric_allow_deny_list['host_metric_allowlist'], host_metric_deny_list=entity_metric_allow_deny_list['host_metric_denylist']).fullcounters
                if self.metricscache:
                    metric_dict = {"metric_cache" : self.metricscache, "entity_metric_allow_deny_list_cache" : entity_metric_allow_deny_list}
                    set_cache_returncode = self.runtime_adapter.set_cache(name=Connection.domain+':hostvmperf:metrics', value=metric_dict, expiration=172800)
                    if set_cache_returncode != 200:
                        self.logger.error("[Performance Handler] {task} Failed updating metrics cache raising an exception.")
                        return False
                else:
                    self.logger.error("[Performance Handler] {task} There was an error returning metrics from the vc for the selected host ( vc={vc} target_host={host} ).".format(task=config['perf_collection_type'], vc=Connection.domain, host=config["perf_target_hosts"][0]))
                    return False
            # grab the real times for collection from the vc
            start_time, end_time = self._prepare_timestamps(last_time, create_time)
            self.storage_collection_time = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            self.logger.debug("[Performance Handler] {task} Converting (last_time, create_time) to server time; location=handler_args_server_clock start_time={s} end_time={e}".format(task=config['perf_collection_type'], s=start_time, e=end_time))
            # setup different collection time checks in-case 0 second span passed for first run.
            if end_time - start_time < datetime.timedelta(seconds=1):
                start_time = end_time - datetime.timedelta(seconds=1)
            entities = []
            # get format type (default 'csv')
            format_type = config.get('perf_format_type', 'csv')
            self._check_format_type(format_type)
            #Create MOR for the host
            #Check if host systems are excluded, if not, add them to the collection.
            #This next part is going to look like a rip off of _query_perf, but it should exist in the handler
            for host_moid in config['perf_target_hosts']:
                if not self._is_entity_excluded('HostSystem', config['perf_entity_denylist']) and self.metricscache['hostmetrics']:
                    host_allowlist = [re.compile(x) for x in entity_metric_allow_deny_list['host_metric_allowlist']]
                    host_denylist = [re.compile(x) for x in entity_metric_allow_deny_list['host_metric_denylist']]
                    self._prune_entity_allowdeny_list(metricstoprune, 'host', host_allowlist, host_denylist)
                    #runs through the metric cache and builds metric objects based on the correct instance.
                    host_mor = ManagedObjectReference(value=host_moid, _type="HostSystem")
                    self._get_host_inventory_data(host_moid, host_mor)
                    self.logger.debug("[Performance Handler] Successfully get inventory data for host: {0}".format(host_moid))
                    metrics=[]
                    if config["host_instance_allowlist"] or config["host_instance_denylist"]:
                        metrics=[self._create_counter_from_id(metric['id'], instanced=True) for metric in self.metricscache['hostmetrics']]
                    else:
                        for metric in self.metricscache['hostmetrics']:
                            if metric['group'] == 'datastore':
                                metrics.append(self._create_counter_from_id(metric['id'], instanced=True))
                            else:
                                metrics.append(self._create_counter_from_id(metric['id']))
                    queryspec = Connection.vim25client.new('PerfQuerySpec', entity=host_mor, metricId=metrics, format=format_type, intervalId=self.metricscache['hostrefreshrate'], startTime=start_time, endTime=end_time)
                    #queryspec built for the current host, adding it to the collection cycle
                    entities.append(queryspec)
                #Now find the vm's
                if self.vms_on_host and not self._is_entity_excluded('VirtualMachine', config['perf_entity_denylist']) and self.metricscache['vmmetrics']:
                    vmallowlist = [re.compile(x) for x in entity_metric_allow_deny_list['vm_metric_allowlist']]
                    vmdenylist = [re.compile(x) for x in entity_metric_allow_deny_list['vm_metric_denylist']]
                    self._prune_entity_allowdeny_list(metricstoprune, 'vm', vmallowlist, vmdenylist)
                    # Check and set the global variable that will be used to decide whether to index storage metrics or not
                    self._is_vm_aggregated_instance_collection_enabled(config["vm_instance_allowlist"], config["vm_instance_denylist"])
                    for vm_moid in self.vms_on_host[host_moid]:
                        #runs through the metric cache and builds metric objects based on the correct instance.
                        vm_mor = ManagedObjectReference(value=vm_moid, _type="VirtualMachine")
                        self._get_vm_inventory_data(vm_moid, vm_mor, host_moid)
                        self.logger.debug("[Performance Handler] Successfully get inventory data for VM: {0}".format(vm_moid))
                        metrics=[]
                        if config["vm_instance_allowlist"] or config["vm_instance_denylist"]:
                            metrics=[self._create_counter_from_id(metric['id'], instanced=True) for metric in self.metricscache['vmmetrics']]
                        else:
                            for metric in self.metricscache['vmmetrics']:
                                if metric['group'] == 'datastore':
                                    metrics.append(self._create_counter_from_id(metric['id'], instanced=True))
                                else:
                                    metrics.append(self._create_counter_from_id(metric['id']))
                        queryspec = Connection.vim25client.new('PerfQuerySpec', entity=vm_mor, metricId=metrics, format=format_type,intervalId=self.metricscache['vmrefreshrate'], startTime=start_time, endTime=end_time)
                        entities.append(queryspec)
                #All eligible vm's and hosts should have been added to the entities dict.  Time to get perf.
                if len(entities) > 0:
                    num_collections = math.ceil(len(entities) / float(NUM_VMS_SINGLE_COLLECTION))
                    chunk_size = int(math.ceil(len(entities) / num_collections))
                    assert chunk_size >= 0 and chunk_size <= len(entities)
                    for i in range(int(num_collections)):
                        perfdata = []
                        #python is OK with slice indexes being longer than max list index
                        chunk = entities[i * chunk_size : (i + 1) * chunk_size]
                        try:
                            perfdata = Connection.perfManager.queryPerf(chunk)
                        except WebFault as wf:
                            if "Server raised fault:" in str(wf) and "has already been deleted or has not been completely created" in str(wf):
                                self.logger.warn("[Performance Handler] Error while collecting perf data for chunk. Error: {0} Retrying...".format(str(wf)))
                                try:
                                    perfdata = Connection.perfManager.queryPerf(chunk)
                                except WebFault as wf:
                                    if "Server raised fault:" in str(wf) and "has already been deleted or has not been completely created" in str(wf):
                                        self.logger.warn("[Performance Handler] Error while collecting perf data for chunk. Error: {0} Skipping this chunk.".format(str(wf)))
                        self._process_perf_data(perfdata, format_type, host_moid, config)
                    entities = []
            # Clean the global dictionaries at the end of task.
            global host_vm_ds_map
            global host_dic
            global vm_dic
            global metric_allowdeny_flag
            global cluster_dic
            host_vm_ds_map = {}
            host_dic = {}
            vm_dic = {}
            metric_allowdeny_flag = {'vm': {}, 'host': {}}
            cluster_dic = {}
            self.logger.info("[Performance Handler] {task} finished collecting perf".format(task=config['perf_collection_type']))
            return True
        except BrokenPipeError:
            raise
        except Exception as e:
            self.logger.exception(e)
            return False


class ClusterPerfHandler(BasePerfHandler):
    """
    Handler for running Cluster perf collection
    5-minute aggregate stastistics is gathered from clusters and resource pools.
    """
    def run(self, session, config, create_time, last_time):
        """
        create_time - the time this task was created/scheduled to run (datetime object)
        last_time - the last time this task was created/scheduler to run (datetime object)
        RETURNS True if successful, False otherwise
        """
        try:
            start_time, end_time = self._prepare_timestamps(last_time, create_time)
            self.logger.debug("[Performance Handler] {task} Converting (last_time, create_time) to server time; location=handler_args_server_clock start_time={s} end_time={e}".format(task=config['perf_collection_type'], s=start_time, e=end_time))

            if not hasattr(self, 'pc') or not hasattr(self, 'config'):
                self.config = config
                self.logger.debug("[Performance Handler] {task} Instantiating PerfCollector...".format(task=config['perf_collection_type']))
                self.pc = PerfCollector(config, self.logger)
            #Handle the destination index for the data, note that we must handle empty strings and change them to None
            self.pc.update_config(config)
            self.pc.dest_index = config.get("perf_index", None)
            self.pc.collect_performance(start_time, end_time, self.output, host=session[0]+DBG_SUFFIX)
            return True
        except BrokenPipeError:
            raise
        except Exception as e:
            self.logger.exception(e)
            return False

class VcenterPerfHandler(BasePerfHandler):
    """
    Handler for running vCenter perf collection
    5-minute aggregate stastistics is gathered from vcenter server.
    """
    def run(self, session, config, create_time, last_time):
        """
        create_time - the time this task was created/scheduled to run (datetime object)
        last_time - the last time this task was created/scheduler to run (datetime object)
        RETURNS True if successful, False otherwise
        """
        try:
            start_time, end_time = self._prepare_timestamps(last_time, create_time)
            self.logger.debug("[Performance Handler] {task} Converting (last_time, create_time) to server time; location=handler_args_server_clock start_time={s} end_time={e}".format(task=config['perf_collection_type'], s=start_time, e=end_time))

            if not hasattr(self, 'vpc') or not hasattr(self, 'config'):
                self.config = config
                self.logger.debug("[Performance Handler] {task} Instantiating PerfCollector...".format(task=config['perf_collection_type']))
                self.vpc = VCPerfCollector(config, self.logger)
            self.vpc.update_config(config)
            #Handle the destination index for the data, note that we must handle empty strings and change them to None
            self.vpc.dest_index = config.get("perf_index", None)
            self.vpc.collect_performance(start_time, end_time, self.output, host=session[0]+DBG_SUFFIX)
            return True
        except BrokenPipeError:
            raise
        except Exception as e:
            self.logger.exception(e)
            return False

class DatastorePerfHandler(BasePerfHandler):
    """
    Handler for running Datastore perf collection
    """
    def run(self, session, config, create_time, last_time):
        """
        create_time - the time this task was created/scheduled to run (datetime object)
        last_time - the last time this task was created/scheduler to run (datetime object)
        RETURNS True if successful, False otherwise
        """
        try:
            global datastore_buf
            datastore_buf = []
            start_time, end_time = self._prepare_timestamps(last_time, create_time)
            self.logger.debug("[Performance Handler] {task} Converting (last_time, create_time) to server time; location=handler_args_server_clock start_time={s} end_time={e}".format(task=config['perf_collection_type'], s=start_time, e=end_time))
            ds_collection_time = utils.ConvertIsoUtcDate(end_time.strftime('%Y-%m-%dT%H:%M:%SZ'))

            #Handle the destination index for the data, note that we must handle empty strings and change them to None
            self.pool_name = config.get("pool_name", None)
            self.dest_index = config.get("perf_index", None)
            # Grab datastore metadata from runtime cache.
            target_dsinfo_cache = "dsinfo:" + Connection.domain
            self.ds_info_by_uuid = self.runtime_adapter.get_cache(target_dsinfo_cache)
            if not self.ds_info_by_uuid:
                    self.logger.warn("[Performance Handler] {task} No datastore moids in cache. Datastore performance data will be skipped for this job. Cache Target: {target}".format(task=config['perf_collection_type'], target=target_dsinfo_cache))
                    return True
            for ds_info in list(self.ds_info_by_uuid.values()):
                mor = ManagedObjectReference(value=ds_info[0], _type="Datastore")
                mo = Connection.vim25client.createExactManagedObject(mor)
                try:
                    capacity = mo.getCurrentProperty("summary.capacity")
                    self._prepare_datastore_metrics_data(metric_name="capacity", timestamp=ds_collection_time, group="datastore", type="Datastore", entity_name=ds_info[0], data=capacity, unit="bytes", name=ds_info[1])

                    freespace = mo.getCurrentProperty("summary.freeSpace")
                    self._prepare_datastore_metrics_data(metric_name="freespace", timestamp=ds_collection_time, group="datastore", type="Datastore", entity_name=ds_info[0], data=freespace, unit="bytes", name=ds_info[1])

                    used_percent = ((capacity-freespace)/capacity)*100
                    self._prepare_datastore_metrics_data(metric_name="used_percent", timestamp=ds_collection_time, group="datastore", type="Datastore", entity_name=ds_info[0], data=used_percent, unit="percent", name=ds_info[1])
                except Exception as e:
                    self.logger.warn("Couldn't find the storage details: freespace and capacity for datastore: {0}, Error: {1}.".format(ds_info[0], e))
                try:
                    uncommitted = mo.getCurrentProperty("summary.uncommitted")
                    self._prepare_datastore_metrics_data(metric_name="uncommitted", timestamp=ds_collection_time, group="datastore", type="Datastore", entity_name=ds_info[0], data=uncommitted, unit="bytes", name=ds_info[1])
                except Exception as e:
                    self.logger.warn("Couldn't find the storage detail: uncommitted for datastore: {0}, Error: {1}.".format(ds_info[0], e))
            if datastore_buf:
                ds_num_collections = int(math.ceil(len(datastore_buf) / float(NUM_EVENTS_SINGLE_COLLECTION)))
                for i in range(ds_num_collections):
                    self.output.sendChunkData(datastore_buf[i * NUM_EVENTS_SINGLE_COLLECTION: (i+1) * NUM_EVENTS_SINGLE_COLLECTION],  host=Connection.domain, index=self.dest_index)
            self.logger.info("[Performance Handler] {task} finished collecting perf".format(task=config['perf_collection_type']))
            return True
        except BrokenPipeError:
            raise
        except Exception as e:
            self.logger.exception(e)
            return False
