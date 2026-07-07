import concurrent
import sys
import os
import time
import traceback
from concurrent.futures import as_completed

APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LIB_DIR = os.path.join(APP_DIR, "lib")
sys.path.insert(0, LIB_DIR)

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators
from solnlib import splunkenv, log
from controller_service import ControllerService
from ucc_utils import Util
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
                     require=False)
    type = Option(doc='''
        **Syntax: type=<string>
        **Description:** the AppDynamics Status Types to return.''',
                   require=False)

    def generate(self):
        self.account = self.get_arg("account")
        self.application = self.get_arg("application")
        self.type = self.get_arg("type")
        if self.type is None:
            self.type = "application"
        if self.application is None:
            self.application = "*"
        search_earliest_time, search_latest_time = self.get_search_times()

        self.logger.info("Account '%s' type: '%s' application: '%s' start: '%d' end: '%d'", self.account, self.type, self.application, search_earliest_time, search_latest_time)
        self.logger.debug("Entered generate()\n")
        self.logger.debug(f"Available metadata keys: {dir(self.metadata)}\n")
        self.logger.debug(f"Available searchinfo keys: {dir(self.metadata.searchinfo)}\n")
        self.logger.debug(f"Available arg keys: {self.metadata.searchinfo.args}\n")
        try:
            session_key = self.get_session_key()

            max_workers = Util.get_max_workers(session_key)

            controller = ControllerService(global_account_name=self.account, session_key=session_key)
            if self.application == "*":
                # Use same app list source as appdynamics_status: APM applications only
                all_apps = controller.get_all_app_list() or {}
                apm_apps = all_apps.get("apmApplications") or []
                if not isinstance(apm_apps, list):
                    apm_apps = [apm_apps]
                application_ids = [app["id"] for app in apm_apps if isinstance(app, dict) and "id" in app]
            else:
                application_ids = [controller.get_application_id_by_name(self.application)]

            self.logger.info(f"Application List: {application_ids}")

            if self.type.lower().startswith("application") :
                self.logger.info("Collecting Application Status Metrics")
                app_metrics_data = controller.get_application_summary(application_ids)
                for metric in app_metrics_data:
                    metric['performanceState'] = metric['severitySummary']['performanceState']
                    yield metric
                return

            if self.type.lower() == "tiers":
                def process_tiernode_query(app):
                    try:
                        processed_data = []
                        tier_data, node_data = controller.get_tier_node_status(app)
                        if tier_data:
                            for tier in tier_data:
                                processed_data.append(tier_data[tier])
                        if node_data:
                            for node in node_data:
                                processed_data.append(node)
                        return processed_data
                    except Exception as e:
                        self.logger.error("Error fetching Tier Node status for app %s: %s", app, e)
                        return []

                try:
                    self.logger.info("Collecting Tier and Node Status Metrics")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        results = [executor.submit(process_tiernode_query, app_id) for app_id in application_ids]
                    for future in as_completed(results):
                        for data in future.result():
                            self.logger.info(f"data: {data}")
                            yield data
                    return
                except Exception as e:
                    self.logger.error(e)

            if self.type.lower() == "bts":
                def process_bt_query(app):
                    try:
                        bt_data = controller.get_application_business_transactions([app])
                        if bt_data is not None:
                            return bt_data
                        return []
                    except Exception as e:
                        self.logger.error("Error fetching BT status for app %s: %s", app, e)
                        return []

                try:
                    self.logger.info("Collecting Business Transaction Status Metrics")
                    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                        results = [executor.submit(process_bt_query, app_id) for app_id in application_ids]
                    for future in as_completed(results):
                        for data in future.result():
                            self.logger.info(f"data: {data}")
                            yield data
                    return
                except Exception as e:
                    self.logger.error(e)

            if self.type.lower() == "databases":
                try:
                    self.logger.info("Collecting Database Status Metrics")
                    db_data = controller.get_database_summary()
                    if db_data:
                        for data in db_data:
                            data = self.expand_attribute(data, "rolledUpMetricDatas")
                            self.logger.info(f"data: {data}")
                            yield data
                    return
                except Exception as e:
                    self.logger.error(e)

            if self.type.lower() == "servers":
                try:
                    self.logger.info("Collecting Server Status Metrics")
                    server_summary = controller.get_server_summary()
                    for attribute, value in server_summary.items():
                        value = self.expand_attribute(value, "health")
                        value = self.expand_attribute(value, "metrics")
                        self.logger.info(f"data: {value}")
                        yield value
                    return
                except Exception as e:
                    self.logger.error(e)

            if self.type.lower() == "web_dem":
                try:
                    self.logger.info("Collecting DEM Web Status Metrics")
                    web_summaries = controller.get_dem_web_summary()
                    for data in web_summaries:
                        data = self.expand_attribute(data, "metrics")
                        self.logger.info(f"data: {data}")
                        yield data
                    return
                except Exception as e:
                    self.logger.error(e)

            if self.type.lower() == "mobile_dem":
                try:
                    self.logger.info("Collecting DEM Mobile Status Metrics")
                    mobile_summaries = controller.get_dem_mobile_summary()
                    for data in mobile_summaries:
                        data = self.expand_attribute(data, "metrics")
                        data = self.expand_attribute(data, "healthRuleViolationStatus")
                        self.logger.info(f"data: {data}")
                        yield data
                    return
                except Exception as e:
                    self.logger.error(e)

            raise ValueError(f"Unknown type: {self.type}. Supported types are 'applications', 'tiers', 'bts', 'databases', 'servers', 'web_dem', 'mobile_dem'")
        except Exception:
            self.logger.error(traceback.format_exc())
            raise


# ─── DISPATCH ENTRYPOINT ────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        dispatch(MetricSearch, sys.argv, sys.stdin, sys.stdout, __name__)
    except Exception:
        raise
