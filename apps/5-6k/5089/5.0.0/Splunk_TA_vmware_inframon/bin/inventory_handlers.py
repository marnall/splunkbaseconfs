# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved. 

#Core Python Imports
import sys
import datetime
import json
import random
# from test_autoeventgen import inventory_autogen_data
from splunk import util

# Append SA-Hydra-inframon/bin to the Python path

from splunk.clilib.bundle_paths import make_splunkhome_path
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-Hydra-inframon', 'bin']))

# Import TA-VMware-inframon collection code

import vim25.inventory as inventory
from vim25.connection import Connection
from ta_vmware_inframon.models import TAVMwareCacheStanza
from vim25.mo import ManagedObjectReference
from vim25.mo import ManagedObject


# Import from SA-Hydra-inframon
import hydra_inframon

import os

class BaseInventoryHandler(hydra_inframon.HydraHandler):
	"""
	Things all inv handlers need
	"""
	cache_model = TAVMwareCacheStanza
	def get_inv_cache(self, vc, target_config_object):
		for retry in range(4):
			locked_cache, status = self.getCacheAndLock(vc+":"+ target_config_object)
			if status:
				inv_data = locked_cache.get("inv_data", False)
				if inv_data:
					return inv_data.get("last_mor", None), inv_data.get("last_version", None), inv_data.get("last_session", None), inv_data.get("additional_fields", None), locked_cache.get("inv_time", None)
		return None, None, None, None, None

	def set_inv_cache(self, vc, target_config_object, last_mor, last_version, last_session, additional_fields, last_dump_time):
		inv_data = {"last_mor" : last_mor, "last_version" : last_version, "last_session" : last_session, "additional_fields" : additional_fields}
		inv_time = last_dump_time
		for retry in range(4):
			locked_cache, status = self.getCacheAndLock(vc+":"+ target_config_object)
			if status:
				locked_cache["inv_data"] = inv_data
				locked_cache["inv_time"] = inv_time
				return self.setCache(vc+":"+ target_config_object, locked_cache)
		return False
		
	def destroy_inv_cache(self, target, target_config_object):
		return self.destroyCache(target + ":" + target_config_object)

	# Get mor of passing type
	def find_mor_by_type(self, host_mor,type):
		"""
			@param host_mor: managed object reference of hostsystem
			@param type: entity type ex.ClusterComputeResource
		"""
		parent_mor = host_mor
		while parent_mor._type != type:
			mo = Connection.vim25client.createExactManagedObject(parent_mor)
			parent_mor = mo.getCurrentProperty("parent")
			if parent_mor._type == "RootFolder":
				return None, None
		parent_mo = Connection.vim25client.createExactManagedObject(parent_mor)
		parent_name = parent_mo.getCurrentProperty("name")
		return parent_mor, parent_name

	# Send inventory data to splunk in chunks
	def send_inv_data(self, hierarchyCollector, last_version, host, sourcetype, sourcename, time, dest_index, config, target_config_object=None, pool_name=None):
		"""
			A common function which is used to send data hierarchical data to splunk for all inventory handlers
			@param hierarchyCollector: Property collector object to get inventory data
			@param last_version : version
			@param host: host name to send the data for that host
			@param sourcetype: sourcetype name
			@param sourcename: source value
			@param time : time to index the data
			@param dest_index : splunk index value
			
			@return last_version: final version of hierarchy data
		"""
		is_first_version_seen = False
		if hierarchyCollector is None:
			self.logger.error("[Inventory Handler] Property collector to get hierarchy is not defined")
			return last_version, is_first_version_seen
		maxObjUpdates = config.get('inv_maxObjUpdates', None)
		gen_check_for_updates = hierarchyCollector.checkForUpdates(ver=last_version, maxObjUpdatesWaitOp=maxObjUpdates)
		
		# data_set is only used only for datagen, not in production, Uncomment it if you want to generate dummy events using autoeventgen
		# data_set = []

		for last_version, data in gen_check_for_updates:
			if data is None:
				self.logger.warn("Failed to get data for sourcetype=%s, version=%s", sourcename, last_version)
				return last_version, is_first_version_seen
			self.logger.info("[Inventory Handler] Creating a flattened json object")
			flattenCombineDataGen = inventory.FlattenCombinedData(data, last_version)
			host_cluster_mapping = {}
			for data in flattenCombineDataGen:
				if target_config_object == "VirtualMachine":
					vm_dict = json.loads(data) if data else {}
					vm_dict["pool_name"] = pool_name
					try:
						runtime_dict = vm_dict.get('changeSet', {}).get('summary', {}).get('runtime', {})
						host_moid = runtime_dict.get('host', {}).get('moid', None) if isinstance(runtime_dict, dict) else None
						if host_moid is not None:
							if host_moid not in host_cluster_mapping:
								host_mor = ManagedObjectReference(value=host_moid, _type="HostSystem")
								cluster_mor, cluster_name = self.find_mor_by_type(host_mor, "ClusterComputeResource")
								host_cluster_mapping[host_moid] = (cluster_mor, cluster_name)
							else:
								cluster_mor, cluster_name = host_cluster_mapping[host_moid]

							if cluster_mor is not None:
								vm_dict['cluster'] = {"moid": cluster_mor.value, "type": cluster_mor._type, "name": str(cluster_name)}
					except:
						self.logger.warn("Looks like host is not part of cluster, Cound not find ClusterComputeResource for Virtual Machine.")
					data= json.dumps(vm_dict)
				if target_config_object == "HostSystem":
					host_dict = json.loads(data) if data else {}
					host_dict["pool_name"] = pool_name
					host_moid = host_dict.get('moid', None)
					if host_moid is not None:
						try:
							host_mor = ManagedObjectReference(value=host_moid, _type="HostSystem")
							cluster_mor, cluster_name = self.find_mor_by_type(host_mor, "ClusterComputeResource")
							if cluster_mor is not None:
								host_dict['cluster'] = {"moid": cluster_mor.value, "type": cluster_mor._type, "name": str(cluster_name)}
						except:
							self.logger.warn("Looks like host is not part of cluster, Cound not find ClusterComputeResource for host.")
					data= json.dumps(host_dict)
				if target_config_object == "Datastore" or target_config_object == "ClusterComputeResource" or target_config_object == "Hierarchy":
					target_dict = json.loads(data) if data else {}
					target_dict["pool_name"] = pool_name
					data = json.dumps(target_dict)
				self.logger.info("[Inventory Handler] Finished creating a json object, processing XML output")
				self.output.sendData(data, host=host, sourcetype=sourcetype, source=sourcename, time=time, index=dest_index)

				# Uncomment the following lines if you want to generate dummy events using autoeventgen
				"""
				if config.get('autoeventgen', None) and util.normalizeBoolean(config['autoeventgen']):
					if target_config_object == 'HostSystem' or target_config_object == 'Hierarchy' or target_config_object == 'VirtualMachine' or target_config_object == 'ClusterComputeResource':
						data_set.append(data)
				"""

			del flattenCombineDataGen
			if float(str(last_version)) == 1:
				is_first_version_seen = True

		# Uncomment the following lines if you want to generate dummy events using autoeventgen
		"""
		if is_first_version_seen and config.get('autoeventgen', None) and util.normalizeBoolean(config['autoeventgen']):
			if target_config_object == 'HostSystem' or target_config_object == 'Hierarchy' or target_config_object == 'VirtualMachine' or target_config_object == 'ClusterComputeResource':
				if config.get('autoeventgen_poweroff_vmcount', None):
					poweroff_vm_count = config['autoeventgen_poweroff_vmcount']
				else:
					poweroff_vm_count = 0
				inventory_autogen_data(self, data_set, host, sourcetype, sourcename, time, dest_index, target_config_object, config["target"][0], poweroff_vm_count)
		del data_set
		"""
		return last_version, is_first_version_seen

