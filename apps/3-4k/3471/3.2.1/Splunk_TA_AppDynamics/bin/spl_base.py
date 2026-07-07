import sys
import os
import time

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(APP_DIR, "lib")
sys.path.insert(0, LIB_DIR)

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from solnlib import splunkenv, log


class BaseGeneratingCommand(GeneratingCommand):
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
