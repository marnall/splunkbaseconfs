#Copyright (C) 2014 Kieren Crossland
import pprint as pp
import logging 
import copy
import httplib
import json

import splunk
import splunk.admin as admin
import splunk.entity as en
import splunk.rest as rest
from splunk import util

# set up logging suitable for splunkd consumption
logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

ENDPOINT = '/admin/conf-tems'
req_args = ['temsname', 'hostname', 'username','tepshost']
opt_args = ['password', 'port','tepsport','domain_override']

class ConfigApp(admin.MConfigHandler):
	def setup(self):
		logging.debug("Initialising tems endpoint handler")
		if self.requestedAction in [admin.ACTION_CREATE, admin.ACTION_EDIT]:
			for arg in req_args:
				self.supportedArgs.addReqArg(arg)
			for arg in opt_args:
				self.supportedArgs.addOptArg(arg)

	def handleList(self, confInfo):
		logging.debug("Reading tems conf")
		confDict = self.readConfCtx("tems")
		if None != confDict:
			for stanza, settings in confDict.items():
				for key, val in settings.items():
					confInfo[stanza].append(key, val)
				
				#try to get creds
				if 'password' not in confInfo[stanza]:
					try:
						# works with 6.3+ to allow non admins access to tems creds
						logging.debug("Getting TEMS password from tems_creds endpoint")
						rsp, content = rest.simpleRequest('/servicesNS/nobody/ITM6/ITM6/tems_creds', getargs={'entity': str(stanza)+':'+str(confInfo[stanza]['username'])+':'}, sessionKey=self.getSessionKey(), raiseAllErrors=True, timeout=60)
						
						if rsp.status == 200:
							creds = json.loads(content)
							confInfo[stanza].append('password', creds['password'])
						else:
							raise Exception("HTTP Error %s returned from tems_creds endpoint: %s\n" % (rsp.status, content))	
					except Exception, e:
						raise Exception("Error %s returned from tems_creds endpoint: %s\n" % (e))	

						confInfo[stanza].append('password', result['password'])
				
				acl = {}
				for k, v in settings[admin.EAI_ENTRY_ACL].items():
					if None != v:
						acl[k] = v
				confInfo[stanza].setMetadata(admin.EAI_ENTRY_ACL, acl)

	def handleEdit(self, confInfo):
		self.processModification('edit', confInfo)

	def handleCreate(self, confInfo):
		self.processModification('create', confInfo)
		
	def processModification(self, action, confInfo):
		logging.debug("Saving TEMS conf")
		name = self.callerArgs.id
		args = self.callerArgs
		sessionKey = self.getSessionKey()
		
		for arg in req_args:
			self.supportedArgs.addReqArg(arg)
			if args.data[arg][0] in [None, '']:
				#check that this is not blank
				raise admin.ArgValidationException, str(arg) + " cannot be blank"
		
		password = ""		
		try:
			#clear the password field as this is stored in app.conf
			password = args.data['password'][0]
			args.data['password'][0] = ''
		except:
			pass

		try:
			#write the conf file
			new = {}
			for arg in req_args:
				new[arg] = self.callerArgs[arg] 

			for arg in opt_args:
				if None in self.callerArgs[arg]:
					new[arg] = ''
				else:
					new[arg] = self.callerArgs[arg]
				#except:
				#	pass
			self.writeConf('tems', name, new)
			
		except Exception, e:
			raise admin.ArgValidationException, "Failed to create tems config: %s; %s" % (str(e), new)
		
		#Create encrypted password
		try:
			#delete existing credential setting if there is one
			if action == 'edit' and password != None:
				try:
					en.deleteEntity('/storage/passwords', name+':'+args.data['username'][0]+':', sessionKey=sessionKey, owner='nobody',namespace='ITM6')
				except Exception, e: 
					pass
			
			credentials = en.getEntity('/storage/passwords','_new', owner=self.userName,namespace=self.appName, sessionKey=sessionKey)
			credentials['name'] = args.data['username'][0]
			credentials['password'] = password
			credentials['realm'] = name
			credentials.namespace = 'ITM6'
			en.setEntity(credentials, sessionKey=sessionKey)
		except Exception, e:
			raise admin.ArgValidationException, "Failed to create credential: " + str(e)

	def handleRemove(self, confInfo):
		logging.debug("Removing TEMS conf")
		id = self.callerArgs.id
		if id:
			confDict = self.readConf("tems")
			if id in confDict:
				cfg = confDict[id]
				temsname = cfg['temsname']
				username = cfg['username']
				
				#add try/catch
				sessionKey = self.getSessionKey()
				
				try:
					en.deleteEntity(ENDPOINT, id, sessionKey=sessionKey, owner=self.userName,namespace=self.appName)
					
				except Exception, e:
					raise admin.ArgValidationException, "Failed to delete stanza: " + str(e)
				
				try:
					en.deleteEntity('/storage/passwords', id+':'+username+':', sessionKey=sessionKey, owner='nobody',namespace='ITM6')
				except Exception, e:
					# Handle cases where no password entry is found in storage/passwords
					raise admin.ArgValidationException, "Failed to delete password: " + str(e)
					#pass

				self.shouldReload = True

	def handleReload(self, confInfo):
		logging.debug("ITM6 TEMS reload called")
		en.refreshEntities('properties/tems', sessionKey=self.getSessionKey())
	
	def handleCustom(self, confInfo):
		logging.debug("ITM6 TEMS %s called" % self.customAction)
		if self.customAction in ['_reload']:
			return self.handleReload(confInfo)
		else:
			raise splunk.ResourceNotFound()

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)