import datetime
import time
import os
import sys
import logging
import requests
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.client import Service
from splunklib.six.moves.urllib.parse import urlsplit
from splunklib.modularinput import *
from splunklib import six

if sys.version_info[0] == 3:
    from urllib.parse import urlencode
else:
    from six.moves.urllib.parse import urlencode

logging.root    
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

class MyScript(Script):

    PAGE_LENGTH = 2147483647

    def __init__(self):
        Script.__init__(self)
        self._app_service = None

    def get_scheme(self):       
        scheme = Scheme("Workplace activity")

        scheme.description = "Pulling OS33 workplace activity. Config through Workplace By OS33"
        scheme.use_external_validation = True
        scheme.use_single_instance = False

        uri_argument = Argument("uri")
        uri_argument.title = "Uri"
        uri_argument.data_type = Argument.data_type_string
        uri_argument.description = ""
        uri_argument.required_on_create = True
        scheme.add_argument(uri_argument)

        return scheme

    def validate_input(self, validation_definition):
        return

    def stream_events(self, inputs, ew):
        for input_name, input_item in six.iteritems(inputs.inputs):            
            checkpoint_filepath = self.get_checkpoint_filepath(inputs.metadata["checkpoint_dir"], input_name)
            checkpoint_date = self.get_checkpoint_date(checkpoint_filepath)
            end_date = datetime.datetime.utcnow() - datetime.timedelta(minutes=5)

            page_date = checkpoint_date + datetime.timedelta(days=1)
            while True:
                if (page_date >= end_date):
                    self.import_activity(checkpoint_date, end_date, input_name, input_item, checkpoint_filepath, ew)
                    break
                self.import_activity(checkpoint_date, page_date, input_name, input_item, checkpoint_filepath, ew)
                checkpoint_date = page_date
                page_date = checkpoint_date + datetime.timedelta(days=1)                                

    def import_activity(self, checkpoint_date, end_date, input_name, input_item, checkpoint_filepath, ew):
        credentials = self.get_credentials()
        app_config = self.get_app_config()
        access_token = self.get_access_token(app_config, credentials)
        checkpoint_iso_date = self.iso_format(checkpoint_date)
        end_iso_date = self.iso_format(end_date)

        logging.info("Input: %s, start pulling from %s to %s" % (input_name, checkpoint_iso_date, end_iso_date))
        
        activity_uri = "%s%s?%s" % (app_config["workplace_params"]["uri"], input_item["uri"], self.get_query(1, checkpoint_iso_date, end_iso_date))
        headers = {"Authorization": "Bearer %s" % (access_token)}
        response = requests.get(activity_uri, headers=headers)
        if (response.status_code == 400):
            raise requests.HTTPError("Bad request. %s" % response.text, response=response)
        response.raise_for_status()

        data = response.json()
        data.sort(key = self.sort_by_date)
        if len(data) > 0:
            logging.info("Input: %s, pulling %s activities" % (input_name, len(data)))
            try:
                for item in data:
                    event = Event()
                    event.stanza = str(input_name)
                    event.data = json.dumps(item)
                    event.time = time.mktime(self.from_iso_string(item["Timestamp"]).timetuple())
                    ew.write_event(event)
                    checkpoint_iso_date = item["Timestamp"]
                    
                logging.info("Input: %s, pulling finished" % (input_name))
            except:
                logging.info("Input: %s, import failed" % (input_name))
                self.set_checkpoint(checkpoint_filepath, checkpoint_iso_date)
                raise
        else:
            logging.info("Input: %s, not found new activities" % (input_name))

        self.set_checkpoint(checkpoint_filepath, end_iso_date)


    def from_iso_string(self, date_string):
        try:
            return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            return datetime.datetime.strptime(date_string, "%Y-%m-%dT%H:%M:%SZ")

    def get_query(self, page_number, start_date, finish_date):
        params = {
            "PageNumber": page_number,
            "PageLength": self.PAGE_LENGTH,            
            "TimeStamp": finish_date,
            "PageTimeStamp": finish_date,
            "StartTimeStamp": start_date
        }
    
        return urlencode(params)

    def get_app_config(self):
        app_config = {}
        workplace_conf = self.app_service.confs["workplace"]
        for stanza in workplace_conf.list():
            app_config[stanza.name] = {}
            for k, v in six.iteritems(stanza.content):
                app_config[stanza.name][k] = v
        return app_config

    def get_credentials(self):
        credentials = {}
        storage_passwords = self.app_service.storage_passwords
        for storage_password in storage_passwords:
            credentials[storage_password.username] = storage_password.clear_password
        return credentials

    def sort_by_date(self, item):
        return item["Timestamp"]

    def get_access_token(self, app_config, credentials):
        token_info = self.get_token_info(credentials)        
        if (token_info is None or (datetime.datetime.utcnow() + datetime.timedelta(minutes=3)) > self.from_iso_string(token_info["expires_in"])):
            token_info = self.update_token(app_config, credentials, token_info)
            self.save_token_info(token_info)
        
        return token_info["access_token"]

    def get_token_info(self, credentials):
        token_info_string = credentials.get("token_info")
        if (token_info_string is None):
            return None
        
        return json.loads(token_info_string)    

    def update_token(self, app_config, credentials, token_info):
        params = {}
        params["grant_type"] = "refresh_token"
        params["client_id"] = credentials["client_id"]
        params["client_secret"] = credentials["client_secret"]
        if (token_info is not None):
            params["refresh_token"] = token_info["refresh_token"]
        else:
            params["refresh_token"] = credentials["refresh_token"]

        oauth2_token_endpoint = app_config["workplace_params"]["uri"] + app_config["oauth_params"]["oauth2_token_endpoint"]
        headers = {"content-type": "application/x-www-form-urlencoded"}
        token_response = requests.post(oauth2_token_endpoint, data=params, headers=headers)
        token_response.raise_for_status()

        token_info = json.loads(token_response.text)
        token_info["expires_in"] = self.iso_format(datetime.datetime.utcnow() + datetime.timedelta(seconds=token_info["expires_in"]))
        return token_info        

    def save_token_info(self, token_info):
        storage_passwords = self.app_service.storage_passwords
        realm = "activity_rest_api"
        name = "token_info"
        try:
            storage_passwords.delete(name, realm)
        except KeyError:
            pass

        storage_passwords.create(json.dumps(token_info), name, realm)
        
    def get_checkpoint_filepath(self, checkpoint_dir, name):
        input_name = name.split('://')[1]
        return os.path.join(checkpoint_dir, "%s.txt" % (input_name))

    def get_checkpoint_date(self, checkpoint_filepath):
        try:            
            with open(checkpoint_filepath, "r") as f:
                checkpoint_date_string = f.read()
                checkpoint_date = self.from_iso_string(checkpoint_date_string)
                return checkpoint_date
        except:
            now = datetime.datetime.utcnow()
            return now - datetime.timedelta(days=1)

    def iso_format(self, date):
        return date.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'

    def set_checkpoint(self, filepath, date):
        if not os.path.exists(os.path.dirname(filepath)):
            try:
                os.makedirs(os.path.dirname(filepath))
            except OSError as exc:
                if exc.errno != errno.EEXIST:
                    raise

        with open(filepath, "w") as f:
            f.write(date)

    @property
    def app_service(self):       
        if self._app_service is not None:
            return self._app_service

        if self._input_definition is None:
            return None

        splunkd_uri = self._input_definition.metadata["server_uri"]
        session_key = self._input_definition.metadata["session_key"]

        splunkd = urlsplit(splunkd_uri, allow_fragments=False)

        self._app_service = Service(
            scheme=splunkd.scheme,
            host=splunkd.hostname,
            port=splunkd.port,
            token=session_key,            
            owner="nobody",
            app="workplace"
        )

        return self._app_service

if __name__ == "__main__":
    sys.exit(MyScript().run(sys.argv))