from __future__ import absolute_import
from __future__ import division
from future import standard_library
standard_library.install_aliases()  # noqa: E402
from builtins import str
import splunk
from . import helper
from .pbs_global_configs import PbsGlobalConfigs as pbsConf
from .instance_utils import InstanceUtils as instanceUtil
from .messaging import Messaging as msging


class Summary(splunk.rest.BaseRestHandler):
    def build_summary(self, spark_data, spark_master_ip, spark_master_ui, spark_master_port, spark_history_ui,
                      global_errors,):
        spark_conf_map = {}

        try:
            status = spark_data['status']
            pretty_status = 'running' if status == 'ALIVE' else 'down'

            spark_conf_map['spark_status'] = pretty_status
            spark_conf_map['spark_history_webui_port'] = str(spark_history_ui)
            spark_conf_map['spark_master_uri'] = spark_master_ip
            spark_conf_map['spark_master_webui_port'] = str(spark_master_ui)
            spark_conf_map['spark_master_port'] = spark_master_port

        except Exception as e:
            global_errors.append(msging.error_obj_map["general_error"].to_json(e.message))
            return None

        return spark_conf_map

    def handle_GET(self):
        header = {'Authorization': 'Splunk ' + self.sessionKey}

        global_errors = []
        global_warnings = []
        multisite_warnings = []

        res = {
            'summary': {},
            'user': '',
            'instance_type': '',
            'sh_captain': '',
            'errors': [],
            'warnings': [],
            'site_affinity_warnings': []
        }

        mgmt_port = helper.Helper.get_splunkd_mgmt_port()
        if mgmt_port is None:
            res['errors'].append(msging.error_obj_map["mgmt_port"].to_json())
            helper.Helper.write_json_response(self.response, res)
            return

        try:
            instanceUtil.get_instance_type(mgmt_port, header, res)
            instanceUtil.get_user(mgmt_port, header, res)
            instanceUtil.get_sh_captain(mgmt_port, header, res)

            app_config = helper.RestComm.get_app_config(mgmt_port, header)

            spark_master_ip = app_config.get(pbsConf.spark_master_host_key, None)
            spark_master_port = app_config.get(pbsConf.spark_master_port_key, None)
            spark_master_ui = app_config.get(pbsConf.spark_master_webui_port_key, None)
            spark_history_ui = app_config.get(pbsConf.spark_history_webui_port_key, None)
            history_server_enabled = app_config.get(pbsConf.history_server_enabled_key, None)
            res['summary']['history_server_enabled'] = history_server_enabled

            # get 1) spark ip/ports info and 2) Spark cluster info from splunkd and spark master
            spark_data = helper.RestComm.get_spark_info(spark_master_ip, spark_master_ui)

            res['summary']['security'] = app_config.get(pbsConf.security_status_key, "-")
            res['summary']['site_affinity'] = helper.RestComm.get_sh_site_info(mgmt_port, header, global_warnings,
                                                                               multisite_warnings)

            # check aliveness of history server
            if res['instance_type'] not in ("worker", "indexer") and history_server_enabled.lower() == "true":
                history_data = helper.RestComm.splunk_rest(
                    "api/v1/version", None, '127.0.0.1', str(spark_history_ui), True)
                if not helper.Helper.is_valid_history_resp(history_data):
                    global_warnings.append(msging.warn_obj_map["clstr_no_history_info"].to_json())

            if spark_data is None:
                global_errors.append(msging.error_obj_map["clstr_no_spark_info"].to_json())
                res['errors'] = global_errors
                res['warnings'] = global_warnings
                helper.Helper.write_json_response(self.response, res)
                return

            # TODO 1: refactor to get settings from single API
            # TODO 2: add `actionable_errors` field to response and check where to add actions
            # load basic spark info into spark_conf, as the first part of summary in response
            summary = self.build_summary(spark_data, spark_master_ip, spark_master_ui, spark_master_port,
                                         spark_history_ui, global_errors)
            res['summary'].update(summary)
            res['errors'] = global_errors
            res['warnings'] = global_warnings
            res['site_affinity_warnings'] = multisite_warnings
            helper.Helper.write_json_response(self.response, res)
        except Exception as e:
            self.response.write("Failed: " + e.message)

    handle_POST = handle_GET
