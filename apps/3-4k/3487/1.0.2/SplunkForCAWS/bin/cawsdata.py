import sys, os, stat
import json, hashlib, base64
import urllib, urllib2, ssl
import time
import logging
from datetime import datetime, timedelta
from splunklib.modularinput import *
import splunklib.client as client
import caws.cawsutility as cawsutility

logging.root
logging.root.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler(stream=sys.stderr)
handler.setFormatter(formatter)
logging.root.addHandler(handler)

class CawsDataModularInput(Script):
    """  
    A modular input to pull threats and bypasses from the CAWS API.    
    """

    """
    The default day count if no checkpoint files exist.
    """
    defaultDayCount = 365

    """
    Defines the string used to mask the modular input password field.
    """
    passwordMask = "**********"

    def getCredentials(self, inputName, inputItem):
        """
        Get the CAWS API user credentials for the current input.
        """
        sessionKey = str(self._input_definition.metadata["session_key"])
        username = str(inputItem["username"])
        password = str(inputItem["password"])
        
        try:
            if password != self.passwordMask:
                self.encryptPassword(username, password, sessionKey)
                self.maskPassword(sessionKey, username, inputName)
            password = self.getClearPassword(sessionKey, username)
        except Exception as ex:
            raise Exception("Error getting credentials: %s" % ex)

        return username, password

    def encryptPassword(self, username, password, sessionKey):
        """
        Encrpyt the password for the modular input.
        """
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

    def maskPassword(self, sessionKey, username, inputName):
        """
        Masks the modular input password.
        """
        try:
            item = None
            args = {'token':sessionKey}
            service = client.connect(**args)
            
            kind, inputName = inputName.split("://")
            for input in service.inputs.iter():
                if input.name == inputName and input.kind == kind:
                    item = input
            
            if item != None:
                kwargs = {
                    "username": username,
                    "password": self.passwordMask,
                    "baseurl": item.content["baseurl"],
                    "interval": item.content["interval"],
                    "proxy": item.content["proxy"]
                }

        except Exception as ex:
            raise Exception("Error updating input.conf: %s" % ex)

    def getClearPassword(self, sessionKey, username):
        """
        Gets the credentials required to access the CAWS API
        """
        try:
            args = {'token':sessionKey}
            service = client.connect(**args)

            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    return storage_password.content.clear_password
        except Exception as ex:
            raise Exception("Error retrieving password: %s" % ex)

    def getCheckpointData(self, filename):
        """
        Gets the timestamp of the checkpoint file.
        """
        checkpointPath = os.path.join(self._input_definition.metadata["checkpoint_dir"], filename)
        if os.path.exists(checkpointPath) == False:
            return None
        
        timestamp = os.path.getmtime(checkpointPath)        
        return datetime.fromtimestamp(timestamp)
    
    def setCheckpointData(self, filename):
        """
        Updates the checkpoint file so that it reflects the latest timestamp that the modular input ran.
        """
        #  Delete the file if it exists.
        checkpointPath = os.path.join(self._input_definition.metadata["checkpoint_dir"], filename)
        if os.path.exists(checkpointPath):
            os.remove(checkpointPath)
        
        file = open(checkpointPath, "w")
        file.close()
    
    def streamThreatEvents(self, ew, inputName, username, password, baseUrl, proxy):
        checkpointFile = "threatsCheckpoint"
        endpointUrl = "integration/organization/threats"
        sourceType = "caws:threat"
        endDate = datetime.today()
        startDate = endDate - timedelta(self.defaultDayCount)

        try:
            latestTimestamp = self.getCheckpointData(checkpointFile)
            if latestTimestamp != None:
                startDate = latestTimestamp
        except IOError as ioerr:
            ew.log(EventWriter.ERROR, "I/O Error reading threatsCheckpoint data: %s" % ioerr)

        try:
            self.setCheckpointData(checkpointFile)
        except IOError as ioerror:
            ew.log(EventWriter.ERROR, "I/O Error writing threatsCheckpoint data: %s" % ioerror)
        except TypeError as typeerror:
            ew.log(EventWriter.ERROR, "Type Error writing threatsCheckpoint data: %s" % typeerror)
        except Exception as ex:
            ew.log(EventWriter.ERROR, "Error writing threatsCheckpoint data: %s" % ex)

        requestUrl = "%s/%s" % (baseUrl, endpointUrl)
        query = {'startDate': startDate.isoformat(), 'endDate': endDate.isoformat()}

        threats = []
        try:
            threats = cawsutility.make_paged_request(username, password, requestUrl, query, "Threats", proxy)
        except urllib2.HTTPError as httperror:            
            ew.log(EventWriter.ERROR, "An http error occurred: %s" % httperror)
        except Exception as ex:
            ew.log(EventWriter.ERROR, "Error making api request: %s" % ex)

        try:
            for threat in threats:
                timestamp = cawsutility.get_iso_date(threat["DetectionDate"])
                event = Event(
                    data = json.dumps(threat),
                    stanza = inputName,
                    host = baseUrl,
                    sourcetype = sourceType,
                    time = time.mktime(timestamp.timetuple())
                )
                ew.write_event(event)
        except Exception as ex:
            ew.log(EventWriter.ERROR, "Error writing events: %s" % ex)        

    def streamBypassEvents(self, ew, inputName, username, password, baseUrl, https_proxy):
        checkpointFile = "bypassCheckpoint"
        endpointUrl = "integration/organization/bypasses"
        sourceType = "caws:bypass"
        endDate = datetime.today()        
        startDate = endDate - timedelta(self.defaultDayCount)

        try:
            latestTimestamp = self.getCheckpointData(checkpointFile)
            if latestTimestamp != None:
                startDate = latestTimestamp
        except IOError as ioerr:
            ew.log(EventWriter.ERROR, "I/O Error reading bypassCheckpoint data: %s" % ioerr)

        requestUrl = "%s/%s" % (baseUrl, endpointUrl)
        query = {'startDate': startDate.isoformat(), 'endDate': endDate.isoformat()}

        response = None
        success = False
        try:            
            response = cawsutility.make_api_request(username, password, requestUrl, query, https_proxy)
            success = True
        except TypeError as typeerror:
            ew.log(EventWriter.ERROR, "Type Error: %s" % typeerror)
        except urllib2.HTTPError as httperror:
            ew.log(EventWriter.ERROR, "An http error occurred: %s" % httperror)
        except Exception as ex:                
            ew.log(EventWriter.ERROR, "An unknown error occurred while making a API request: %s" % ex)

        if success:
            try:
                self.setCheckpointData(checkpointFile)
            except IOError as ioerror:
                ew.log(EventWriter.ERROR, "I/O Error writing bypassCheckpoint data: %s" % ioerror)
            except TypeError as typeerror:
                ew.log(EventWriter.ERROR, "Type Error writing bypassCheckpoint data: %s" % typeerror)
            except Exception as ex:
                ew.log(EventWriter.ERROR, "Error writing bypassCheckpoint data: %s" % ex)

        alerts = []
        if response != None:
            alerts = json.loads(response)

        try:
            for alert in alerts:
                timestamp = cawsutility.get_iso_date(alert["ReplayDate"])
                event = Event(                    
                    data = json.dumps(alert),
                    stanza = inputName,
                    host = baseUrl,
                    sourcetype = sourceType,
                    time = time.mktime(timestamp.timetuple())
                )                
                ew.write_event(event)
        except Exception as ex:
            ew.log(EventWriter.ERROR, "Error writing events: %s" % ex)

    def validate_input(self, validation_definition):
        """
        Implementation of Splunk Script class's validate_input method.
        """
        endpointUrl = "integration/organization/bypasses"
        sessionKey = validation_definition.metadata["session_key"]
        username = validation_definition.parameters["username"]
        password = validation_definition.parameters["password"]
        baseurl = validation_definition.parameters["baseurl"]
        proxy = validation_definition.parameters["proxy"]

        if password == self.passwordMask:
            password = self.getClearPassword(sessionKey, username)

        if len(username) == 0:
            raise ValueError("username is a required parameter")

        if len(password) == 0:
            raise ValueError("password is a required parameter")

        if len(baseurl) == 0:
            raise ValueError("baseurl is a required parameter")
        
        requestUrl = "%s/%s" % (baseurl, endpointUrl)

        startDate = datetime.today() - timedelta(1)
        endDate = datetime.today()
        query = {'startDate': startDate.isoformat(), 'endDate': endDate.isoformat()}
        response = cawsutility.make_api_request(username, password, requestUrl, query, proxy)
        
        if response == None:
            raise ValueError("Invalid CAWS username/password, privileges, or url")

    def get_scheme(self):
        """
        Implementation of the Splunk Script class's get_scheme method.
        """
        scheme = Scheme("NSS Labs' CAWS API Data")
        scheme.description = "Allows Splunk users to receive threat details and bypass notifications from NSS Labs' Cyber Advanced Warning System"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        usernameArgument = Argument("username")
        usernameArgument.title = "CAWS API Username"
        usernameArgument.data_type = Argument.data_type_string
        usernameArgument.description = "CAWS API Username"
        usernameArgument.required_on_create = True
        scheme.add_argument(usernameArgument)

        passwordArgument = Argument("password")
        passwordArgument.title = "CAWS API Password"
        passwordArgument.data_type = Argument.data_type_string
        passwordArgument.description = "The CAWS API password"
        passwordArgument.required_on_create = True
        scheme.add_argument(passwordArgument)

        baseurlArgument = Argument("baseurl")
        baseurlArgument.title = "CAWS API URL"
        baseurlArgument.data_type = Argument.data_type_string
        baseurlArgument.description = "The CAWS API URL (https://data.nsslabs.com)"
        baseurlArgument.required_on_create = True
        scheme.add_argument(baseurlArgument)

        proxyArgument = Argument("proxy")
        proxyArgument.title = "Proxy Server"
        proxyArgument.data_type = Argument.data_type_string
        proxyArgument.description = "Proxy Server (optional)"
        proxyArgument.required_on_create = False
        scheme.add_argument(proxyArgument)
        
        return scheme
    
    def stream_events(self, inputs, ew):
        for inputName, inputItem in inputs.inputs.iteritems():
            baseurl = str(inputItem["baseurl"])
            try:
                proxy = inputItem["proxy"]
            except Exception:
                proxy = ''
            username, password = self.getCredentials(inputName, inputItem)
            self.streamBypassEvents(ew, inputName, username, password, baseurl, proxy)
            self.streamThreatEvents(ew, inputName, username, password, baseurl, proxy)

if __name__ == "__main__":
    sys.exit(CawsDataModularInput().run(sys.argv))