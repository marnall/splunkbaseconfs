#!/usr/bin/env python
import csv
import datetime
import json
import os

from dateutil import parser
from onelogin.api.client import OneLoginClient

from onelogin_endpoint import api_server
from config import Config
from data_storage import DataStorage


class Api:

    def __init__(self, session_key, base_url=api_server()):
        data_storage = DataStorage(session_key)
        base_url = base_url
        client_id = Config('onelogin').get('onelogin_api', 'client_id')
        client_secret = data_storage.get_client_secret(client_id)
        region = "eu" if ".eu." in base_url else "us"
        self.client = OneLoginClient(client_id, client_secret, region, 1000)

# USERS ===================================================================

    def fetch_user_count(self):
        user_count = self.client.get_total_users() or 'NA'
        user = {'Total-Count': user_count}
        print(json.dumps(user))

# EVENTS ===================================================================

    def fetch_all_events(self, params=None):
        if params is None:
            params = {}
        config = Config('onelogin_events')
        current_time = datetime.datetime.utcnow()
        old_events_retrieved_time = current_time
        old_events_retrieved = config.get('events', 'retrieved_old')
        events = None
        parsed_event = {}
        while (not events) or (len(events) >= 1000):
            events = self.client.get_events(params)
            if events:
                for event in events:
                    parsed_event = self._get_all_params(vars(event))
                    print(json.dumps(parsed_event))

                ts = parsed_event["created_at"]
                if not old_events_retrieved:
                    old_events_retrieved_time = datetime.datetime.now()
                    time_stamp = str(parser.parse(str(current_time)))

                    config.set('events', 'retrieved_old', True)
                    config.set('events', 'last_event_timestamp', time_stamp)
            else:
                break
        if current_time == old_events_retrieved_time:
            config.set('events', 'last_event_timestamp', ts)

# LOOKUPS ============================================================
    def update_lookups(self):
        lookups_path = os.path.join(
            os.environ.get('SPLUNK_HOME'),
            'etc',
            'apps',
            'splunk_ta_onelogin',
            'lookups'
        )

        result = self.client.get_event_types()
        event_types = {
            str(one_event_type.id): str(one_event_type.name).lower()
            for one_event_type in result
        }

        with open(
                os.path.join(lookups_path, "onelogin_event_type_id.csv"),
                "w",
                newline=''
        ) as event_type_id:
            writer = csv.writer(event_type_id)
            writer.writerow(["id", "value"])
            for key, value in event_types.items():
                writer.writerow([key, "onelogin_event_" + value])

        with open(
                os.path.join(lookups_path, "onelogin_event_name_id.csv"),
                "w",
                newline=''
        ) as event_name_id:
            writer = csv.writer(event_name_id)
            writer.writerow(["id", "value"])
            for key, value in event_types.items():
                name = value.split('_')
                event = " ".join(name)
                event_name = event[0].upper() + event[1:]
                writer.writerow([key, event_name])

# Private Method============================================================

    @staticmethod
    def _get_all_params(user_data):
        for key in user_data.keys():
            if isinstance(user_data[key], datetime.datetime):
                user_data[key] = str(user_data[key])
        return user_data
