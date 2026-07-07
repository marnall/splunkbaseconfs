import os
import sys
import json
import logging
import logging.handlers
from datetime import datetime
import requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
# pylint: disable=wrong-import-position
import splunklib.client as client
from splunklib.modularinput import Script, Scheme, Argument, Event
# pylint: enable=wrong-import-position

class SplunkPolar(Script):
    """Creates Polar Data Input in Splunk and retrieves events from Polar API."""

    MASK = "********"
    APP = __file__.split(os.sep)[-3]

    def __init__(self):
        """Setup the logger and initialise variables."""
        super().__init__()
        self.logger = self.setup_logger(logging.INFO)
        self.input_name = ""
        self.input_item = ""

    # Setup a custom logger, logs to $SPLUNK_HOME/var/log/splunk/$APP.log.
    def setup_logger(self, level):
        """Define the logger details."""
        app = self.APP.lower()
        logger = logging.getLogger(app)
        # Prevent the log messages from being duplicated in the python.log file
        logger.propagate = False
        logger.setLevel(level)

        file_handler = logging.handlers.RotatingFileHandler("{}/var/log/splunk/{}.log".format(os.environ['SPLUNK_HOME'], app), maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def get_scheme(self):
        """Setup the data inputs."""
        scheme = Scheme("Polar")
        scheme.description = "Imports Polar exercises, daily activities and physical information."
        user_id = Argument("user_id")
        access_token = Argument("access_token")
        scheme.add_argument(user_id)
        scheme.add_argument(access_token)
        return scheme

    def encrypt_access_token(self, username, password, session_key):
        """Encrypt token using Splunk REST API."""
        args = {'token': session_key}
        service = client.connect(**args)

        try:
            for storage_password in service.storage_passwords:
                if storage_password.username == username and storage_password.realm == self.APP:
                    service.storage_passwords.delete(username=storage_password.username, realm=storage_password.realm)

            service.storage_passwords.create(password, username, self.APP)

        except Exception as ex:
            raise Exception(f'An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: {ex}') from ex

    def mask_access_token(self, session_key, user_id):
        """Mask token in Splunk GUI to show value of self.MASK"""
        try:
            args = {'token': session_key}
            service = client.connect(**args)
            kind, input_name = self.input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))

            kwargs = {
                "user_id": user_id,
                "access_token": self.MASK,
            }
            item.update(**kwargs).refresh()

        except Exception as ex:
            raise Exception(f'Error masking password: {ex}') from ex

    def get_clear_token(self, session_key, username):
        """Get cleartext token from Splunk REST API."""
        args = {'token': session_key}
        service = client.connect(**args)
        clear_pw = ""

        for storage_password in service.storage_passwords:
            if storage_password.username == username and storage_password.realm == self.APP:
                clear_pw = storage_password.content.clear_password
        return clear_pw

    def get_kvstore_data(self, session_key):
        """Get most recent dates for sleep and nightly recharge data."""
        try:
            nightly_recharge_last_date = None
            sleep_last_date = None

            args = {'token': session_key, 'owner': 'nobody', 'app': self.APP}
            service = client.connect(**args)

            _, input_name = self.input_name.split("://")
            kvcollection = self.APP

            collection = service.kvstore[kvcollection]
            get_item = collection.data.query_by_id(input_name)
            if get_item:
                nightly_recharge_last_date = datetime.strptime(get_item['nightly_recharge_last_date'], "%Y-%m-%d").date()
                sleep_last_date = datetime.strptime(get_item['sleep_last_date'], "%Y-%m-%d").date()
        except Exception as ex:
            self.logger.error(ex)

        return nightly_recharge_last_date, sleep_last_date

    def set_kvstore_data(self, session_key, data, new_date):
        """Update the KV Store with the most recent dates for sleep and nightly recharge data."""
        nightly_recharge_last_date = datetime.strptime("1970-01-01", "%Y-%m-%d").date()
        sleep_last_date = datetime.strptime("1970-01-01", "%Y-%m-%d").date()

        args = {'token': session_key, 'owner': 'nobody', 'app': self.APP}
        _, input_name = self.input_name.split("://")
        kvcollection = self.APP

        service = client.connect(**args)
        collection = service.kvstore[kvcollection]

        row = collection.data.query()
        # Read current values from KV Store
        if any(d.get('nightly_recharge_last_date') for d in row):
            nightly_recharge_last_date = datetime.strptime(row[0]['nightly_recharge_last_date'], "%Y-%m-%d").date()
        if any(d.get('sleep_last_date') for d in row):
            sleep_last_date = datetime.strptime(row[0]['sleep_last_date'], "%Y-%m-%d").date()

        if data == 'sleep' and new_date > sleep_last_date:
            sleep_last_date = new_date
        if data == 'nightly-recharge' and new_date > nightly_recharge_last_date:
            nightly_recharge_last_date = new_date

        # Update record, if it fails it doesn't exist so create it.
        try:
            collection.data.update(input_name, json.dumps({'nightly_recharge_last_date': nightly_recharge_last_date.strftime('%Y-%m-%d'), 'sleep_last_date': sleep_last_date.strftime('%Y-%m-%d')}))
        except Exception:
            collection.data.insert(json.dumps({"_key": input_name, 'nightly_recharge_last_date': nightly_recharge_last_date.strftime('%Y-%m-%d'), 'sleep_last_date': sleep_last_date.strftime('%Y-%m-%d')}))

    def create_transaction(self, user_id, transaction_type, access_token):
        """Create Polar transaction to get new activity, exercise & physical-information data."""
        # transaction_type = activity, exercise or physical-information
        url = f'https://www.polaraccesslink.com/v3/users/{user_id}/{transaction_type}-transactions'
        transaction_uri = None
        response = self.call_api("POST", url, access_token)
        if response:
            transaction_uri = response['resource-uri']
            response = self.call_api("GET", transaction_uri, access_token)
        return response, transaction_uri

    @staticmethod
    def call_api(method, url, access_token):
        """Generic function to call Polar API and return JSON response."""
        headers = {'Accept': 'application/json', 'Authorization': 'Bearer {}'.format(access_token)}
        if method == "GET":
            response = requests.get(url, headers=headers)
        elif method == "POST":
            response = requests.post(url, headers=headers)
        elif method == "PUT":
            response = requests.put(url, headers=headers)
        try:
            response = response.json()
        except ValueError:
            response = False
        return response

    @staticmethod
    def get_tcx_file(url, exercise_id, access_token):
        """Gets TCX file for exercise_id, returns it as plaintext."""
        url = f'{url}/exercises/{exercise_id}/tcx'
        headers = {'Accept': 'application/vnd.garmin.tcx+xml', 'Authorization': 'Bearer {}'.format(access_token)}
        response = requests.get(url, headers=headers).text
        return response

    def get_nightly_data(self, access_token, data, last_date):
        """Gets sleep & nightly recharge data, returns data that's newer than last_date."""
        url = f'https://www.polaraccesslink.com/v3/users/{data}'
        response = self.call_api("GET", url, access_token)
        details = {}
        if data == 'nightly-recharge':
            data = 'recharges'
        else:
            data = 'nights'
        for night in response[data]:
            night_date = datetime.strptime(night['date'], "%Y-%m-%d").date()

            # If there's no nightly_recharge_last_date, get all available days. Otherwise only get days newer than sleep_last_date.
            if last_date is None or night_date > last_date:
                details[night_date] = night
        return details

    def stream_events(self, inputs, ew):
        """Main function to get data into Splunk."""
        # Get inputs
        for self.input_name, self.input_item in inputs.inputs.items():
            user_id = self.input_item["user_id"]
            access_token = self.input_item["access_token"]

        session_key = self._input_definition.metadata["session_key"]

        try:
            # If the access token is not masked, mask it.
            if access_token != self.MASK:
                self.encrypt_access_token(user_id, access_token, session_key)
                self.mask_access_token(session_key, user_id)
        except Exception as ex:
            self.logger.error(f'Error: {ex}')

        # Use clear_password for API authentication
        access_token = self.get_clear_token(session_key, user_id)

        # Get last stored dates for sleep & nightly recharge
        nightly_recharge_last_date, sleep_last_date = self.get_kvstore_data(session_key)

        try:
            # Get sleep & nightly recharge data
            nightly_dict = {'sleep': sleep_last_date, 'nightly-recharge': nightly_recharge_last_date}

            for key, value in nightly_dict.items():
                self.logger.info(f'Getting Polar {key} data...')
                response = self.get_nightly_data(access_token, key, value)
                if response:
                    # For sleep, most recent date is first key. For nightly-recharge, it's the last key.
                    last_date = list(response.keys())[0] if key == 'sleep' else list(response.keys())[-1]

                    # Send data to Splunk
                    for item in response.values():
                        sourcetype = 'polar:sleep' if key == 'sleep' else 'polar:recharge'
                        event = Event(stanza=self.input_name, sourcetype=sourcetype, data=json.dumps(item))
                        ew.write_event(event)
                    # Store new last date for key in the KV Store
                    self.set_kvstore_data(session_key, key, last_date)

            # Get physical information, activity & exercise data
            transaction_types = ['physical-information', 'activity', 'exercise']

            for transaction_type in transaction_types:
                self.logger.info(f'Getting Polar {transaction_type} data...')
                response, transaction_uri = self.create_transaction(user_id, transaction_type, access_token)
                if response:
                    counter = 0
                    for item in response[next(iter(response))]:
                        counter += 1
                        data = self.call_api("GET", item, access_token)
                        if data:
                            # Set sourcetype to physical, activity or exercise
                            sourcetype = f'polar:{transaction_type.split("-")[0]}'
                            event = Event(stanza=self.input_name, sourcetype=sourcetype, data=json.dumps(data))
                            ew.write_event(event)

                            # Get TCX and FIT files if transaction type is exercise
                            if transaction_type == 'exercise':
                                exercise_id = data['id']
                                data_tcx = self.get_tcx_file(transaction_uri, exercise_id, access_token)
                                source = f'{exercise_id}.tcx'
                                event = Event(stanza=self.input_name, source=source, sourcetype='polar:exercise:tcx', data=json.dumps(data_tcx))
                                ew.write_event(event)

                    self.logger.info(f'Retrieved {counter} {transaction_type} item(s).')

                    # Commit transaction so the data doesn't get retrieved again.
                    self.call_api("PUT", transaction_uri, access_token)
                    self.logger.debug(f'Committed {transaction_uri}')

            self.logger.info("Looks like we have all Polar data.")
        except Exception as ex:
            self.logger.error(ex)


if __name__ == "__main__":
    sys.exit(SplunkPolar().run(sys.argv))
