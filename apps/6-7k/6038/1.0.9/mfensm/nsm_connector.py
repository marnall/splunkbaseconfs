import phantom.app as phantom
from phantom.base_connector import BaseConnector
from phantom.action_result import ActionResult

import requests
import json
import base64

from nsm_consts import *


class RetVal(tuple):
   def __new__(cls, val1, val2):
      return tuple.__new__(RetVal, (val1, val2))


def b64(user, password):
   creds = user + ':' + password
   return base64.b64encode(creds)


def session(creds, nsmurl, verify):
   authheader = { 'Accept': 'application/vnd.nsm.v1.0+json',
                  'Content-Type': 'application/json',
                  'NSM-SDK-API': creds }
   r = requests.get(nsmurl + 'session', headers=authheader, verify=verify)
   res = r.json()
   sessionheader = { 'Accept': 'application/vnd.nsm.v1.0+json',
                     'Content-Type': 'application/json',
                     'NSM-SDK-API': '%s'
                     % b64(res['session'], res['userId']) }
   return sessionheader


def get_sensors(nsmurl, headers, verify):
   r = requests.get(nsmurl + 'sensors', headers=headers, verify=verify)
   res = r.json()
   return res


def is_sensorup(nsmurl, nsm_sensor, headers, verify):
   r = requests.get(nsmurl + 'sensor/%s/status' % nsm_sensor, headers=headers, verify=verify)
   res = r.json()

   try:
      if res['status'] == 'ACTIVE':
         return True
      else:
         return False
   except:
      return False


def post_qhost(nsmurl, headers, nsm_sensor, block_ip, duration, verify):
   time = {15: 'FIFTEEN_MINUTES', 30: 'THIRTY_MINUTES', 45: 'FORTYFIVE_MINUTES', 60: 'SIXTY_MINUTES',
           240: 'FOUR_HOURS', 480: 'EIGHT_HOURS', 720: 'TWELVE_HOURS', 960: 'SIXTEEN_HOURS',
           999: 'UNTIL_EXPLICITLY_RELEASED'}

   if duration not in time:
      duration = 15

   payload = {'IPAddress': '%s' % block_ip,
              'Duration': '%s' % time[duration]}

   if nsm_sensor and is_sensorup(nsmurl, nsm_sensor, headers, verify):
      r = requests.post(nsmurl + 'sensor/%s/action/quarantinehost' % nsm_sensor, headers=headers, data=json.dumps(payload), verify=verify)
      res = r.json()
   elif is_sensorup(nsmurl, nsm_sensor, headers, verify) is False:
      res = (0, "Sensor %s down" % nsm_sensor)

   return res


def delete_qhost(nsmurl, headers, nsm_sensor, unblock_ip, verify):

   if nsm_sensor and is_sensorup(nsmurl, nsm_sensor, headers, verify):
      r = requests.delete(nsmurl + 'sensor/%s/action/quarantinehost/%s' % (nsm_sensor, unblock_ip), headers=headers, verify=verify)
      res = r.json()
   elif is_sensorup(nsmurl, nsm_sensor, headers, verify) is False:
      res = (0, "Sensor %s down" % nsm_sensor)

   return res


def logout(headers, nsmurl, verify):
   r = requests.delete(nsmurl + 'session', headers=headers, verify=verify)
   res = r.json()
   return res