class VirtualMachineInventoryHandler(BaseInventoryHandler):
	"""
	Handler for running the inventory collection for targetConfig
	of VirtualMachine
	"""
	def run(self, session, config, create_time, last_time):
		
		"""
		This is the method you must implement to perform your atomic task
		args:
			session - the session object return by the loginToTarget method
			config - the dictionary of all the config keys from your stanza in the collection.conf
			create_time - the time this task was created/scheduled to run (datetime object)
			last_time - the last time this task was created/scheduler to run (datetime object)
		
		RETURNS True if successful, False otherwise
		"""
		try:
			#Handle the destination index for the data, note that we must handle empty strings and change them to None
			dest_index = config.get("inv_index", False)
			if not dest_index:
				dest_index = None
			
			#Retrieve Pool name from configuration
			pool_name = config.get("pool_name", None)

			#Build a list of any additional properties that need to be collected as specified in conf file
			additionalFields = config.get("vm_inv_fields", None)
			
			self.logger.info("[Inventory Handler] Starting VirtualMachine Collection: create_time={0}, last_time={1}".format(create_time, last_time))
			self.logger.info("[Inventory Handler] Starting Cache Inspection")
			last_mor, last_version, last_session, additional_fields_cache, last_dump_time = self.get_inv_cache(session[0], "VirtualMachine")
			self.logger.info("[Inventory Handler] Finished Cache Inspection")
			self.logger.info("[Inventory Handler] Cached Collection Values: last_mor:"+str(last_mor)+"|last_version:"+str(last_version)+"|last_session:"+str(last_session)+"|last_dumptime:"+str(last_dump_time)+"|additional_fields:"+str(additional_fields_cache))
			if last_session != session[1]:
				updatedump = True
				self.logger.info("[Inventory Handler] Found a changed session, recreating collector")
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(targetConfigObject="VirtualMachine", additionalFields=additionalFields)
			elif not additional_fields_cache == additionalFields:
				updatedump = True
				self.logger.info("[Inventory Handler] Found change in additional field list, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="VirtualMachine", additionalFields=additionalFields)
			elif (create_time-last_dump_time)>datetime.timedelta(hours=4) or (last_version != None and float(str(last_version)) >= 20):
				updatedump = True
				self.logger.info("[Inventory Handler] Found session too old or version is greater then 20, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="VirtualMachine", additionalFields=additionalFields)
			else:
				updatedump = False
				self.logger.info("[Inventory Handler] Checking for updates on existing collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, targetConfigObject="VirtualMachine")
			tempus = str(Connection.svcInstance.currentTime())
			sourcename = "VMInv:" + target_config_object
			last_version, is_first_version_seen = self.send_inv_data(hierarchyCollector, last_version, session[0], "vmware_inframon:inv:vm", sourcename, tempus, dest_index, config, target_config_object, pool_name)
			if is_first_version_seen and updatedump:
				self.set_inv_cache(session[0], "VirtualMachine", mor, last_version, session[1], additionalFields, create_time)
			else:
				self.set_inv_cache(session[0], "VirtualMachine", mor, last_version, session[1], additionalFields, last_dump_time)
			self.logger.info("[Inventory Handler] Finished collecting "+target_config_object+", stored these values: mor:"+str(mor)+" | last_version:"+str(last_version)+" | session:"+str(session[1])+" | last_dump_time:"+str(last_dump_time) )
			del last_version, mor, target_config_object
			return True
		except BrokenPipeError:
			raise
		except Exception as e:
			self.logger.exception(e)
			return False

class HostSystemInventoryHandler(BaseInventoryHandler):
	"""
	Handler for running the inventory collection for targetConfig
	of HostSystem
	"""
	def run(self, session, config, create_time, last_time):
		"""
		This is the method you must implement to perform your atomic task
		args:
			session - the session object return by the loginToTarget method
			config - the dictionary of all the config keys from your stanza in the collection.conf
			create_time - the time this task was created/scheduled to run (datetime object)
			last_time - the last time this task was created/scheduler to run (datetime object)
		
		RETURNS True if successful, False otherwise
		"""
		try:
			#Handle the destination index for the data, note that we must handle empty strings and change them to None
			dest_index = config.get("inv_index", False)
			if not dest_index:
				dest_index = None
			
			#Retrieve Pool name from configuration
			pool_name = config.get("pool_name", None)

			#Build a list of any additional properties that need to be collected as specified in conf file
			additionalFields = config.get("host_inv_fields", None)

			self.logger.info("[Inventory Handler] Starting HostSystem Collection: create_time={0}, last_time={1}".format(create_time, last_time))
			self.logger.info("[Inventory Handler] Starting Cache Inspection")
			last_mor, last_version, last_session, additional_fields_cache, last_dump_time = self.get_inv_cache(session[0], "HostSystem")
			self.logger.info("[Inventory Handler] Finished Cache Inspection")
			self.logger.info("[Inventory Handler] Cached Collection Values: last_mor:"+str(last_mor)+"|last_version:"+str(last_version)+"|last_session:"+str(last_session)+"|last_dumptime:"+str(last_dump_time) +"|additional_fields:"+str(additional_fields_cache))
			if last_session != session[1]:
				updatedump = True
				self.logger.info("[Inventory Handler] Found a changed session, recreating collector")
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(targetConfigObject="HostSystem", additionalFields=additionalFields)
			elif not additional_fields_cache == additionalFields:
				updatedump = True
				self.logger.info("[Inventory Handler] Found change in additional field list, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="HostSystem", additionalFields=additionalFields)
			elif (create_time-last_dump_time)>datetime.timedelta(hours=4) or (last_version != None and float(str(last_version)) >= 20):
				updatedump = True
				self.logger.info("[Inventory Handler] Found session too old or version is greater then 20, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="HostSystem", additionalFields=additionalFields)
			else:
				updatedump = False
				self.logger.info("[Inventory Handler] Checking for updates on existing collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, targetConfigObject="HostSystem")
			tempus = str(Connection.svcInstance.currentTime())
			sourcename = "VMInv:" + target_config_object
			last_version, is_first_version_seen = self.send_inv_data(hierarchyCollector, last_version, session[0], "vmware_inframon:inv:hostsystem", sourcename, tempus, dest_index, config, target_config_object, pool_name)
			if is_first_version_seen and updatedump:
				self.set_inv_cache(session[0], "HostSystem", mor, last_version, session[1], additionalFields, create_time)
			else:
				self.set_inv_cache(session[0], "HostSystem", mor, last_version, session[1], additionalFields, last_dump_time)
			self.logger.info("[Inventory Handler] Finished collecting "+target_config_object+", stored these values: mor:"+str(mor)+" | last_version:"+str(last_version)+" | session:"+str(session[1])+" | last_dump_time:"+str(last_dump_time) )
			del last_version, mor, target_config_object
			return True
		except BrokenPipeError:
			raise
		except Exception as e:
			self.logger.exception(e)
			return False
			
class ClusterComputeResourceInventoryHandler(BaseInventoryHandler):
	"""
	Handler for running the inventory collection for targetConfig
	of ClusterComputeResource
	"""
	def run(self, session, config, create_time, last_time):
		"""
		This is the method you must implement to perform your atomic task
		args:
			session - the session object return by the loginToTarget method
			config - the dictionary of all the config keys from your stanza in the collection.conf
			create_time - the time this task was created/scheduled to run (datetime object)
			last_time - the last time this task was created/scheduler to run (datetime object)
		
		RETURNS True if successful, False otherwise
		"""
		try:
			#Handle the destination index for the data, note that we must handle empty strings and change them to None
			dest_index = config.get("inv_index", False)
			if not dest_index:
				dest_index = None
			
			#Retrieve Pool name from configuration
			pool_name = config.get("pool_name", None)

			#Build a list of any additional properties that need to be collected as specified in conf file
			additionalFields = config.get("cluster_inv_fields", None)

			self.logger.info("[Inventory Handler] Starting ClusterComputeResource Collection: create_time={0}, last_time={1}".format(create_time, last_time))
			self.logger.info("[Inventory Handler] Starting Cache Inspection")
			last_mor, last_version, last_session, additional_fields_cache, last_dump_time = self.get_inv_cache(session[0], "ClusterComputeResource")
			self.logger.info("[Inventory Handler] Finished Cache Inspection")
			self.logger.debug("[Inventory Handler] Cached Collection Values: last_mor:"+str(last_mor)+"|last_version:"+str(last_version)+"|last_session:"+str(last_session)+"|last_dumptime:"+str(last_dump_time)+"|additional_fields:"+str(additional_fields_cache))
			if last_session != session[1]:
				updatedump = True
				self.logger.info("[Inventory Handler] Found a changed session, recreating collector")
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(targetConfigObject="ClusterComputeResource", additionalFields=additionalFields)
			elif not additional_fields_cache == additionalFields:
				updatedump = True
				self.logger.info("[Inventory Handler] Found change in additional field list, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="ClusterComputeResource", additionalFields=additionalFields)
			elif (create_time-last_dump_time)>datetime.timedelta(hours=4) or (last_version != None and float(str(last_version)) >= 20):
				updatedump = True
				self.logger.info("[Inventory Handler] Found session too old or version is greater then 20, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="ClusterComputeResource", additionalFields=additionalFields)
			else:
				updatedump = False
				self.logger.info("[Inventory Handler] Checking for updates on existing collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, targetConfigObject="ClusterComputeResource")
			tempus = str(Connection.svcInstance.currentTime())
			sourcename = "VMInv:" + target_config_object
			last_version, is_first_version_seen = self.send_inv_data(hierarchyCollector, last_version, session[0], "vmware_inframon:inv:clustercomputeresource", sourcename, tempus, dest_index, config, target_config_object, pool_name)
			if is_first_version_seen and updatedump:
				self.set_inv_cache(session[0], "ClusterComputeResource", mor, last_version, session[1], additionalFields, create_time)
			else:
				self.set_inv_cache(session[0], "ClusterComputeResource", mor, last_version, session[1], additionalFields, last_dump_time)
			self.logger.info("[Inventory Handler] Finished collecting "+target_config_object+", stored these values: mor:"+str(mor)+" | last_version:"+str(last_version)+" | session:"+str(session[1])+" | last_dump_time:"+str(last_dump_time) )
			del last_version, mor, target_config_object
			return True
		except BrokenPipeError:
			raise
		except Exception as e:
			self.logger.exception(e)
			return False

class DatastoreInventoryHandler(BaseInventoryHandler):
	"""
	Handler for running the inventory collection for targetConfig
	of Datastore
	"""
	def run(self, session, config, create_time, last_time):
		"""
		This is the method you must implement to perform your atomic task
		args:
			session - the session object return by the loginToTarget method
			config - the dictionary of all the config keys from your stanza in the collection.conf
			create_time - the time this task was created/scheduled to run (datetime object)
			last_time - the last time this task was created/scheduler to run (datetime object)
		
		RETURNS True if successful, False otherwise
		"""
		try:
			#Handle the destination index for the data, note that we must handle empty strings and change them to None
			dest_index = config.get("inv_index", False)
			if not dest_index:
				dest_index = None
			
			#Retrieve Pool name from configuration
			pool_name = config.get("pool_name", None)

			#Build a list of any additional properties that need to be collected as specified in conf file
			additionalFields = config.get("datastore_inv_fields", None)
			
			self.logger.info("[Inventory Handler] Starting Datastore Collection: create_time={0}, last_time={1}".format(create_time, last_time))
			self.logger.info("[Inventory Handler] Starting Cache Inspection")
			last_mor, last_version, last_session, additional_fields_cache, last_dump_time = self.get_inv_cache(session[0], "Datastore")
			self.logger.info("[Inventory Handler] Finished Cache Inspection")
			self.logger.debug("[Inventory Handler] Cached Collection Values: last_mor:"+str(last_mor)+"|last_version:"+str(last_version)+"|last_session:"+str(last_session)+"|last_dumptime:"+str(last_dump_time)+"|additional_fields_cache:"+str(additional_fields_cache))
			if last_session != session[1]:
				updatedump = True
				self.logger.info("[Inventory Handler] Found a changed session, recreating collector")
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(targetConfigObject="Datastore", additionalFields=additionalFields)
			elif not additional_fields_cache == additionalFields:
				updatedump = True
				self.logger.info("[Inventory Handler] Found change in additional field list, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="Datastore", additionalFields=additionalFields)
			elif (create_time-last_dump_time)>datetime.timedelta(hours=4) or (last_version != None and float(str(last_version)) >= 20):
				updatedump = True
				self.logger.info("[Inventory Handler] Found session too old or version is greater then 20, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="Datastore", additionalFields=additionalFields)
			else:
				updatedump = False
				self.logger.info("[Inventory Handler] Checking for updates on existing collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, targetConfigObject="Datastore")
			tempus = str(Connection.svcInstance.currentTime())
			sourcename = "VMInv:" + target_config_object
			last_version, is_first_version_seen = self.send_inv_data(hierarchyCollector, last_version, session[0], "vmware_inframon:inv:datastore", sourcename, tempus, dest_index, config, target_config_object, pool_name)
			if is_first_version_seen and updatedump:
				self.set_inv_cache(session[0], "Datastore", mor, last_version, session[1], additionalFields, create_time)
			else:
				self.set_inv_cache(session[0], "Datastore", mor, last_version, session[1], additionalFields, last_dump_time)
			self.logger.info("[Inventory Handler] Finished collecting "+target_config_object+", stored these values: mor:"+str(mor)+" | last_version:"+str(last_version)+" | session:"+str(session[1])+" | last_dump_time:"+str(last_dump_time) )
			del last_version, mor, target_config_object
			return True
		except BrokenPipeError:
			raise
		except Exception as e:
			self.logger.exception(e)
			return False

class HierarchyInventoryHandler(BaseInventoryHandler):
	"""
	Handler for running the inventory collection for targetConfig
	of Hierarchy
	"""
	def run(self, session, config, create_time, last_time):
		"""
		This is the method you must implement to perform your atomic task
		args:
			session - the session object return by the loginToTarget method
			config - the dictionary of all the config keys from your stanza in the collection.conf
			create_time - the time this task was created/scheduled to run (datetime object)
			last_time - the last time this task was created/scheduler to run (datetime object)
		
		RETURNS True if successful, False otherwise
		"""
		try:
			#Handle the destination index for the data, note that we must handle empty strings and change them to None
			dest_index = config.get("inv_index", False)
			if not dest_index:
				dest_index = None
			
			#Retrieve Pool name from configuration
			pool_name = config.get("pool_name", None)

			self.logger.info("[Inventory Handler] Starting Hierarchy Collection: create_time={0}, last_time={1}".format(create_time, last_time))
			self.logger.info("[Inventory Handler] Starting Cache Inspection")
			last_mor, last_version, last_session, _, last_dump_time = self.get_inv_cache(session[0], "Hierarchy")
			self.logger.info("[Inventory Handler] Finished Cache Inspection")
			self.logger.debug("[Inventory Handler] Cached Collection Values: last_mor:"+str(last_mor)+"|last_version:"+str(last_version)+"|last_session:"+str(last_session)+"|last_dumptime:"+str(last_dump_time))
			if last_session != session[1]:
				updatedump = True
				self.logger.info("[Inventory Handler] Found a changed session, recreating collector.")
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(targetConfigObject="Hierarchy")
			elif (create_time-last_dump_time)>datetime.timedelta(hours=4) or (last_version != None and float(str(last_version)) >= 20):
				updatedump = True
				self.logger.info("[Inventory Handler] Found session too old or version is greater then 20, recreating collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, updateType="recycle", targetConfigObject="Hierarchy")
			else:
				updatedump = False
				self.logger.info("[Inventory Handler] Checking for updates on existing collector")
				self.logger.debug("[Inventory Handler] Calling CreateHierarchyCollector: MOR:"+str(last_mor)+"| Version:"+str(last_version))
				last_version, hierarchyCollector, target_config_object, mor = inventory.CreateHierarchyCollector(managedObjectReference=last_mor, version=last_version, targetConfigObject="Hierarchy")
			tempus = str(Connection.svcInstance.currentTime())
			sourcename = "VMInv:" + target_config_object
			last_version, is_first_version_seen = self.send_inv_data(hierarchyCollector, last_version, session[0], "vmware_inframon:inv:hierarchy", sourcename, tempus, dest_index, config, target_config_object, pool_name)
			if is_first_version_seen and updatedump:
				self.set_inv_cache(session[0], "Hierarchy", mor, last_version, session[1], None, create_time)
				addRootNode = True
			else:
				self.set_inv_cache(session[0], "Hierarchy", mor, last_version, session[1], None, last_dump_time)
				addRootNode = False
			if addRootNode:
				rootNode={ "moid":Connection.rootFolder.getMOR().value, "type":"RootFolder", "changeSet":{"name":Connection.domain, "parent":{"moid":"N/A", "type":"N/A"}}}
				self.output.sendData(inventory.Jsonify(rootNode), host=session[0], sourcetype="vmware_inframon:inv:hierarchy", source=sourcename, time=tempus, index=dest_index)
			self.logger.info("[Inventory Handler] Finished collecting "+target_config_object+", stored these values: mor:"+str(mor)+" | last_version:"+str(last_version)+" | session:"+str(session[1])+" | last_dump_time:"+str(last_dump_time) )
			del last_version, mor, addRootNode, target_config_object
			return True
		except BrokenPipeError:
			raise
		except Exception as e:
			self.logger.exception(e)
			return False