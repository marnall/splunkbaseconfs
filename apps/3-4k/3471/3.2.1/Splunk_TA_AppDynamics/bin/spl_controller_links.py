#!/usr/bin/env python
import datetime
import pickle
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from controller_service import ControllerService
from ucc_utils import Util
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators
from solnlib import splunkenv, log


class ControllerCache:
    def __init__(self, name, directory, session_key, logger, timeout_hours=24):
        self.name = name
        self.directory = directory
        self.session_key = session_key
        self.logger = logger
        self.timeout_hours = timeout_hours
        self.cache_file = os.path.join(self.directory, f"{name}.cache")
        self.cache = {}


        if os.path.exists(self.cache_file):
            with open(self.cache_file, "rb+") as f:
                try:
                    self.cache = pickle.load(f)
                    self.logger.info(f"Read cache for {self.name} from {self.cache_file}")
                except EOFError:
                    pass

        if self.expired():
            self.build_cache()
            with open(self.cache_file, "wb") as f:
                pickle.dump(self.cache, f)
                self.logger.info(f"Wrote cache for {self.name} to {self.cache_file}")

    def expired(self):
        return self.cache.get("timestamp", 0) < time.time() - self.timeout_hours*60*60

    def build_cache(self):
        start_time = time.time()
        self.logger.info("Building cache for %s from controller", self.name)
        controller = ControllerService(global_account_name=self.name, session_key=self.session_key, logger=self.logger)
        self.cache = {
            "timestamp": time.time(),
            "name": self.name,
            "controller_url": controller.get_controller_url(),
            "application_names": [],
            "node_tiers": {},
            "app_bts": {},
            "application_map": {}
        }

        applications = controller.get_apm_app_list()
        self.logger.info(f"applications = {applications}")
        for application in applications:
            app_bts = controller.get_application_business_transactions([application])
            #self.logger.info(f"app_bts = {app_bts}")
            app_name = controller.get_application(application)['name']
            self.cache["application_map"][app_name] = application
            self.cache["app_bts"][app_name] = app_bts
            self.cache["application_names"].append(app_name)
            self.cache["node_tiers"][app_name] = controller.get_nodes(application)
        end_time = time.time()
        self.logger.info(f"Cached {self.name} in {round(end_time - start_time, 2)} seconds")

    def match(self, event):
        if event.get("appd_app_name") not in self.cache["application_names"]:
            return None
        bt_id = event.get("appd_bt_id", None)
        if bt_id is not None and bt_id != "''":
            app_bts = self.cache["app_bts"].get(event.get("appd_app_name"), None)
            if app_bts is None:
                return None
            for bt in app_bts:
                try:
                    if int(bt.get("business_transaction_id", 0)) == int(bt_id):
                        return self.make_bt_deepLink(event)
                except ValueError as e:
                    self.logger.warning(f"Conversion failed: {e} for string: '{repr(bt_id)}'")
        node_id = event.get("appd_node_id")
        if node_id is not None and node_id != "''":
            for cached_node_id in self.cache["node_tiers"][event.get("appd_app_name")]:
                try:
                    if int(cached_node_id) == int(node_id):
                        return self.make_node_deepLink(event)
                except ValueError as e:
                    self.logger.warning(f"Conversion failed: {e} for string: '{repr(node_id)}'")
        return None

    def _get_app_id(self, app_name):
        return self.cache["application_map"][app_name]

    def make_bt_deepLink(self, event):
        duration = 15
        timestamp = int(event.get("_time")) * 1000
        timeRangeEnd = timestamp + (8*60000)
        timeRangeStart = timestamp - (7*60000)
        deepLink = f"{self.cache['controller_url']}/controller/#/location=APP_BT_DETAIL&timeRange=Custom_Time_Range.BETWEEN_TIMES.{timeRangeEnd}.{timeRangeStart}.{duration}&application={self._get_app_id(event['appd_app_name'])}&businessTransaction={event['appd_bt_id']}&dashboardMode=force"
        self.logger.info(f"bt deepLink: {deepLink}")
        return deepLink

    def make_node_deepLink(self, event):
        duration = 15
        timestamp = int(event.get("_time")) * 1000
        timeRangeEnd = timestamp + (8*60000)
        timeRangeStart = timestamp - (7*60000)
        deepLink = f"{self.cache['controller_url']}/controller/#/location=APP_NODE_MANAGER&timeRange=Custom_Time_Range.BETWEEN_TIMES.{timeRangeEnd}.{timeRangeStart}.{duration}&application={self._get_app_id(event['appd_app_name'])}&node={event['appd_node_id']}&dashboardMode=force"
        self.logger.info(f"node deepLink: {deepLink}")
        return deepLink



@Configuration()
class AddLinks(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    parsed_args = None
    logger = log.Logs().get_logger("appdynamics_spl_command")

    def get_arg(self, name, default=None):
        if not self.parsed_args:
            self.parsed_args = dict(
                part.split("=", 1)
                for part in self.metadata.searchinfo.args
                if "=" in part
            )
        return self.parsed_args.get(name, default)

    def get_session_key(self):
        session_key = self.metadata.searchinfo.session_key
        if not session_key:
            self.logger.error("Missing sessionKey: is passauth=true in commands.conf?")
            raise RuntimeError("No session key available. Make sure passauth=true is set in commands.conf.")
        return session_key

    def get_search_times(self):
        search_results = self.search_results_info
        self.logger.debug('search time: %s %s' % (str(search_results.search_et), str(search_results.search_lt)))
        if search_results.search_lt:
            search_latest_time = int(search_results.search_lt * 1000)
        else:
            search_latest_time = int(time.time() * 1000)
        if search_results.search_et:
            search_earliest_time = int(search_results.search_et * 1000)
        else:
            # set 10 min from search_latest_time as search_earliest_time
            search_earliest_time = search_latest_time - 600000
        return search_earliest_time, search_latest_time

    def expand_attribute(self, data, attribute_name, remove=True):
        for k, v in data.get(attribute_name, {}).items():
            data[k] = v
        if remove:
            del data[attribute_name]
        return data

    def __init__(self, **kwargs):
        super().__init__()

        # create a cache directory if it doesn't exist
        self.controllers = []
        self._initialized = False


    def stream(self, events):
        # To connect with Splunk, use the instantiated service object which is created using the server-uri and
        # other meta details and can be accessed as shown below
        # Example:-
        #    service = self.service

        if not self._initialized: # we have to wait until this is called to build the cache
            directory = os.path.join(os.path.dirname(__file__), "..", "controller-cache/")
            os.makedirs(directory, exist_ok=True)

            #get controller config stanzas
            config_names = splunkenv.get_conf_stanzas("splunk_ta_appdynamics_account", Util.get_app_name())
            for name in config_names:
                self.controllers.append(ControllerCache(name, directory, self.get_session_key(), self.logger, timeout_hours=24))
            self._initialized = True

        # Put your event transformation code here
        for event in events:
            #iterate controller caches until a match is found
            #once found add a deep link to the event before yeilding it
            for cache in self.controllers:
                deepLink = cache.match(event)
                if deepLink is not None:
                    event['appd_deepLink'] = deepLink
                    break                
            yield event


if __name__ == "__main__":
    dispatch(AddLinks, sys.argv, sys.stdin, sys.stdout, __name__)
