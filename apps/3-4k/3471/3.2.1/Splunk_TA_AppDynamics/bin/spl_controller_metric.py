import concurrent
import sys
import os
import time
import traceback
from concurrent.futures import as_completed

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(APP_DIR, "lib")
sys.path.insert(0, LIB_DIR)

from ucc_utils import Util
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from solnlib import splunkenv, log
from controller_service import ControllerService
from spl_base import BaseGeneratingCommand
from appdynamics_utils import process_metric_entry


@Configuration()
class MetricSearch(BaseGeneratingCommand):
    account = Option(doc='''
        **Syntax: account=<string>
        **Description:** the AppDynamics Controller Account Name in the TA configuration.''',
                     require=True)
    application = Option(doc='''
        **Syntax: application=<string>
        **Description:** the AppDynamics Application Name these metrics are registered under.''',
                     require=False, default="*")
    metrics = Option(doc='''
        **Syntax: query=<string>
        **Description:** the AppDynamics Metric Paths to return.''',
                   require=True)
    rollup = Option(doc='''
        **Syntax: limit=<boolean>
        **Description:** the default is True which will provide only a single rolled up metric set for each metric, false will provide all the raw data for periods available''',
                   require=False, default=True)

    def _process_entry(self, entry):
        return process_metric_entry(entry)

    def generate(self):
        self.account = self.get_arg("account")
        self.application = self.get_arg("application")
        self.metrics = self.get_arg("metrics")
        self.rollup = self.get_arg("rollup")
        if self.rollup is None:
            self.rollup = True
        search_earliest_time, search_latest_time = self.get_search_times()

        self.logger.info("Account '%s' app: '%s' metrics: '%s' start: '%d' end: '%d' rollup: '%s'", self.account, self.application, self.metrics, search_earliest_time, search_latest_time, self.rollup)
        self.logger.debug("Entered generate()\n")
        self.logger.debug(f"Available metadata keys: {dir(self.metadata)}\n")
        self.logger.debug(f"Available searchinfo keys: {dir(self.metadata.searchinfo)}\n")
        self.logger.debug(f"Available arg keys: {self.metadata.searchinfo.args}\n")
        try:
            session_key = self.get_session_key()
            max_workers = Util.get_max_workers(session_key)
            controller = ControllerService(global_account_name=self.account, session_key=session_key)
            if self.application == "*":
                application_ids = []
                all_applications = controller.get_all_app_list()
                for section_key, section_value in all_applications.items():
                    if isinstance(section_value, list):
                        for app in section_value:
                            if 'id' in app and 'name' in app:
                                application_ids.append(app['id'])
                    elif isinstance(section_value, dict) and 'id' in section_value and 'name' in section_value:
                        application_ids.append(section_value['id'])

                def process_application(application_id):
                    data = controller.get_metric_data(application_id, self.metrics, start=search_earliest_time, end=search_latest_time, opt_compress_data_flag=self.rollup)
                    processed_data = []
                    for entry in data:
                        for each in self._process_entry(entry):
                            each['application_id'] = application_id
                            each['application_name'] = controller.get_application(application_id).get('name') #i did this twice but i don't care :P
                            processed_data.append(each)
                    return processed_data

                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    results = [executor.submit(process_application, app_id) for app_id in application_ids]
                    for future in as_completed(results):
                        for data in future.result():
                            self.logger.info(f"data: {data}")
                            yield data
            else:
                application_id = controller.get_application_id_by_name(self.application)
                if not application_id:
                    raise RuntimeError("No application found with name '%s'" % self.application)
                data = controller.get_metric_data(application_id, self.metrics, start=search_earliest_time, end=search_latest_time, opt_compress_data_flag=self.rollup)
                for entry in data:
                    for each in self._process_entry(entry):
                        each['application_id'] = application_id
                        each['application_name'] = self.application
                        yield each


        except Exception:
            self.logger.error(traceback.format_exc())
            raise


# ─── DISPATCH ENTRYPOINT ────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        dispatch(MetricSearch, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        raise
