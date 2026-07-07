import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import datetime
import json
import logging
import logging.handlers
import splunklib.client as client
from splunklib.modularinput import Script, Scheme, Argument, Event
from garminexport import garminclient


class GarminDailySummary(Script):

    MASK = "********"
    APP = __file__.split(os.sep)[-3]

    # Setup a custom logger, logs to $SPLUNK_HOME/var/log/splunk/ta_garmin_dailysummary.log.
    def setup_logger(self, level):
        app = self.APP.lower()
        logger = logging.getLogger(app)
        logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
        logger.setLevel(level)

        file_handler = logging.handlers.RotatingFileHandler("{}/var/log/splunk/{}_dailysummary.log".format(os.environ['SPLUNK_HOME'], app), maxBytes=25000000, backupCount=5)
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    def get_scheme(self):
        # Setup the data inputs
        scheme = Scheme("Garmin - Daily Summary")
        scheme.description = "Imports daily user summaries from Garmin Connect."
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

    def get_last_dailysummary(self, session_key):
        args = {'token': session_key, 'owner': 'nobody', 'app': self.APP}
        service = client.connect(**args)

        kind, input_name = self.input_name.split("://")
        input_name = "{}-{}".format(kind, input_name)
        kvcollection = "TA_garmin"

        last_daily_summary = None
        collection = service.kvstore[kvcollection]
        try:
            get_item = collection.data.query_by_id(input_name)
            if get_item:
                last_daily_summary = get_item['last_daily_summary']
        except Exception:
            pass
        return last_daily_summary

    def set_last_dailysummary(self, session_key, last_daily_summary):
        args = {'token': session_key, 'owner': 'nobody', 'app': self.APP}
        service = client.connect(**args)

        kind, input_name = self.input_name.split("://")
        input_name = "{}-{}".format(kind, input_name)
        kvcollection = "TA_garmin"

        collection = service.kvstore[kvcollection]
        # Update record, if it fails it doesn't exist so create it.
        try:
            collection.data.update(input_name, json.dumps({'last_daily_summary': last_daily_summary}))
        except Exception:
            collection.data.insert(json.dumps({"_key": input_name, "last_daily_summary": last_daily_summary}))
        return True

    def stream_events(self, inputs, ew):

        # Setup the logging handler
        logger = self.setup_logger(logging.INFO)

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
            logger.error("Error: {}".format(e))

        # Use clear_password for Garmin authentication
        clear_password = self.get_password(session_key, username)

        try:
            logger.info("Authenticating to Garmin Connect...")
            with garminclient.GarminClient(username, clear_password) as garmin_client:

                displayname = garmin_client.get_displayname()
                today = datetime.date.today()
                start_date = self.get_last_dailysummary(session_key)
                if not start_date:
                    logger.info("Getting all daily summaries, this will take a few minutes.")
                    daily_summaries = garmin_client.get_daily_summaries(displayname)
                    dates = []
                    event = Event(stanza=self.input_name, sourcetype='garmin:daily', source='garmin_connect', data=json.dumps(daily_summaries))
                    ew.write_event(event)
                    for item in daily_summaries:
                        for daily_event in item:
                            day = datetime.datetime.strptime(daily_event['calendarDate'], '%Y-%m-%d')
                            dates.append(day)
                    last_day = max(dates).strftime("%Y-%m-%d")
                    self.set_last_dailysummary(session_key, last_day)
                    logger.info("Last day updated to {}".format(last_day))
                else:
                    # Start from one day after the last day we have, stop at yesterday as today is still in progress.
                    get_from_day = datetime.datetime.strptime(start_date, '%Y-%m-%d').date() + datetime.timedelta(days=1)
                    delta = today - get_from_day
                    if delta.days >= 1:
                        logger.info("Getting daily summaries from {}".format(start_date))
                        for i in range(delta.days):
                            date = get_from_day + datetime.timedelta(days=i)
                            logger.info("Found daily summary for {}".format(date))
                            daily_summary = garmin_client.get_daily_summary(displayname, date)
                            event = Event(stanza=self.input_name, sourcetype='garmin:daily', source='garmin_connect', data=daily_summary)
                            ew.write_event(event)
                            # Write last day to KV store
                            self.set_last_dailysummary(session_key, date.strftime("%Y-%m-%d"))
                    else:
                        logger.info("Looks like we've got all daily user summaries!")

        except Exception as e:
            logger.error(e)


if __name__ == "__main__":
    sys.exit(GarminDailySummary().run(sys.argv))
