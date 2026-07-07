#!/usr/bin/env python
# coding: utf-8
# COPYRIGHT BY GEMINI DATA INC - All rights reserved
# KV Store Migrate
# Enables migration of collections on a per-app basis

# Author: Florian Miehe
# Version: 1.3.1

import sys
from splunk.clilib import cli_common as cli
from splunklib.searchcommands import \
	dispatch, GeneratingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli
import splunklib.client as client
import splunk.rest as rest
import splunk.entity as entity
import os, stat
import json
import httplib, urllib
import urllib2
import time
from datetime import datetime
import gzip
import glob
import shutil
import logging
import re
from xml.dom import minidom
import roles


@Configuration()
class KVStoreMigrateCommand(GeneratingCommand):
	""" %(synopsis)

	##Syntax

	| kvstoremigrate app="app_name" collection="collection_name" global_scope="false" target="remotehost"

	##Description

	migrate each collection in the KV Store to a JSON file in the path specified

	"""

	app = Option(
		doc='''
			Syntax: app=<appname>
			Description: Specify the app to backup collections from''',
			require=False)

	global_scope = Option(
		doc='''
			Syntax: global_scope=[true|false]
			Description: Specify the whether or not to include all globally available collections''',
			require=False, validate=validators.Boolean())

	collection = Option(
		doc='''
			Syntax: collection=<collection_name>
			Description: Specify the collection to backup within the specified app''',
			require=False)

	append = Option(
		doc='''
			Syntax: append=[true|false]
			Description: Specify whether or not to delete existing entries on the target.''',
			require=False, validate=validators.Boolean())

	target = Option(
		doc='''
			Syntax: target=<remotetarget_hostname>
			Description: Specify the hostname to migrate to. Credentials must be given via setup.''',
			require=True)

	targetport = Option(
		doc='''
			Syntax: port=<Port>
			Description: Specify the Splunk serviceport''',
			require=False, validate=validators.Integer(minimum=1025,maximum=65535))

	def request(self, method, url, data, headers):
		"""Helper function to fetch JSON data from the given URL"""
		req = urllib2.Request(url, data, headers)
		req.get_method = lambda: method
		res = urllib2.urlopen(req)
		res_txt = res.read()
		res_code = res.getcode()
		if len(res_txt)>0:
			return json.loads(res_txt)
		else:
			return res_code

	# access the credentials in /servicesNS/nobody/app_name/admin/passwords
	def getCredentials(self, sessionKey):
		myapp = 'gemini_kvstore_tools'
		try:
		# list all credentials
		 entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
		 owner='nobody', sessionKey=sessionKey)
		except Exception, e:
			raise Exception("Could not get %s credentials from splunk. Error: %s"
				% (myapp, str(e)))

		# return first set of credentials
		for i, c in entities.items():
			return c['username'], c['clear_password']
		raise Exception("No credentials have been found")

	def generate(self):
		logger = logging.getLogger('kvst')

		# Facility Info in the loglines
		facility = os.path.basename(__file__)
		facility = os.path.splitext(facility)[0]
		facility = facility.replace('_','')
		facility = "[%s]" % (facility)

		logger.debug('%s KVStoreMigrateCommand: %s', facility, self)
		errors = []

		# get service object for more infos about this session
		service = client.connect(token=self._metadata.searchinfo.session_key)

		# Check permissions
		required_role = "kv_admin"
		active_user = self._metadata.searchinfo.username
		if active_user in roles.get_role_users(self._metadata.searchinfo.session_key, required_role) or active_user == "admin":
			logger.debug("%s User %s is authorized.", facility, active_user)
		else:
			logger.error("%s User %s is unauthorized. Has the kv_admin role been granted?", facility, active_user)
			exit(3)

		logger.info('%s kvstoremigrate started', facility)

		try:
			cfg = cli.getConfStanza('kvstore_tools','backups')
			limits_cfg = cli.getConfStanza('limits','kvstore')
		except BaseException as e:
			logger.error("%s ERROR getting configuration: " + str(e), facility)

		batch_size = int(cfg.get('backup_batch_size'))
		logger.debug("%s Batch size: %d rows", facility, batch_size)
		session_key = self._metadata.searchinfo.session_key
		splunkd_uri = self._metadata.searchinfo.splunkd_uri

		if len(session_key) == 0:
			sys.stderr.write("Did not receive a session key from splunkd. " +
							"Please enable passAuth in inputs.conf for this " +
							"script\n")
			exit(2)

		# get credentials - might exit if no creds are available
		username, password = self.getCredentials(session_key)

		# Sanitize input
		if self.app:
			logger.debug('%s App Context: %s', facility, self.app)
		else:
			self.app = None

		if self.collection:
			logger.debug('%s Collection: %s', facility, self.collection)
		else:
			self.collection=None

		if self.global_scope:
			logger.debug('%s Global Scope: %s', facility, self.global_scope)
		else:
			self.global_scope = False

		if self.append:
			logger.debug('%s Appending to existing collection', facility)
		else:
			self.append = False
			logger.debug('%s Append to existing collection: ' + str(self.append), facility)

		if self.targetport:
			logger.debug('%s Port for remote connect: %s', facility, self.targetport)
		else:
			self.targetport = 8089

		url_tmpl_app = '%(server_uri)s/servicesNS/%(owner)s/%(app)s/storage/collections/config?output_mode=json&count=0'

		# Login Remote and get the Remote session key
		try:
			remote_uri = 'https://' + self.target + ':' + str(self.targetport)
			request = urllib2.Request(remote_uri + '/servicesNS/admin/search/auth/login',data = urllib.urlencode({'username': username, 'password': password}))
			server_content = urllib2.urlopen(request)

		except (urllib2.HTTPError, BaseException) as e:
			logger.critical('%s ERROR Failed to login on remote Splunk instance: %s', facility, str(e))
			sys.exit(3)

		remote_session_key = str(minidom.parseString(server_content.read()).getElementsByTagName('sessionKey')[0].childNodes[0].nodeValue)
		apps = []
		logger.debug('%s Remote Session_key: ' + remote_session_key, facility)
		if self.app is not None:
			apps.append(self.app)
		else:
			# Enumerate all apps
			try:
				response, content = rest.simpleRequest("apps/local?output_mode=json", sessionKey=session_key, method='GET')
				#logger.debug('%s Server response: %s', facility, response)
				#logger.debug('%s Server content: %s', facility, content)
				content = json.loads(content)
				for entry in content["entry"]:
					if not entry["content"]["disabled"]:
						apps.append(entry["name"])

			except urllib2.HTTPError, e:
				logger.critical('%s ERROR Failed to create app list: %s', json.dumps(json.loads(e.read())), facility)
				sys.exit(3)
			except urllib2.URLError, e:
				logger.critical('%s ERROR URLError = ' + json.dumps(json.loads(e.read())), facility)
				sys.exit(3)
			except httplib.HTTPException, e:
				logger.critical('%s HTTPException: ' + json.dumps(json.loads(e.read())), facility)
				sys.exit(3)
		collections = []
		for app in apps:
			logger.debug("%s Polling collections in app: %s" , facility, app)
			# Enumerate all of the collections in the app (if an app is selected)
			collections_url = url_tmpl_app % dict(
				server_uri=splunkd_uri,
				owner='nobody',
				app=app)
			headers = {
				'Authorization': 'Splunk %s' % session_key,
				'Content-Type': 'application/json'}
			try:
				response = self.request('GET', collections_url, '', headers)
			except urllib2.HTTPError, e:
				logger.critical('%s ERROR Failed to download collection list: %s', json.dumps(json.loads(e.read())), facility)
				sys.exit(3)
			except urllib2.URLError, e:
				logger.critical('%s ERROR URLError = ' + json.dumps(json.loads(e.read())), facility)
				sys.exit(3)
			except httplib.HTTPException, e:
				logger.critical('%s HTTPException: ' + json.dumps(json.loads(e.read())), facility)
				sys.exit(3)

			logger.debug("%s Parsing response for collections in app: %s" , facility, app)
			for entry in response["entry"]:
				entry_app = entry["acl"]["app"]
				collection_name = entry["name"]
				#logger.debug(entry_app)
				#logger.debug(collection_name)
				sharing = entry["acl"]["sharing"]

				#logger.debug("Parsing entry: %s" % str(entry))

				if (self.app == entry_app and self.collection == collection_name) or (self.app is None and self.collection == collection_name) or (self.app == entry_app and self.collection is None) or (sharing == 'global' and self.global_scope) or (self.app is None and self.collection is None):

					c = [entry_app, collection_name]
					if c not in collections:
						collections.append(c)
					logger.debug("%s Added {0}/{1} to migration list".format(entry_app, collection_name), facility)

		logger.debug('%s Collections to migrate: %s', facility, str(collections))

		url_tmpl_collection = '%(server_uri)s/servicesNS/%(owner)s/%(app)s/storage/collections/data/%(collection)s?limit=%(limit)s&skip=%(skip)s&output_mode=json'

		for collection in collections:
			# Reset every iteration to local splunk uri
			headers = {
				'Authorization': 'Splunk %s' % session_key,
				'Content-Type': 'application/json'}
			batched_response = ''

			# Extract the app and collection name from the array
			entry_app = collection[0]
			collection_name = collection[1]
			loop_record_count = None
			total_record_count = 0
			message = None
			maxrows = int(limits_cfg.get('max_rows_per_query'))
			logger.debug('%s Collection: %s', facility, collection)

			try:
				cursor = 0

				# If the loop record count is equal to batch size, we hit the limit. Keep going.
				while (loop_record_count is None or loop_record_count == batch_size):

					# Build the URL
					data_url = url_tmpl_collection % dict(
						server_uri=splunkd_uri,
						owner='nobody',
						app=entry_app,
						collection=collection_name,
						limit = batch_size,
						skip = cursor)

					# Download the data from the collection
					response = self.request('GET', data_url, '', headers)

					# Remove the first and last characters ( [ and ] )
					response = json.dumps(response)[1:-1]
					#logger.debug('Response: %s ' , response)
					loop_record_count = response.count('_key')
					total_record_count += loop_record_count
					logger.debug('%s We counted ' + str(total_record_count) + ' total records and ' + str(loop_record_count) + ' in this loop.', facility)

					# Append the records to the variable
					if loop_record_count > 0:
						## Write the leading [ or comma delimiter (between batches)
						if cursor == 0:
							batched_response = batched_response + '['
						else:
							batched_response = batched_response + ','
						batched_response = batched_response + response
						if loop_record_count < batch_size:
							batched_response = batched_response + ']'
					cursor += loop_record_count

				logger.debug("%s Retrieved {0} records from {1}".format(total_record_count, collection_name), facility)

				if total_record_count > 0:
					logger.debug('%s maxrows per query: ' + str(maxrows))
					if total_record_count == maxrows:
						logger.warning('%s Stored up KV store collection up to the limit: %s/%s', facility, entry_app, collection_name)
						result = "warning"
						message = "Rows returned equal to configured limit. Possible incomplete backup."
					if batch_size > maxrows and total_record_count > maxrows:
						logger.warning('%s Stored up KV store collection with batches exceeding the limit: %s/%s', facility, entry_app, collection_name)
						result = "warning"
						message = "Batch size greater than configured query limit. Possible incomplete backup."
					else:
						logger.info('%s Stored up KV store collection successfully: %s/%s', facility, entry_app, collection_name)
						result = "success"
						message = "downloaded collection"
					# make it a json object
					batched_response = json.loads(batched_response)
				else:
					logger.debug('Skipping collection: ' + collection_name)
					result = "skipped"
					message = "collection is empty"

			except BaseException as e:
				logger.critical('%s ERROR Failed to download collection: %s', facility, str(e))
				logger.debug(str(headers))
				result = "error"
				message = str(e)
				record_count = 0
				errors.append('%s ERROR downloading collection: ' + entry_app + '/' + collection_name, facility)

			yield {'_time': time.time(), 'app': entry_app, 'collection': collection_name, 'result': result, 'records': total_record_count, 'message': message, }
			content_len = len(batched_response)
			logger.debug('%s Length batched_response: ' + str(len(batched_response)), facility)
			#logger.debug('BATCHED RESPONSE: ' + str(batched_response))

			# Set URL templates
			url_tmpl_add_collection = '%(server_uri)s/servicesNS/%(owner)s/%(app)s/storage/collections/config?output_mode=json'
			url_tmpl_batch = '%(server_uri)s/servicesNS/%(owner)s/%(app)s/storage/collections/data/%(collection)s/batch_save?output_mode=json'
			url_tmpl = '%(server_uri)s/servicesNS/%(owner)s/%(app)s/storage/collections/data/%(collection)s/?output_mode=json'

			# Build the URL for adding the collection
			create_collection_url = url_tmpl_add_collection % dict(
				server_uri=remote_uri,
				owner='nobody',
				app=app)

			# Build the URL for deleting the collection
			delete_url = url_tmpl % dict(
				server_uri=remote_uri,
				owner='nobody',
				app=app,
				collection=collection_name)

			# Build the URL for updating the collection
			record_url = url_tmpl_batch % dict(
				server_uri=remote_uri,
				owner='nobody',
				app=app,
				collection=collection_name)

			logger.debug('%s delete_url: ' + delete_url + ' record_url: ' + record_url, facility)

			# Use remote session_key for target Host
			headers = {
				'Authorization': 'Splunk %s' % remote_session_key,
				'Content-Type': 'application/json'}

			# Enumerate all of the collections in the app (if an app is selected)
			collections_url = url_tmpl_app % dict(
				server_uri=remote_uri,
				owner='nobody',
				app=app)

			# Get list of collections on the remote-host
			try:
				response = self.request('GET', collections_url, '', headers)
			except urllib2.HTTPError, e:
				logger.critical('%s ERROR Failed to download remote collection list: %s', json.dumps(json.loads(e.read())), facility)
				sys.exit(3)
			except urllib2.URLError, e:
				logger.critical('%s ERROR URLError = ' + json.dumps(json.loads(e.read())), facility)
				sys.exit(3)
			except httplib.HTTPException, e:
				logger.critical('%s HTTPException: ' + json.dumps(json.loads(e.read())), facility)
				sys.exit(3)

			# Look for collection in remote-collection-list, create it if necessary
			if not any(d['name'] == collection_name for d in response["entry"]):
				try:
					response = self.request('POST',create_collection_url,'name=' + str(collection[1]),headers)
					logger.debug('%s Created collection: ' + str(collection[1]), facility)
				except (urllib2.HTTPError,BaseException) as e:
					logger.critical('%s ERROR Failed to create collection: ' + json.dumps(json.loads(e.read())), facility)
					sys.exit(3)
				except urllib2.URLError, e:
					logger.critical('%s ERROR URLError = ' + json.dumps(json.loads(e.read())), facility)
					sys.exit(3)
				except httplib.HTTPException, e:
					logger.critical('%s HTTPException: ' + json.dumps(json.loads(e.read())), facility)
					sys.exit(3)
			else:
				if not self.append:
					# Delete the collection contents
					try:
						response = self.request('DELETE', delete_url, '', headers)
						logger.debug('%s Server response for collection deletion: ' + json.dumps(response), facility)
					except urllib2.HTTPError as e:
						logger.critical('%s ERROR Failed to delete collection: ' + json.dumps(json.loads(e.read())), facility)
						sys.exit(3)
					except urllib2.URLError, e:
						logger.critical('%s ERROR URLError = ' + json.dumps(json.loads(e.read())), facility)
						sys.exit(3)
					except httplib.HTTPException, e:
						logger.critical('%s HTTPException: ' + json.dumps(json.loads(e.read())), facility)
						sys.exit(3)

			# set everything up for the Upload
			i = 0
			batch_number = 1
			limit = int(limits_cfg.get('max_documents_per_batch_save'))
			posted = 0

			while i < content_len:
				# Get the lesser number between (limit-1) and (content_len)
				last = (batch_number*limit)
				last = min(last, content_len)
				batch = batched_response[i:last]
				i += limit

				logger.debug('%s Batch number: ' + str(batch_number) + '(' + str(sys.getsizeof(batch)) + ' bytes)', facility)

				# Upload the restored records to the server
				try:
					#logger.debug('posting batch: ' + json.dumps(batch))
					response = self.request('POST', record_url, json.dumps(batch), headers)
					logger.debug('%s Server response:' + str(len(response)) + ' records uploaded.', facility)
					batch_number += 1
					posted += len(batch)
					message = 'posted collection to ' + self.target
					result = 'success'
				except urllib2.HTTPError, e:
					logger.error('[kvstoremigrate] ERROR Failed to update records:', json.dumps(json.loads(e.read())))
					message = str(e)
					result = 'error'
					# Force out of the while loop
					i = content_len
				except urllib2.URLError, e:
					logger.critical('%s ERROR URLError = ' + json.dumps(json.loads(e.read())), facility)
					message = str(e)
					result = 'critical'
					yield {'_time': time.time(), 'app': app, 'collection': collection_name, 'records': posted, 'result': result, 'message': message }
					# exit because we could have a problem with the given target
					sys.exit(3)
				except httplib.HTTPException, e:
					logger.critical('%s HTTPException: ' + json.dumps(json.loads(e.read())), facility)
					message = str(e)
					result = 'critical'
					yield {'_time': time.time(), 'app': app, 'collection': collection_name, 'records': posted, 'result': result, 'message': message }
					# exit because we could have a problem with the given target
					sys.exit(3)
			if result != 'skipped':
				# Collection now fully restored
				logger.info('%s Restored collection ' + collection_name + ' successfully.', facility)
				yield {'_time': time.time(), 'app': app, 'collection': collection_name, 'records': posted, 'result': result, 'message': message }

dispatch(KVStoreMigrateCommand, sys.argv, sys.stdin, sys.stdout, __name__)
