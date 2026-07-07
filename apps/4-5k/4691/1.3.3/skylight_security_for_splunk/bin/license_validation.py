import requests
import json
import uuid
import time
import sys
import os
import splunk.appserver.mrsparkle.lib.util as util

status_path = os.path.join(util.get_apps_dir(), 'skylight_security_for_splunk','bin', 'license_validation')
inputs_path = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk','local', 'inputs.conf')
inputs_name = ["skylight_dns", "skylight_alexa", "skylight_citrix", "skylight_dga_ml", "skylight_smb", "skylight_sql", "skylight_http", "skylight_tcp", "skylight_udp", "skylight_rf_ti", "skylight_tls", "skylight_voip", "skylight_ti_domain", "skylight_ti"]

def get_stanza(name):
    with open(inputs_path) as f:
        for i, line in enumerate(f.readlines()):
            if "[{0}]".format(name) in line or "{0}://".format(name) in line:
                return i

def status_input(line_num, command):
    check = lambda x : "disabled = 0" if x == "disabled = 1" else "disabled = 1"

    with open(inputs_path) as f:
        for i, line in enumerate(f.readlines()):
            if i > line_num:
                if command in line:
                    return False
                elif check(command) in line:
                    change_status(i, command)
                    return False
                elif "[" in line:
                    return True
        return True

def disable_input(name, command):
    out = []
    with open(inputs_path, "r") as f:
        for line in f.readlines():
            out.append(line)

            if "[{0}]".format(name) in line or "{0}://".format(name) in line:
                out.append("%s\n" % (command))

    with open(inputs_path, "w") as f:
        f.writelines(out)

def change_status(line, command):
    with open(inputs_path, "r") as f:
        lines = f.readlines()
        out = ''.join(lines[:line]) + command + '\n' + ''.join(lines[line + 1:])
        
        with open(inputs_path, "w") as a:
            a.writelines(out)

def validation_status(get=False, status=""):
    if get:
        with open(status_path, "r") as f:
            return f.readlines()
    else:
        with open(status_path, "w") as f:
            f.write(status)

def main(command):
    for name in inputs_name:
        include = get_stanza(name)
        if type(include) == int:
            if status_input(include, command):
                disable_input(name, command)
        else:
            stanza = "[{0}]\n{1}\n\n".format(name, command)
            with open(inputs_path, "a+") as f:
                f.write(stanza)

def create_alert(token):
    search_command = '''| makeresults
| eval _time = %s
| eval edit_time = _time
| eval id = "%s"
| eval Source = "splunk" 
| eval Destination = "splunk"  
| eval ruleName = "License validation (Inputs disabled)" 
| eval alert_type = "Network" 
| eval pvx_alert=1
| eval host = "local"
| eval status = "New"
| eval owner = "Unassigned"
| eval comment = "no comment"
| eval severity = "Critical" 
| eval ruleDescription = "If the data volume is more than the license allows, then all inputs in TA will be disabled." 
| eval killchain = "none" 
| eval user_name = "User unavailable"
| table _time, edit_time, id, Source, Destination, ruleName, ruleDescription, alert_type, pvx_alert, host, severity, owner, status, killchain, user_name
| collect index=pvx_alerts''' % (time.time(), str(uuid.uuid4()))


    url = "https://localhost:8089/servicesNS/nobody/search/search/jobs/export?output_mode=json"
    headers = {
        'Authorization': 'Splunk %s' % token,
        'Content-Type': 'application/json'
    }

    data = {
        "search": search_command
    }
    
    r = requests.post(url, data=data, headers=headers, verify=False)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())

        splunk_threshold = int(payload["result"]["threshold"])
        splunk_usage = float(payload["result"]["usage"])
        splunk_license = float(payload["result"]["poolsz"])
        splunk_percent = int((splunk_usage/splunk_license)*100)

        splunk_status = validation_status(get=True)
        if splunk_percent>splunk_threshold:
            create_alert(token=payload.get('session_key'))

            if "inputs_enabled" in splunk_status:
                main("disabled = 1")
                validation_status(status="inputs_disabled")
                util.restart_splunk()
        else:
            if "inputs_disabled" in splunk_status:
                main("disabled = 0")

                validation_status(status="inputs_enabled")
                util.restart_splunk()
