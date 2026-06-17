import splunk
import splunk.admin as admin
import splunk.appbuilder as appbuilder
import splunk.entity as en

HTTP_POST_URL   		= "url"
HTTP_POST_INDEX_BODY    = "shouldIndexBody"
HTTP_POST_INDEX_MD5     = "shouldIndexMD5"


class WebmonHandler(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
            
        if self.requestedAction == admin.ACTION_CREATE:
            for arg in [HTTP_POST_URL, HTTP_POST_INDEX_BODY, HTTP_POST_MD5]:
                self.supportedArgs.addOptArg(arg)

        elif self.requestedAction == admin.ACTION_EDIT:
            for arg in [HTTP_POST_URL, HTTP_POST_INDEX_BODY, HTTP_POST_MD5]:
                self.supportedArgs.addOptArg(arg)
                
    '''
    '''
    def handleCreate(self, confInfo):
        try:
            appName = self.callerArgs.id
            args = self.callerArgs.data

            if not HTTP_POST_URL in args:
                raise admin.ArgValidationException('Ambiguous request: no URL in post')

			url = args[HTTP_POST_URL]
			indexBody = args[HTTP_POST_INDEX_BODY]
			indexMD5 = args[HTTP_POST_INDEX_MD5]
            
			if len( url ) > 0:
			me = self.callerArgs.id
		args = self.callerArgs
		
		if int(self.callerArgs.data['field_3'][0]) < 60:
			self.callerArgs.data['field_3'][0] = '60'
				
		if int(self.callerArgs.data['field_2_boolean'][0]) == 1:
			self.callerArgs.data['field_2_boolean'][0] = '0'
		else:
			self.callerArgs.data['field_2_boolean'][0] = '1'
		
		if self.callerArgs.data['field_1'][0] in [None, '']:
			self.callerArgs.data['field_1'][0] = ''	

				
		'''
		Since we are using a conf file to store parameters, write them to the [setupentity] stanza
		in <appname>/local/myappsetup.conf  
		'''
				
		self.writeConf('myappsetup', 'setupentity', self.callerArgs.data)
           
			else:
                raise admin.ArgValidationException('Missing or wrong arguments provided for the new app')
        # translate exceptions to EAI exceptions...
        except splunk.RESTException, e:
            
            if e.statusCode == 409:
                raise admin.AlreadyExistsException(str(e.msg))
            raise

    '''
    Lists locally installed applications
    '''
    def handleList(self, confInfo):
        for appInfo in appbuilder.appInfoIterator():
            self.appName = appInfo['name']

            confInfo[self.appName].append(HTTP_POST_LABEL, appInfo['label'])
            confInfo[self.appName].append(HTTP_POST_ENABLED, appInfo['enabled'])
            # stub for SPL-17385 
            confInfo[self.appName].append(HTTP_POST_CONFIGURED, 'True')

            confInfo[self.appName].append(HTTP_POST_VISIBLE, appInfo['visible'])
            
    '''
    Controls local applications
    '''
    def handleEdit(self, confInfo):
        appName = self.callerArgs.id
        args = self.callerArgs
        action = None
        appbuilder.addUploadAssets(appName)

    '''
    Handles other commands
    '''
    def handleCustom(self, confInfo):
        action = self.customAction

        actionType = self.requestedAction
        
        # Create a package of an application
        if self.customAction == 'package':
            appName = self.callerArgs.id
            pkgPath = appbuilder.packageApp(appName)

            confInfo['Package'].append('name',appName)
            confInfo['Package'].append('path',pkgPath)
        

# initialize the handler, and add the actions it supports.    
admin.init(LocalAppsHandler, admin.CONTEXT_NONE)
