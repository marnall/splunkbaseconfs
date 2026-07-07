import requests
import xmltodict
import json
import os
import http
import re
import splunklogger as SL

def get_instance(os_info, install_dir, client_name, client_id, commserve, auth_code):
    if 'windows' in os_info.lower():
        command = 'powershell.exe Get-Content "{0}"'.format(os.path.join(install_dir, 'Base', 'QinetixVM').replace(" ", "' '"))
        exit_code, output, __ = execute_script('PowerShell', command, client_name, client_id, commserve, auth_code)
        if exit_code == 0:
            return output.strip()
        else:
            SL.make_entry("log_dir_helper", "Failed to get instance number for client " + client_name)
            return ""
    else:
        command = 'cat {0}'.format(os.path.join(install_dir + '/', 'galaxy_vm'))
        exit_code, output, __ = execute_script('UnixShell', command, client_name, client_id, commserve, auth_code)
        if exit_code == 0:
            temp = re.findall('GALAXY_INST="(.+?)";', output)
            if temp:
                return temp[0]
            else:
                SL.make_entry("log_dir_helper", "Failed to get instance number for client " + client_name)
                return ""
        else:
            SL.make_entry("log_dir_helper", "Failed to get instance number for client " + client_name)
            return ""

def get_log_directory(os_info, client_name, client_id, commserve, auth_code, install_dir):
        instance = get_instance(os_info, install_dir, client_name, client_id, commserve, auth_code)
        if instance == "":
            raise Exception("Not able to find the instance for client " + client_name)
        if 'windows' in os_info.lower():
            key = r'HKLM:\SOFTWARE\CommVault Systems\Galaxy\{0}\EventManager'.format(instance)
            exit_code, output, __ = execute_script(
                'PowerShell',
                '(Get-ItemProperty -Path {0}).dEVLOGDIR'.format(key.replace(" ", "' '")), client_name, client_id, commserve, auth_code)

            if exit_code == 0:
                return output.strip()
            else:
                SL.make_entry("log_dir_helper", "Line 19: Failed to get log dir")
                raise Exception("Unable to get log directory")

        elif 'unix' in os_info.lower():
            script = r"""
            FILE=/etc/CommVaultRegistry/Galaxy/%s/EventManager/.properties
            KEY=dEVLOGDIR

            get_registry_value()
            {
                cat $1 | while read line
                do
                    key=`echo $line | cut -d' ' -f1`
                    if [ "$key" = "$2" ]; then
                        echo $line | awk '{print $2}'
                        break
                    fi
                done
            }

            echo `get_registry_value $FILE $KEY`
            """ % instance

            __, output, error = execute_script('UnixShell', script, client_name, client_id, commserve, auth_code)

            if error:
                SL.make_entry("log_dir_helper", "Line 45: Failed to get log dir")
                raise Exception("Unable to get log directory")
            else:
                return output.strip()

        else:
            return "No Log File"

def execute_script(script_type, script, client_name, client_id, commserve, auth_code, script_arguments=None, wait_for_completion=True):

        script_types = {
            'java': 0,
            'python': 1,
            'powershell': 2,
            'windowsbatch': 3,
            'unixshell': 4
        }
        if script_type.lower() not in script_types:
            raise Exception("Unable to get log directory")

        import html

        if os.path.isfile(script):
            with open(script, 'r') as temp_file:
                script = html.escape(temp_file.read())
        else:
            script = html.escape(script)

        script_lines = ""
        script_lines_template = '<scriptLines val="{0}"/>'

        for line in script.split('\n'):
            script_lines += script_lines_template.format(line)

        script_arguments = '' if script_arguments is None else script_arguments
        script_arguments = html.escape(script_arguments)

        xml_execute_script = """
        <App_ExecuteCommandReq arguments="{0}" scriptType="{1}" waitForProcessCompletion="{5}">
            <client clientId="{2}" clientName="{3}"/>
            "{4}"
        </App_ExecuteCommandReq>
        """.format(
            script_arguments,
            script_types[script_type.lower()],
            client_id,
            client_name,
            script_lines,
            1 if wait_for_completion else 0
        )
        #Header to be added
        #this is always commserver
        flag, response = make_request(
            'POST',"http://" + commserve + "/webconsole/api/Qcommand/qoperation execute", xml_execute_script, commserve=commserve, auth_code=auth_code
        )
        if flag:
            if response.json():
                exit_code = -1
                output = ''
                error_message = ''

                if 'processExitCode' in response.json():
                    exit_code = response.json()['processExitCode']

                if 'commandLineOutput' in response.json():
                    output = response.json()['commandLineOutput']

                if 'errorMessage' in response.json():
                    error_message = response.json()['errorMessage']

                return exit_code, output, error_message
            else:
                SL.make_entry("log_dir_helper", "Line 119: Failed to get log dir")
                raise Exception("Unable to get log directory")
        else:
            raise Exception("Unable to get log directory")
            SL.make_entry("log_dir_helper", "Line 123: Failed to get log dir")

def make_request(
            method,
            url,
            payload=None,
            attempts=0,
            headers=None,
            stream=False,
            files=None,
            commserve=None,
            auth_code=None):
            #Header to be added
            headers = {'Host': commserve, 'Accept': 'application/json', 'Content-type': 'application/json', 'Authtoken': auth_code}

            if method == 'POST':
                if isinstance(payload, (dict, list)):
                    if files is not None:
                        response = _request(method=method, url=url, files=files, data=payload, verify=False)
                    else:
                        response = _request(
                            method=method, url=url, headers=headers, json=payload, stream=stream, verify=False
                        )
                else:
                    try:
                        # call encode on the payload in case the characters in the payload
                        # are not encoded, and to encode the string payload to bytes
                        payload = payload.encode()
                    except AttributeError:
                        # pass silently if payload is alredy encoded in bytes
                        pass

                    if 'Content-type' in headers:
                        try:
                            if payload is not None:
                                xmltodict.parse(payload)
                            headers['Content-type'] = 'application/xml'
                        except ExpatError:
                            headers['Content-type'] = 'text/plain'
                    response = _request(
                        method=method, url=url, headers=headers, data=payload, stream=stream, verify=False
                    )
            elif method == 'GET':
                response = _request(method=method, url=url, headers=headers, stream=stream, verify=False)
            elif method == 'PUT':
                response = _request(method=method, url=url, headers=headers, json=payload, verify=False)
            elif method == 'DELETE':
                response = _request(method=method, url=url, headers=headers, verify=False)
            else:
                SL.make_entry("log_dir_helper", "Line 173: Failed to get log dir")
                raise Exception("Unable to get log directory")

            if response.status_code == http.client.OK and response.ok:
                return (True, response)
            else:
                return (False, response)

def _request(**kwargs):
    return requests.request(**kwargs)
