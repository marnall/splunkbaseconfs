import logging 

from splunk.clilib.bundle_paths import make_splunkhome_path
import splunk.admin as admin
import splunk.entity as en


required_args = []
optional_args = ['disabled','description','perftype','metric','critical','warning','comparator','entitytype']

ENDPOINT = 'admin/conf-sa_threshold'

def setup_logger():
    """
    Set up a logger with a rotating file handler for the search command.

    Returns:
        logging.Logger: A configured logger instance.
    """
    logger = logging.getLogger('sa_threshold_conf_rest_handler')
    logger.setLevel(logging.WARN)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log',
					'splunk', 'sa_threshold_conf_rest_handler.log']))
    file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))

    logger.addHandler(file_handler)

    return logger

logger = setup_logger()

class SAThresholdConfHandler(admin.MConfigHandler):

	def setup(self):
		if self.requestedAction in [admin.ACTION_CREATE, admin.ACTION_EDIT]:
			
			for arg in required_args:
				self.supportedArgs.addReqArg(arg)

			for arg in optional_args:
				self.supportedArgs.addOptArg(arg)

	def handleList(self, confInfo):
		ent = en.getEntities(ENDPOINT,
							 count=0,
							 namespace=self.appName,
							 owner=self.userName,
							 sessionKey=self.getSessionKey())
		logger.error("this is normal")
		for name, obj in ent.items():
			confItem = confInfo[name]
			for key, val in obj.items():
				confItem[key] = str(val)
			acl = {}
			for k, v in obj[admin.EAI_ENTRY_ACL].items():
				if None != v:
					acl[k] = v
			confItem.setMetadata(admin.EAI_ENTRY_ACL, acl)

	def handleReload(self, confInfo):
		# Refresh the configuration (handles disk based updates)
		refreshInfo = en.refreshEntities(ENDPOINT, sessionKey=self.getSessionKey())

	def handleEdit(self, confInfo):
		name = self.callerArgs.id

		ent = en.getEntity(ENDPOINT, name,
							  namespace=self.appName,
							  owner=self.userName,
							  sessionKey=self.getSessionKey())
							  
		for arg in optional_args:
			try:
				ent[arg] = self.callerArgs[arg]
			except:
				pass

		for arg in required_args:
			try:
				ent[arg] = self.callerArgs[arg] 
			except: 
				pass

		en.setEntity(ent, sessionKey=self.getSessionKey())

	def handleCreate(self, confInfo):
		name = self.callerArgs.id
	   
		new = en.Entity(ENDPOINT, name, 
						namespace=self.appName, owner=self.userName) 

		for arg in required_args:
			new[arg] = self.callerArgs[arg] 

	#TODO: Modify this to work appropriately
		for arg in optional_args:
			try:
				new[arg] = self.callerArgs[arg]
			except:
				pass
		
		en.setEntity(new, sessionKey=self.getSessionKey())

	def handleRemove(self, confInfo):
		name = self.callerArgs.id

		en.deleteEntity(ENDPOINT, name,
						namespace=self.appName,
						owner=self.userName,
						sessionKey = self.getSessionKey())

admin.init(SAThresholdConfHandler, admin.CONTEXT_APP_AND_USER)
