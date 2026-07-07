import splunk.admin as admin
import splunk.entity as entity
import splunklib.client as client

logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

class CawsConfig(admin.MConfigHandler):
    """
    Config file name (cawssetup.conf)
    """    
    configFile = "cawssetup"

    """
    Inputs config file name (inputs.conf)
    """
    inputsFile = "inputs"

    """
    The default input kind.
    """
    inputKind = "cawsdata"

    """
    The default input name for the application.
    """
    inputName = "events"

    """
    Config file stanza (settings)
    """
    configStanza = "settings"

    """
    The keys for CAWS API credentials.
    """
    keyUsername = "username"
    keyPassword = "password"

    """
    The key for the interval to poll the api.
    """
    keyInterval = "interval"

    """
    The key for the base url setting.
    """
    keyBaseUrl = "baseurl"

    """
    The key for the proxy server setting.
    """
    keyProxy = "proxy"

    """
    The default value for the base URL setting.
    """
    defaultBaseUrl = "https://data.nsslabs.com"

    """
    The default value for the interval
    """
    defaultInterval = 600

    """
    The password mask.
    """
    passwordMask = "**********"

    """
    Reads the existing and/or default values 
    """
    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT or admin.ACTION_CREATE:
            for arg in [self.keyUsername, self.keyPassword, self.keyBaseUrl, self.keyInterval, self.keyProxy]:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf(self.configFile)        
        if confDict != None:
            for stanza, settings in confDict.items():
                for key, val in settings.items():
                    if key == self.defaultBaseUrl and val in [None, ""]:
                        val = self.defaultBaseUrl
                    if key == self.keyInterval:
                        if val in [None, ""] or int(val) < self.defaultInterval:
                            val = self.defaultInterval
                    if key == self.keyPassword:
                        val = self.passwordMask
                    if key == self.keyProxy:
                        if val == None:
                            val = ""
                    confInfo[stanza].append(key, val)
    
    def handleEdit(self, confInfo):
        name = self.callerArgs.id
        args = self.callerArgs
        
        if self.callerArgs.data[self.keyProxy][0] == None:
            self.callerArgs.data[self.keyProxy][0] = ""
        
        if self.callerArgs.data[self.keyBaseUrl][0] in [None, ""]:
            self.callerArgs.data[self.keyBaseUrl][0] = self.defaultBaseUrl
        
        #
        #  Set the default interval if it is not set or an invalid value.
        #
        try:            
            intervalArg = int(self.callerArgs.data[self.keyInterval][0])
        except TypeError as typeerror:
            intervalArg = self.defaultInterval
        
        if intervalArg < self.defaultInterval:
            intervalArg = self.defaultInterval

        self.callerArgs.data[self.keyInterval][0] = str(intervalArg)
        
        #  Store the clear password so it can be set in storage/passwords
        #  and then set the callerArgs value to the password mask.
        clear_password = self.callerArgs.data[self.keyPassword][0]
        self.callerArgs.data[self.keyPassword][0] = self.passwordMask

        try:
            #  Only update the storage/passwords if a password has been entered.
            if clear_password not in [None, "", self.passwordMask]:
                self.writeCreds(self.callerArgs.data[self.keyUsername][0], clear_password)
        except Exception as ex:
            logging.error("Error updating credentials: %s" % ex)
        
        try:
            #Write username, password mask, baseurl, interval, and proxy to inputs.conf
            self.writeInputConf(
                self.callerArgs.data[self.keyUsername][0],
                self.callerArgs.data[self.keyBaseUrl][0],
                self.callerArgs.data[self.keyInterval][0],
                self.callerArgs.data[self.keyProxy][0])
        except Exception as ex:
            logging.error("Error updating modular input configuration: %s" % ex)

        try:
            #Write username, password mask, baseurl, interval, and proxy address to cawsconfig.conf                
            self.writeConf(self.configFile, self.configStanza, self.callerArgs.data)
        except Exception as ex:
            logging.error("Error writing configuration: %s" % ex)

    def writeInputConf(self, username, baseurl, interval, proxy):
        try:
            item = None
            sessionKey = self.getSessionKey()
            args = {"token": sessionKey}
            service = client.connect(**args)

            kwargs = {
                "username": username,
                "password": self.passwordMask,
                "baseurl": baseurl,
                "interval": interval,
                "proxy": proxy
            }

            for input in service.inputs.iter():
                if input.name == self.inputName and input.kind == self.inputKind:
                    item = input

            if item != None:
                item.update(**kwargs)                
            else:
                item = service.inputs.create(self.inputName, self.inputKind, **kwargs)
            
            item.refresh()
        except Exception as ex:
            raise Exception("Error updating input.conf: %s" % ex)

    def writeCreds(self, username, password):
        """
        Encrpyt the password for the modular input.
        """

        sessionKey = self.getSessionKey()
        args = {"token": sessionKey}
        service = client.connect(**args)

        try:            
            for storage_password in service.storage_passwords:
                if storage_password.username == username:                    
                    service.storage_passwords.delete(username=username)
                    break            
        except Exception as ex:
            logging.debug("Error removing existing credentials: %s" % ex)
        
        try:
            service.storage_passwords.create(password, username)
        except Exception as ex:
            logging.debug("Error creating credentials: %s" % ex)

admin.init(CawsConfig, admin.CONTEXT_NONE)