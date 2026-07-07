from __future__ import absolute_import
import splunk
from . import helper
import json
from .pbs_global_configs import PbsGlobalConfigs as pbsConf
from .messaging import Messaging as msging


class DFSManage(splunk.rest.BaseRestHandler):

    def spark_manage(self, mgmt_port, header):
        res = {'restart_success': False}
        success = helper.RestComm.modify_config_using_rest(pbsConf.conf_name, pbsConf.conf_stanza,
                                                           "spark_instance_id", "", header, mgmt_port)
        if success:
            res['restart_success'] = True

        return res

    def handle_POST(self):
        header = {'Authorization': 'Splunk ' + self.sessionKey}
        res = {'result': {}, 'errors': []}
        accepted_commands = {'restart': 'restart'}
        mgmt_port = helper.Helper.get_splunkd_mgmt_port()

        if mgmt_port is None:
            res['errors'].append(msging.error_obj_map["mgmt_port"].to_json())
            helper.Helper.write_json_response(self.response, res)
            return

        try:
            payload = self.request['payload']
            req = json.loads(payload)
            cmd = req["command"].lower()

            if cmd not in accepted_commands:
                res['errors'].append(msging.error_obj_map["invalid_cmd"].to_json(suffix=cmd))
                helper.Helper.write_json_response(self.response, res)
                return

            res['result'] = self.spark_manage(mgmt_port, header)

            helper.Helper.write_json_response(self.response, res)

        except Exception as e:
            self.response.write("Failed: " + e.message)

    handle_GET = handle_POST
