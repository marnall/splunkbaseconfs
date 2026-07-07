import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import datetime
import requests
import json
import logging
import logging.handlers
import splunklib.client as client
from splunklib.modularinput import Script, Scheme, Argument, Event


class Stryd(Script):

    MASK = "********"
    APP = __file__.split(os.sep)[-3]

    def __init__(self):
        # Setup the logging handler
        self.logger = self.setup_logger(logging.INFO)

    # Setup a custom logger, logs to $SPLUNK_HOME/var/log/splunk/$APP$.log.
    def setup_logger(self, level):
        app = self.APP.lower()
        logger = logging.getLogger(app)
        logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
        logger.setLevel(level)

        file_handler = logging.handlers.RotatingFileHandler("{}/var/log/splunk/{}.log".format(os.environ['SPLUNK_HOME'], app), maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def get_scheme(self):
        # Setup the data inputs
        scheme = Scheme("Stryd")
        scheme.description = "Imports running power data from Stryd."
        username = Argument("username")
        password = Argument("password")
        scheme.add_argument(username)
        scheme.add_argument(password)
        return scheme

    def validate_input(self, validation_definition):
        pass

    def encrypt_password(self, username, password, session_key):
        args = {'token': session_key}
        service = client.connect(**args)

        try:
            for storage_password in service.storage_passwords:
                if storage_password.username == username and storage_password.realm == self.APP:
                    service.storage_passwords.delete(username=storage_password.username, realm=storage_password.realm)

            service.storage_passwords.create(password, username, self.APP)

        except Exception as e:
            raise Exception("An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: {}".format(e))

    def mask_password(self, session_key, username):
        try:
            args = {'token': session_key}
            service = client.connect(**args)
            kind, input_name = self.input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))

            kwargs = {
                "username": username,
                "password": self.MASK,
            }
            item.update(**kwargs).refresh()

        except Exception as e:
            raise Exception("Error masking password: {}".format(e))

    def get_password(self, session_key, username):
        args = {'token': session_key}
        service = client.connect(**args)

        for storage_password in service.storage_passwords:
            if storage_password.username == username and storage_password.realm == self.APP:
                return storage_password.content.clear_password

    def get_last_activity(self, session_key):
        args = {'token': session_key, 'owner': 'nobody', 'app': self.APP}
        service = client.connect(**args)

        kind, input_name = self.input_name.split("://")
        input_name = "{}".format(input_name)
        kvcollection = self.APP

        last_activity = None
        token = None
        collection = service.kvstore[kvcollection]
        try:
            get_item = collection.data.query_by_id(input_name)
            if get_item:
                last_activity = get_item['last_activity']
                token = get_item['token']
        except Exception:
            pass
        return last_activity, token

    def set_last_activity(self, session_key, last_activity, token):
        args = {'token': session_key, 'owner': 'nobody', 'app': self.APP}
        service = client.connect(**args)

        kind, input_name = self.input_name.split("://")
        input_name = "{}".format(input_name)
        kvcollection = self.APP

        collection = service.kvstore[kvcollection]
        # Update record, if it fails it doesn't exist so create it.
        try:
            collection.data.update(input_name, json.dumps({'last_activity': last_activity, 'token': token}))
        except Exception:
            collection.data.insert(json.dumps({"_key": input_name, "last_activity": last_activity, 'token': token}))

    def auth_stryd_session(self, username, password):
        auth = {"email": username, "password": password}
        response = requests.post("https://www.stryd.com/b/email/signin", json=auth)
        if response.status_code != 200:
            raise Exception("Stryd authentication failed.")
        else:
            response_json = response.json()
            token = response_json['token']
        return token

    def get_stryd_data(self, token, start_date=None, end_date=None):
        headers = {'Authorization': 'Bearer: {}'.format(token)}
        if start_date:
            url = "https://www.stryd.com/b/api/v1/activities/calendar?srtDate={start_date}&endDate={end_date}&sortBy=Timestamp?order=asc".format(start_date=start_date.strftime("%m-%d-%Y"), end_date=end_date.strftime("%m-%d-%Y"))
        else:
            url = "https://www.stryd.com/b/api/v1/activities/calendar?order=asc&sortby=Timestamp"
        response = requests.get(url, headers=headers)
        return response.json()

    def test_token(self, token):
        headers = {'Authorization': 'Bearer: {}'.format(token)}
        url = "https://www.stryd.com/b/api/v1/users/device"
        response = requests.get(url, headers=headers)
        if response.status_code != 200:
            return False
        else:
            return True

    def stream_events(self, inputs, ew):

        # Get inputs
        for self.input_name, self.input_item in inputs.inputs.items():
            username = self.input_item["username"]
            password = self.input_item["password"]

        session_key = self._input_definition.metadata["session_key"]

        try:
            # If the password is not masked, mask it.
            if password != self.MASK:
                self.encrypt_password(username, password, session_key)
                self.mask_password(session_key, username)

        except Exception as e:
            self.logger.error("Error: {}".format(e))

        # Use clear_password for API authentication
        clear_password = self.get_password(session_key, username)

        try:
            last_activity, token = self.get_last_activity(session_key)
            self.logger.info("Authenticating to Stryd...")

            # If no token, get one. If token exists, test it to ensure it's still valid.
            if not token:
                token = self.auth_stryd_session(username, clear_password)
            else:
                if not self.test_token(token):
                    self.logger.info("API token expired, getting new token.")
                    token = self.auth_stryd_session(username, clear_password)

            # If no last_activity, get all data. Otherwise only new activities since last_activity.
            if not last_activity:
                self.logger.info("No previous activity found, getting all Stryd data.")
                response = self.get_stryd_data(token)
            else:
                end_date = datetime.datetime.now() + datetime.timedelta(days=1)  # Pass tomorrow's date to ensure no issues with timezones
                start_date = datetime.datetime.utcfromtimestamp(last_activity)
                response = self.get_stryd_data(token, start_date, end_date)

            for item in response['activities']:
                last_activity, _ = self.get_last_activity(session_key)
                if last_activity is None or last_activity < item['timestamp']:
                    self.logger.info("Found activity '{}' ({})".format(item['name'], item['id']))

                    # Write event to Splunk
                    event = Event(stanza=self.input_name, sourcetype="stryd:activities", data=json.dumps(item))
                    ew.write_event(event)

                    # Update the KV store with the latest timestamp
                    self.set_last_activity(session_key, item['timestamp'], token)
            self.logger.info("Looks like we have all activities.")

        except Exception as e:
            self.logger.error(e)


if __name__ == "__main__":
    sys.exit(Stryd().run(sys.argv))