class MfeNSMConnector(BaseConnector):

    def __init__(self):

        # Call the BaseConnectors init first
        super(MfeNSMConnector, self).__init__()

        self._state = None
        self._base_url = None

    def initialize(self):

        config = self.get_config()
        self._verify = config.get('verify_server_cert', False)
        return phantom.APP_SUCCESS

    def _handle_test_connectivity(self, param):

        config = self.get_config()

        nsm_ip = config.get(NSM_IP)
        nsm_user = config.get(NSM_USER)
        nsm_pw = config.get(NSM_PW)
        nsm_sensor = config.get(NSM_SENSOR)

        self.save_progress("Testing the NSM connectivity")
        self.save_progress(phantom.APP_PROG_CONNECTING_TO_ELLIPSES, nsm_ip)

        try:
           creds = b64(nsm_user, nsm_pw)
           nsmurl = "https://" + nsm_ip + "/sdkapi/"
           headers = session(creds, nsmurl, self._verify)
           sensors = get_sensors(nsmurl, headers, self._verify)
           sensor_list = []
           self.save_progress("Querying sensors")
           try:
             for i in sensors['SensorDescriptor']:
                model = i['model']
                ip = i['sensorIPAddress']
                sensorid = i['sensorId']
                sensor_list.append(str(sensorid))
                self.save_progress("Model: %s   |   Sensor IP Address: %s  |   SensorID: %s " % (model, ip, str(sensorid)))
           except:
             self.set_status(phantom.APP_ERROR, "No Sensor found. Please attach a Sensor to the McAfee ESM.")
             return self.get_status()

           if (not nsm_sensor):
              if (len(sensor_list) == 1):
                 self.save_progress("Sensor ID not defined in the asset config, please set it to {0}".format(sensor_list[0]))
              elif (len(sensor_list) > 1):
                 self.save_progress("Sensor ID not defined in the asset config, please set it to one of: {0}".format(', '.join(sensor_list)))
           else:
               if (nsm_sensor not in sensor_list):
                  if (len(sensor_list) == 1):
                     self.save_progress("Invalid Sensor ID defined in the asset config, please set it to {0}".format(sensor_list[0]))
                  elif (len(sensor_list) > 1):
                     self.save_progress("InvalidSensor ID defined in the asset config, please set it to one of: {0}".format(', '.join(sensor_list)))
                  self.save_progress("Test Connectivity Failed")
                  self.set_status(phantom.APP_ERROR, NSM_ERR_SERVER_CONNECTION)
                  return self.get_status()

           logout(headers, nsmurl, self._verify)

        except:
           self.save_progress("Test Connectivity Failed")
           self.set_status(phantom.APP_ERROR, NSM_ERR_SERVER_CONNECTION)
           return self.get_status()

        return self.set_status_save_progress(phantom.APP_SUCCESS, NSM_SUCC_CONNECTIVITY_TEST)

    def _handle_block_ip(self, param):

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        config = self.get_config()

        nsm_ip = config.get(NSM_IP)
        nsm_user = config.get(NSM_USER)
        nsm_pw = config.get(NSM_PW)
        nsm_sensor = config.get(NSM_SENSOR)
        block_ip = param[NSM_BLOCK_IP]
        duration = param[NSM_DURATION]

        try:
            creds = b64(nsm_user, nsm_pw)
            nsmurl = "https://" + nsm_ip + "/sdkapi/"
            headers = session(creds, nsmurl, self._verify)
            post_host = post_qhost(nsmurl, headers, nsm_sensor, block_ip, duration, self._verify)
            logout(headers, nsmurl, self._verify)

            if 'errorId' in post_host:
               errmsg = post_host['errorMessage']
               self.set_status(phantom.APP_ERROR, errmsg)
               action_result.set_status(phantom.APP_ERROR, errmsg)
               return self.get_status()

            action_result.add_data(post_host)
            action_result.set_status(phantom.APP_SUCCESS, NSM_SUCC_QUERY)
        except:
            self.set_status(phantom.APP_ERROR, NSM_ERR_SERVER_CONNECTION)
            return self.get_status()

        return action_result.get_status()

    def _handle_unblock_ip(self, param):

        self.save_progress("In action handler for: {0}".format(self.get_action_identifier()))
        action_result = self.add_action_result(ActionResult(dict(param)))

        config = self.get_config()

        nsm_ip = config.get(NSM_IP)
        nsm_user = config.get(NSM_USER)
        nsm_pw = config.get(NSM_PW)
        nsm_sensor = config.get(NSM_SENSOR)
        unblock_ip = param[NSM_BLOCK_IP]

        try:
            creds = b64(nsm_user, nsm_pw)
            nsmurl = "https://" + nsm_ip + "/sdkapi/"
            headers = session(creds, nsmurl, self._verify)
            delete_host = delete_qhost(nsmurl, headers, nsm_sensor, unblock_ip, self._verify)
            logout(headers, nsmurl, self._verify)

            if 'errorId' in delete_host:
               errmsg = delete_host['errorMessage']
               self.set_status(phantom.APP_ERROR, errmsg)
               action_result.set_status(phantom.APP_ERROR, errmsg)
               return self.get_status()

            action_result.add_data(delete_host)
            action_result.set_status(phantom.APP_SUCCESS, NSM_SUCC_QUERY)
        except:
            self.set_status(phantom.APP_ERROR, NSM_ERR_SERVER_CONNECTION)
            return self.get_status()

        return action_result.get_status()

    def handle_action(self, param):

        ret_val = phantom.APP_SUCCESS

        # Get the action that we are supposed to execute for this App Run
        action_id = self.get_action_identifier()

        self.debug_print("action_id", self.get_action_identifier())

        if action_id == 'test_connectivity':
            ret_val = self._handle_test_connectivity(param)

        elif action_id == 'block_ip':
            ret_val = self._handle_block_ip(param)

        elif action_id == 'unblock_ip':
            ret_val = self._handle_unblock_ip(param)

        return ret_val


if __name__ == '__main__':

    import sys
    import pudb
    pudb.set_trace()

    if (len(sys.argv) < 2):
        print "No test json specified as input"
        exit(0)

    with open(sys.argv[1]) as f:
        in_json = f.read()
        in_json = json.loads(in_json)
        print(json.dumps(in_json, indent=4))

        connector = MfeNSMConnector()
        connector.print_progress_message = True
        ret_val = connector._handle_action(json.dumps(in_json), None)
        print (json.dumps(json.loads(ret_val), indent=4))

    exit(0)
