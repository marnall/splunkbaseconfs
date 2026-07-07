from splunk.persistconn.application import PersistentServerConnectionApplication
import json
import os
import requests
import sys
import splunk.rest as rest
import splunk.appserver.mrsparkle.lib.util as util
dir = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','ta_skylight_for_splunk','aob_py' + str(sys.version_info.major))
if not dir in sys.path:
    sys.path.append(dir)

from splunk_aoblib.setup_util import Setup_Util

class AlertHandler(PersistentServerConnectionApplication):
    def __init__(self, command_line, command_arg):
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, args):
        args_dict = json.loads(args)['query']
        query = args_dict[0]
        query.remove('action')
        query = str(query[0])

        inputs = args_dict[1]
        inputs.remove('inputs')
        inputs = str(inputs[0])

        capture_host = args_dict[2]
        capture_host.remove('hostname')
        capture_host = str(capture_host[0])

        token = json.loads(args)["session"]["authtoken"]
        uri = 'https://127.0.0.1:8089'
        setup_util = Setup_Util(uri, token)

        if query == 'GetInfo':
            return  self.GetInfo(inputs, capture_host, setup_util)
        elif query == 'SaveExclude':
            return self.SaveExclude(inputs, capture_host, args_dict[3], setup_util)
        elif query == 'SensorsList':
            return self.SensorsList(setup_util)

    def GetInfo(self, inputs, capture_host, setup_util):
        def get_api_version(ip, api_key):
            headers = {'PVX-Authorization': api_key}
            response = requests.get('https://{}/api/get-api-version'.format(ip), headers=headers, verify=False, timeout=60)
            return float(response.json()["result"]["version"])

        try:
            pvx_address = setup_util.get_customized_setting("ip_address")
            pvx_api_key = ""
            pvx_data_port = []
            pvx_data_app = []

            from_pvx = []
            in_except = []
            json_path = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','exceptions.json')
            with open(json_path, "r") as f:
                json_data = json.loads(f.read())['filter']
                if len(json_data) > 0:
                    for i in json_data:
                        if i['capture'] == capture_host:
                            for y in i['inputs']:
                                if y['name'] == inputs:
                                    in_except = y['exceptions']

            try:
                cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
                with open(cwd, 'r') as file:
                    pvx_api_key = file.read().splitlines()[0]
            except:
                return None

            api_version = get_api_version(pvx_address, pvx_api_key)
            if api_version >= 0.5:
                url = 'https://{0}/api/query?expr=traffic FROM {1} BY application.name, server.port WHERE capture.hostname="{2}" SINCE @now-86400 TOP 50'.format(pvx_address, inputs, capture_host)
            else:
                url = 'https://{0}/api/query?expr=traffic FROM {1} BY application, server.port WHERE capture.hostname="{2}" SINCE @now-86400 TOP 50'.format(pvx_address, inputs, capture_host)

            headers = {'PVX-Authorization': pvx_api_key}
            response = requests.get(url, headers=headers, verify=False, timeout=60)
            r_json = response.json()

            if 'data' in r_json['result']:
                for res in r_json['result']['data']:
                    traffic = int(res['values'][0]['value'])
                    app = str(res['key'][0].get('value'))
                    port = int(res['key'][1].get('value'))

                    is_state_app = "0"
                    is_state_port = "0"

                    for n in in_except:
                        if n == app:
                            is_state_app = "1"

                        try:
                            n = int(n)
                            if n == port:
                                is_state_port = "1"
                        except:
                            pass

                    app_data = {'traffic': traffic, 'app': app, "is": is_state_app}
                    port_data = {'traffic': traffic, 'port': port, "is": is_state_port}
                    from_pvx.append(app)
                    from_pvx.append(port)

                    pvx_data_port.append(port_data)
                    pvx_data_app.append(app_data)
            
            not_in_pvx = list(set(from_pvx) ^ set(in_except))
            if len(not_in_pvx) > 0:
                for i in not_in_pvx:
                    try:
                        i = int(i)
                        pvx_data_port.append({'traffic': 0, 'port': i, "is": "1"})
                    except:
                        pvx_data_app.append({'traffic': 0, 'app': i, "is": "1"})

            x = UniqList(pvx_data_port, 'port')
            y = UniqList(pvx_data_app, 'app')
            pvx_data = {'port': x, 'app': y}

            return {"payload": "{}".format(json.dumps(pvx_data)), "status": 200}
        except Exception as e:
            return {"payload": "{}".format(e), "status": 401}


    def SaveExclude(self, inputs, capture_host, options, setup_util):
        def WriteToConfig(json_data):
            with open(json_path, "w") as f:
                f.write(json.dumps({"filter": json_data}))
        
        try:
            json_path = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','exceptions.json')

            options.remove('options')
            options = options[0]

            if not options:
                options = []
            else:
                options = options.split(',')

            with open(json_path, "r") as f:
                json_data = json.loads(f.read())['filter']

                if len(json_data) > 0:
                    for idx_i, i in enumerate(json_data):
                        if i['capture'] == capture_host:
                            for idx_e, e in enumerate(i['inputs']):
                                if e['name'] == inputs:
                                    json_data[idx_i]['inputs'][idx_e]['exceptions'] = options
                                    WriteToConfig(json_data)
                                    return {"payload": "Done", "status": 200}
                                if idx_e == len(i['inputs'])-1:
                                    new_data = {"name": inputs, 'exceptions': options}
                                    json_data[idx_i]['inputs'].append(new_data)
                                    WriteToConfig(json_data)
                                    return {"payload": "Done", "status": 200}
                        if idx_i == len(json_data)-1:
                            new_data = {'capture': capture_host, 'inputs': [{"name": inputs, 'exceptions': options}]}
                            json_data.append(new_data)
                            WriteToConfig(json_data)
                            return {"payload": "Done", "status": 200}
                else:
                    new_data = {'capture': capture_host, 'inputs': [{"name": inputs, 'exceptions': options}]}
                    json_data.append(new_data)
                    WriteToConfig(json_data)
                    return {"payload": "Done", "status": 200}
            return {"payload": "Error", "status": 401}
        except Exception as e:
            return {"payload": "{}".format(e), "status": 401}

    def SensorsList(self, setup_util):
        pvx_address = setup_util.get_customized_setting("ip_address")
        pvx_api_key = ""
        capture_stat = []

        try:
            cwd = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','bin','pvx_api_key.txt')
            with open(cwd, 'r') as file:
                pvx_api_key = file.read().splitlines()[0]
        except:
            return None

        url = 'https://{0}/api/query?expr=traffic FROM tcp, udp BY capture.hostname SINCE @now-86400'.format(pvx_address)
        headers = {'PVX-Authorization': pvx_api_key}
        response = requests.get(url, headers=headers, verify=False, timeout=60.0)
        r_json = response.json()

        if 'data' in r_json['result']:
            for res in r_json['result']['data']:
                traffic = int(res['values'][0]['value'])
                capture = str(res['key'][0].get('value'))
                capture_stat.append({"capture": capture, "traffic": traffic})

        data = {"capture_list": capture_stat}
        return {"payload": json.dumps(data), "status": 200}

def UniqList(lists, typeis):
    uniq = []

    for i in lists:
        t = i['traffic']
        a = i[typeis]

        if SearchInList(typeis, uniq, a):
            uniq.append(i)
        else:
            for e in uniq:
                if e[typeis] == a:
                    ct = e['traffic'] + t
                    e['traffic'] = ct
    return uniq

def SearchInList(typeis, uniq, a):
    for i in uniq:
        if i[typeis] == a:
            return False
    return True
