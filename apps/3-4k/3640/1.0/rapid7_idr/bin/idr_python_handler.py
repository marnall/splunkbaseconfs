import splunk.admin as admin
import splunk.entity as entity
import os

APPNAME = 'rapid7ta'

# Get Splunk home
SPLUNK_HOME = os.environ['SPLUNK_HOME']


# Setup Splunk logging
def setup_logging():
    import logging
    import logging.handlers
    import splunk

    logger = logging.getLogger('splunk.rapid7idr')
    logging_default_config_file = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    local_log_config = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    logging_stanza_name = 'python'
    logging_file_name = "rapid7idr.log"
    base_log_path = os.path.join('var', 'log', 'splunk')
    format = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    log_path = os.path.join(SPLUNK_HOME, base_log_path, logging_file_name)
    splunk_log_handler = logging.handlers.RotatingFileHandler(log_path, mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(format))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, logging_default_config_file, local_log_config, logging_stanza_name)

    #Redirect stdout
    #sys.stdout = open(os.path.join(SPLUNK_HOME, base_log_path, logging_file_name), 'w')
    return logger
# Setup Splunk logger
logger = setup_logging()

logger.info('Executing idr_python_handler.py')

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
            for arg in ['hostnames', 'app_enabled', 'enabled']:
                self.supportedArgs.addOptArg(arg)

    '''
  Read the initial values of the parameters from the custom file
      nexpose_details.conf, and write them to the setup screen.

  If the app has never been set up,
      uses .../<appname>/default/nexpose_details.conf.

  If app has been set up, looks at
      .../local/nexpose_details.conf first, then looks at
  .../default/nexpose_details.conf only if there is no value for a field in
      .../local/nexpose_details.conf

  For boolean fields, may need to switch the true/false setting.

  For text fields, if the conf file says None, set to the empty string.
  '''
    def handleList(self, confInfo):
        logger.info("Loading saved InsightIDR details")

        confDict = self.readConf("idrsetup")
        if confDict is None:
            return

        for stanza, settings in confDict.items():
            for key, val in settings.items():
                if key in ['hostnames'] and val in [None, '']:
                    val = ''
                elif key in ['app_enabled']:
                    val = self.convert_int(val)

                confInfo[stanza].append(key, val)
    
    def convert_int(self, val):
        if val == "" or val == None or int(val) != 1:
            return '0'
        return '1'

    def formatHosts(self, args, key):
        hosts = str(args.data[key][0]).replace(' ', '')
        hosts = hosts.split(',')
        for host in hosts:
            host = host.strip()
        hosts = [h for h in hosts if h != '']
        args.data[key][0] = (',').join(hosts)

    def bool_arg(self, args, name, confDict):
        if(name in args):
            if args.data[name][0] in ['True', '1', True]:
                args.data[name][0] = '1'
            else:
                args.data[name][0] = '0'
        else:
            logger.info("No config data for field '%s' passed to setup script!" % name)
            if None != confDict:
                args[name] = confDict.get(name)

        logger.info("Processed value: " + args.data[name][0])

    def string_arg(self, args, name, confDict):
        if(name in args):
            if args.data[name][0] in [None, '']:
                args.data[name][0] = ''
        else:
            logger.info("No config data for field '%s' passed to setup script!" % name)
            if None != confDict:
                args[name] = confDict.get(name)

    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs

        confDict = self.readConf("idrsetup")
        if confDict is not None:
            logger.info("Sucessfully retrieved stored config for InsightIDR.")
        else:
            logger.info("Failed to retrieved stored config for InsightIDR.")

        self.bool_arg(args, 'app_enabled', confDict)
        self.string_arg(args, 'hostnames', confDict)
        self.formatHosts(args, 'hostnames')

        logger.info(str(args))
        #Save the rest of the details - overwites any exisitng details.
        self.writeConf('idrsetup', 'setupentity', args)

# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)



