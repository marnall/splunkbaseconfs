import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import datetime
import json
import logging
import logging.handlers
import splunklib.client as client
from splunklib.modularinput import Script, Scheme, Argument, Event
from fitparse import FitFile
from garminexport import garminclient
from pathlib import Path


class GarminActivities(Script):

    MASK = "********"
    APP = __file__.split(os.sep)[-3]

    # Setup a custom logger, logs to $SPLUNK_HOME/var/log/splunk/ta_garmin_activities.log.
    def setup_logger(self, level):
        app = self.APP.lower()
        logger = logging.getLogger(app)
        logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
        logger.setLevel(level)

        file_handler = logging.handlers.RotatingFileHandler("{}/var/log/splunk/{}_activities.log".format(os.environ['SPLUNK_HOME'], app), maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def get_scheme(self):
        # Setup the data inputs
        scheme = Scheme("Garmin - Activities")
        scheme.description = "Imports FIT files and activity details from Garmin Connect."
        username_arg = Argument("username")
        username_arg.title = "Username"
        username_arg.description = "Your Garmin Connect username."
        username_arg.data_type = Argument.data_type_string
        username_arg.required_on_create = True
        scheme.add_argument(username_arg)

        password_arg = Argument("password")
        password_arg.title = "Password"
        password_arg.description = "Your Garmin Connect password."
        password_arg.data_type = Argument.data_type_string
        password_arg.required_on_create = True
        scheme.add_argument(password_arg)

        folder_arg = Argument("folder")
        folder_arg.data_type = Argument.data_type_string
        folder_arg.title = "Folder"
        folder_arg.description = "Folder to store the activity files. Folder will be created if it doesn't exist."
        folder_arg.required_on_create = True
        scheme.add_argument(folder_arg)
        return scheme

    def validate_input(self, validation_definition):
        # Check if folder exists, if not try to create it and catch Permission Denied error.
        folder = validation_definition.parameters["folder"]
        try:
            Path(folder).mkdir(parents=True, exist_ok=True)
        except PermissionError:
            raise PermissionError("No write permissions for folder {}".format(folder))
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
                "folder": item['folder']
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
        input_name = "{}-{}".format(kind, input_name)
        kvcollection = "TA_garmin"

        last_activity_fit = 1
        last_activity_json = 1

        collection = service.kvstore[kvcollection]
        # Get last activities, cast to int in case they are strings which can happen if you modify using Lookup Editor
        try:
            get_item = collection.data.query_by_id(input_name)
            last_activity_json = int(get_item['last_activity_json'])
            last_activity_fit = int(get_item['last_activity_fit'])
        except Exception:
            pass
        return last_activity_fit, last_activity_json

    def set_last_activity(self, session_key, last_activity_fit, last_activity_json):
        args = {'token': session_key, 'owner': 'nobody', 'app': self.APP}
        service = client.connect(**args)

        kind, input_name = self.input_name.split("://")
        input_name = "{}-{}".format(kind, input_name)
        kvcollection = "TA_garmin"

        collection = service.kvstore[kvcollection]
        # Update record, if it fails it doesn't exist so create it.
        try:
            collection.data.update(input_name, json.dumps({'last_activity_fit': last_activity_fit, 'last_activity_json': last_activity_json}))
        except Exception:
            collection.data.insert(json.dumps({"_key": input_name, "last_activity_fit": last_activity_fit, "last_activity_json": last_activity_json}))
        return True

    def parse_fitfile(self, filename):
        ''' Parses FIT file and returns two JSON objects, one with records (second-by-second data) and one with the device data'''
        fitfile = FitFile(filename)
        skip_this = False
        device_data, records_data = {}, []

        for item in fitfile.get_messages():
            # Ignore the record type, which contains the second-by-second data.
            data_type_detail = item.get_values()
            data_type, sep, tail = str(item).partition(' ')

            for key, value in data_type_detail.items():
                # Convert datetime objects to string
                if isinstance(value, datetime.date):
                    value = value.strftime('%Y-%m-%d %H:%M:%S')
                if isinstance(value, datetime.time):
                    value = value.strftime('%H:%M:%S')
                # Convert GPS coordinates from semicircles to degrees
                if '_lat' in key or '_long' in key:
                    if value is not None:
                        value = value * 180 / pow(2, 31)
                # Some events have no timestamps, happens with pool swims for example. Skip record parsing for those.
                if key == 'timestamp' and value is None:
                    skip_this = True
                data_type_detail.update({key: value})

            if str(item) == "record (#20)" and not skip_this:
                records_data.append(data_type_detail)
            else:
                # Add category as dict with lists, as some categories (e.g. device_info) can appear multiple times.
                device_data.setdefault(data_type, []).append(data_type_detail)

        return device_data, records_data

    def stream_events(self, inputs, ew):

        # Setup the logging handler
        logger = self.setup_logger(logging.INFO)

        # Get inputs
        for self.input_name, self.input_item in inputs.inputs.items():
            username = self.input_item["username"]
            password = self.input_item["password"]
            folder = self.input_item["folder"]

        session_key = self._input_definition.metadata["session_key"]

        try:
            # If the password is not masked, mask it.
            if password != self.MASK:
                self.encrypt_password(username, password, session_key)
                self.mask_password(session_key, username)

        except Exception as e:
            logger.error("Error: {}".format(e))

        # Use clear_password for Garmin authentication
        clear_password = self.get_password(session_key, username)

        try:
            logger.info("Authenticating to Garmin Connect...")
            with garminclient.GarminClient(username, clear_password) as garmin_client:
                # list activities and sort id in ascending order to get oldest activities first
                activities = garmin_client.list_activities()
                activities.sort(key=lambda tup: tup[0])
                logger.info("{} activities found".format(len(activities)))

                for activity in activities:
                    activity_id = activity[0]

                    # Get last downloaded activities for both FIT & JSON files
                    last_activity_fit, last_activity_json = self.get_last_activity(session_key)

                    # if activity is newer than last retrieved activity, proceed with downloading
                    if activity_id > last_activity_json:
                        logger.debug("Last FIT activity: {}, last JSON activity: {}".format(last_activity_fit, last_activity_json))
                        logger.info("Getting summary JSON for activity {}".format(activity_id))
                        activity_summary = garmin_client.get_activity_summary(activity_id)
                        filename_summary = "{}/{}.json".format(folder, activity_id)

                        with open(filename_summary, mode="w") as f:
                            f.write(str(activity_summary))

                        # Write to Splunk index
                        event = Event(stanza=self.input_name, sourcetype="garmin:activities:summary", source=filename_summary, data=json.dumps(activity_summary))
                        ew.write_event(event)

                        last_activity_json = activity_id
                        self.set_last_activity(session_key, last_activity_fit, last_activity_json)

                    if activity_id > last_activity_fit:
                        logger.info("Getting FIT file for activity {}".format(activity_id))
                        # Get activity file in FIT format, None if it's not available
                        activity_fit = garmin_client.get_activity_fit(activity_id)

                        if activity_fit is not None:
                            filename_fit = "{}/{}.fit".format(folder, activity_id)

                            with open(filename_fit, mode="wb") as f:
                                f.write(activity_fit)

                            # device_data has all device settings, however is verbose and unclear. Most details covered in garmin:activities:summary already so only sending records_data to Splunk.
                            device_data, records_data = self.parse_fitfile(filename_fit)

                            if records_data:
                                event = Event(stanza=self.input_name, sourcetype="garmin:activities:fit", source=filename_fit, data=json.dumps(records_data))
                                ew.write_event(event)

                            last_activity_fit = activity_id
                            self.set_last_activity(session_key, last_activity_fit, last_activity_json)
                        else:
                            logger.warning("Could not export activity {} as FIT file.".format(activity_id))
                            last_activity_fit = activity_id
                            self.set_last_activity(session_key, last_activity_fit, last_activity_json)
        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    sys.exit(GarminActivities().run(sys.argv))
