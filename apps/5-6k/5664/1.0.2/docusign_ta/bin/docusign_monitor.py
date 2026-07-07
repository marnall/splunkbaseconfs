#############################################
#
# DocuSign Add-on for Splunk - Monitor Input
#
# ==========
# For support, please e-mail dsmonitorfeedback@docusign.com
#

import os
import sys
import json
import requests
import math
from hashlib import md5
import time
import random
import logging
import logging.handlers
import urllib.parse

sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), "lib"))

import splunklib.client as client
from splunklib.modularinput import *
import jwt
import dateutil.parser as dp
import constants

######################################################
##-- Logging class definitions
class DocuSignLogFilter(logging.Filter):
    def filter(self, record):
        record.invocation_id = INVOCATION_ID
        return True

class DocuSignLogFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            s = time.strftime(datefmt, ct)
        else:
            t  = time.strftime("%Y-%m-%d %H:%M:%S", ct)
            s  = "%s,%03d+0000" % (t, record.msecs)
        return s

######################################################
##-- Helper function to setup the logging
def setup_logger(log_name):
    loginst = logging.getLogger(log_name)
    loginst.propagate = False
    loginst.addFilter(DocuSignLogFilter())
    loginst.setLevel(logging.INFO)

    file_handler = logging.handlers.RotatingFileHandler(os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk',log_name+'.log'), maxBytes=25000000, backupCount=5) 
    DocuSignLogFormatter.converter = time.gmtime
    formatter = DocuSignLogFormatter('%(asctime)s %(levelname)s invocation_id=%(invocation_id)s %(message)s')
    file_handler.setFormatter(formatter)
    loginst.addHandler(file_handler)

    return loginst

class ModInputDocuSign_Monitor(Script):

    # Define some global variables
    INPUT_TYPE = "docusign_monitor"
    MASK = "*********"

    def get_scheme(self):
        """ Called by Splunk to determine the configuration inputs for this module. """

        scheme = Scheme("DocuSign Monitor")
        scheme.description = ("Ingests DocuSign Monitor data")
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        auth_server_arg = Argument(
            name="authServer",
            title="Auth Server",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(auth_server_arg)

        lens_url_arg = Argument(
            name="lensUrl",
            title="Lens Server URL",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(lens_url_arg)

        user_arg = Argument(
            name="userId",
            title="User Id",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(user_arg)

        client_arg = Argument(
            name="clientId",
            title="Integrator Key",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(client_arg)

        rsa_arg = Argument(
            name="rsaKey",
            title="RSA Private Key",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(rsa_arg)

        fetch_arg = Argument(
            name="fetchLimit",
            title="Fetch Limit",
            data_type=Argument.data_type_string,
            required_on_create=True,
            required_on_edit=True
        )
        scheme.add_argument(fetch_arg)

        return scheme

    def validate_input(self, definition):
        """ Called by Splunk to validate the user inputs for the module. """

        userId      = definition.parameters["userId"]
        clientId    = definition.parameters["clientId"]
        rsaKey      = definition.parameters["rsaKey"]
        lensUrl     = definition.parameters["lensUrl"]
        authServer  = definition.parameters["authServer"]

        if not userId:
            raise ValueError("User Id is required")

        if not clientId:
            raise ValueError("Integrator Key is required")

        if not rsaKey:
            raise ValueError("RSA Private Key is required")

        if not lensUrl.lower().startswith('https://'):
            raise ValueError("Lens Server URL must use https")

        if not authServer.lower().startswith('https://'):
            raise ValueError("Auth Server URL must use https")

    def get_encoded_file_path(self,input_name):
        """ Encode the URL (simply to make the file name recognizable). """

        name = ""
        for i in range(len(input_name)):
            if input_name[i].isalnum():
                name += input_name[i]
            else:
                name += "_"

        ## MD5 the URL
        m = md5()
        m.update(input_name.encode('utf-8'))
        name += "_" + m.hexdigest()

        return name

    def get_current_checkpoint(self,name,checkpoint_dir):
        """ Loads the previous cursor checkpoint from disk to resume the integration with. """

        try:
            filepath = os.path.join(checkpoint_dir, name)
            file = open(filepath, "r")
            existingCheckPoint = file.read()
            file.close()
            return existingCheckPoint
        except Exception as e:
            return ""

    def update_checkpoint(self,cursor,name,checkpoint_dir):
        """ Updates the new cursor on disk for the subsequent module run. """

        try:
            filepath = os.path.join(checkpoint_dir, name)
            file = open(filepath, "w")
            file.write(str(cursor))
            file.close()
        except Exception as e:
            raise Exception("Error updating cursor: %s" % str(e))

    def encrypt_password(self, input_name, param, value, session_key):
        """ Encrypts the RSA Private Key and puts it into Splunk's password storage. """

        args = {'token':session_key}
        service = client.connect(**args)

        try:
            input_kind, input_title = input_name.split("://")
            input_kind = input_kind+"-"+param

            ## If the credential already exists, delte it.
            for storage_password in service.storage_passwords:
                if storage_password.realm == input_kind and storage_password.username == input_title:
                    service.storage_passwords.delete(storage_password.username,storage_password.realm)
                    break

            ## Create the credential.
            service.storage_passwords.create(value, input_title, input_kind)

        except Exception as e:
            raise Exception("An error occurred updating credentials - check Splunk Logs for more info")

    def mask_password(self, session_key, input_name, userId, clientId, rsaKey, authServer, lensUrl, fetchLimit):
        """ Updates the Modular Input configuration with the masked version of the RSA Private Key. """

        try:
            args = {'token':session_key}
            service = client.connect(**args)
            input_kind, input_title = input_name.split("://")
            item = service.inputs.__getitem__((input_title, input_kind))

            kwargs = {
                "userId": userId,
                "clientId": clientId,
                "rsaKey": rsaKey,
                "authServer": authServer,
                "lensUrl": lensUrl,
                "fetchLimit": fetchLimit
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception("Error updating inputs.conf: %s" % str(e))

    def get_password(self, session_key, input_name, param):
        """ Retrieves the encrypted password from Splunk's password storage. """

        args = {'token':session_key}
        service = client.connect(**args)

        input_kind, input_title = input_name.split("://")
        input_kind = input_kind+"-"+param

        ## Retrieve the password from the storage/passwords endpoint
        for storage_password in service.storage_passwords:
            if storage_password.realm == input_kind and storage_password.username == input_title:
                return storage_password.content.clear_password

    def get_access_token(self, authServer, userId, clientId, rsaKeyClear):
        """ Constructs a JWT and calls into DS authentication to gain an access token. """

        ## Perform some clean up in case splunk saves these without newline characters
        rsaKeyClear = rsaKeyClear.replace("-----BEGIN RSA PRIVATE KEY----- ", "-----BEGIN RSA PRIVATE KEY-----\n")
        rsaKeyClear = rsaKeyClear.replace(" -----END RSA PRIVATE KEY-----", "\n-----END RSA PRIVATE KEY-----")

        ## Extract the hostname from the authServer URL to be used in the JWT claim
        parsed_authServer = urllib.parse.urlparse(authServer)

        now = math.floor(time.time())
        later = now + 3600
        claim = {"iss": clientId, "aud": parsed_authServer.netloc, "iat": now, "exp": later, "scope": "impersonation", "sub": userId}
        token = jwt.encode(payload=claim, key=rsaKeyClear, algorithm='RS256')

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "User-Agent": constants.USER_AGENT
        }

        response_data = requests.post(authServer, headers=headers, json={
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": token.decode('utf-8')
        })

        logger.info("access_response=%s" % response_data.status_code)

        if response_data.status_code != 200:
            raise Exception("Error occurred getting access token, please check your configuration values")

        response = response_data.json()

        return response['access_token']

    def get_and_write_events(self, ew, lensUrl, access_token, fetchLimit, cursor):
        """ Main integration point with DS Monitor. Calls using previous run's end cursor to resume from. """

        headers = {
            "Authorization": f"Bearer {access_token}",
            "User-Agent": constants.USER_AGENT
        }

        try:
            if not lensUrl.lower().startswith('https://'):
                raise Exception("Lens Server URL must use https")

            response = requests.get(
                lensUrl,
                params={'cursor': cursor, 'limit': fetchLimit},
                headers=headers,
                timeout=120
            )

            logger.info("events_response=%s" % response.status_code)

            if response.status_code != 200:
                raise Exception("Error occurred getting lens data: %s" % response.text)

            lens_data = response.json()

            if len(lens_data['data']) == 0:
                logger.info(f'events_received=0 from cursor={cursor}')
                return lens_data["endCursor"]

            ## Write out all the events to the event writer, override the timestamp with the event's timestamp
            for ev in lens_data["data"]:
                parsed_t = dp.parse(ev['timestamp'])
                event = Event()
                event.time = parsed_t.timestamp()
                event.data = json.dumps(ev)
                ew.write_event(event)

            logger.info("events_received=%s from cursor=%s" % (len(lens_data["data"]),cursor))

            return lens_data["endCursor"]
        except Exception as e:
            raise Exception(f'ERROR: {str(e)}')

    def stream_events(self, inputs, ew):
        """ Entry point from Splunk to begin processing. """

        input_name, input_items = inputs.inputs.popitem()
        session_key = self._input_definition.metadata["session_key"]
        checkpoint_dir = self._input_definition.metadata['checkpoint_dir']
        authServer   = input_items['authServer']
        lensUrl   = input_items['lensUrl']
        userId   = input_items["userId"]
        clientId = input_items["clientId"]
        rsaKey   = input_items['rsaKey']
        fetchLimit   = input_items['fetchLimit']
        access_token = None
        password = None
        status = "unknown"

        logger.info('action=modinput_start type=%s input=%s' % (self.INPUT_TYPE, input_name))
        logger.info('action=config authServer=%s' % authServer)
        logger.info('action=config lensUrl=%s' % lensUrl)

        try:
            ## If the password is not masked, mask it.
            if rsaKey != self.MASK:
                self.encrypt_password(input_name, "rsaKey", rsaKey, session_key)
                self.mask_password(session_key, input_name, userId, clientId, self.MASK ,authServer, lensUrl, fetchLimit)
            if clientId != self.MASK:
                self.encrypt_password(input_name, "clientId" ,clientId, session_key)
                self.mask_password(session_key, input_name, userId, self.MASK, rsaKey, authServer, lensUrl, fetchLimit)

            clear_rsaKey = self.get_password(session_key, input_name,"rsaKey")
            clear_clientId = self.get_password(session_key, input_name, "clientId")

            chkpt_name = self.get_encoded_file_path(input_name)
            logger.info('action=config chkpt_name=%s' % chkpt_name)

            cursor = self.get_current_checkpoint(chkpt_name, checkpoint_dir)
            logger.info("action=state existing_cursor=%s" % cursor)

            access_token = self.get_access_token(authServer, userId, clear_clientId, clear_rsaKey)

            newCursor = self.get_and_write_events(ew, lensUrl, access_token, fetchLimit, cursor)
            logger.info("action=state new_cursor=%s" % newCursor)

            self.update_checkpoint(newCursor, chkpt_name, checkpoint_dir)
            status = "success"

        except Exception as e:
            logger.error("ERROR: %s" % str(e))
            status = "failed"

        logger.info('action=modinput_end input=%s status=%s' % (input_name, status))

if __name__ == "__main__":

    ## Create a unique identifier for this invocation
    INVOCATION_ID   = str(time.time()) + ':' + str(random.randint(0, 100000))

    ## Setup the logging for the modinput runs
    logger = setup_logger(ModInputDocuSign_Monitor.INPUT_TYPE)

    ## Run the Modular Input
    exitcode = ModInputDocuSign_Monitor().run(sys.argv)
    sys.exit(exitcode)
