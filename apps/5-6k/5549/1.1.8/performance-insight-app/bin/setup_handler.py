import splunk.admin as admin
import splunk.entity as en 

'''
Copyright (C) 2005 - 2010 Splunk Inc. All Rights Reserved.
Description:  This skeleton python script handles the parameters in the configuration page.

      handleList method: lists configurable parameters in the configuration page
      corresponds to handleractions = list in restmap.conf

      handleEdit method: controls the parameters and saves the values 
      corresponds to handleractions = edit in restmap.conf

'''

class ConfigApp(admin.MConfigHandler):
    '''
    Set up supported arguments
    '''
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['sh_name', 'idx_name', 'event_ingesting_volume_limit', 'adhoc_search_time_limit', 'saved_search_time_limit', 'adhoc_search_count_limit', 'saved_search_count_limit','sh_cpu_limit', 'idx_cpu_limit', 'sh_memory_limit', 'idx_memory_limit']:
                self.supportedArgs.addOptArg(arg)

           
    '''
    Read the initial values of the parameters from the custom file
        perfinsight_setup.conf, and write them to the setup page. 

    If the app has never been set up,
        uses .../app_name/default/perfinsight_setup.conf. 

    If app has been set up, looks at 
        .../local/perfinsight_setup.conf first, then looks at 
    .../default/perfinsight_setup.conf only if there is no value for a field in
        .../local/perfinsight_setup.conf

    For boolean fields, may need to switch the true/false setting.

    For text fields, if the conf file says None, set to the empty string.
    '''
    def handleList(self, confInfo):
        confDict = self.readConf("perfinsight_setup")
        if None != confDict:
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
                    if val in [None, '']:
                        val = ''
                    confInfo[stanza].append(key, val)

    '''
    After user clicks Save on setup page, take updated parameters,
    normalize them, and save them somewhere
    '''
    def handleEdit(self, confInfo):
        name = self.callerArgs.id 
        args = self.callerArgs
        '''
        Since we are using a conf file to store parameters, 
        write them to the [setupentity] stanza
        in app_name/local/perfinsight_setup.conf  
        '''
        self.writeConf('perfinsight_setup', 'setupentity', self.callerArgs.data)
    
# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
