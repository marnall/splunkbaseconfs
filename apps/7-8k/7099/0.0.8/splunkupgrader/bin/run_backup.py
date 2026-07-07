from splunk.persistconn.application import PersistentServerConnectionApplication
import sys, os, glob
import re
import json
import logging
import logging.handlers
import subprocess
import shlex
import requests
from time import sleep

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from dep_client import depClient
from server_connection import get_session
import backup
import upgrader
import restore
from version import version
from splunk_commands import reload
from urllib.parse import quote


# sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
# import splunk_debug as dbg
# dbg.enable_debugging(timeout=25)

def setup_logger():
    logger = logging.getLogger('splunkupgrader')

    # Clear log handlers since it was discovered that there was duplicate logs.
    if logger.hasHandlers():
        logger.handlers.clear()
    
    log_path = os.path.join(os.getenv('SPLUNK_HOME'), 'var', 'log', 'splunk', 'splunkupgrader.log')
    component = "SplunkUpgrader"
    event = "%(asctime)s.%(msecs)03d %(levelname)s {} %(message)s".format(component)
    # logging.basicConfig(filename =log_file, level=logging.INFO, format=event)
    formatter = logging.Formatter(event, "%m-%d-%Y %H:%M:%S")
    file_handler = logging.handlers.RotatingFileHandler(log_path, mode='a', maxBytes=25000000, backupCount=2)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.setLevel("INFO")
    return logger

class RunBackup(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """
        
        args = self.parse_in_string(in_string)

        form_values = {}
        form_values = self.convert_to_dict(args.get('form', []))
        
        logger = setup_logger()
        

        payload = {}     
        # if form_values['message'] == "installVersion":
        #     inst_version = version()
        #     if inst_version == 'nofile':
        #         payload.update({'text': 'There isn\'t a Splunk install file present.'})
        #     else:
        #         payload.update({'text': 'Retreiving the install version.'})
        #         payload.update({'splunk_version': '{}'.format(inst_version)})
        if form_values['message'] == "install":
            username = form_values['username']
            password = form_values['password']
            isLocal = form_values['isLocal']
            remote_port = form_values['mgmtPort']
            remote_server = form_values['curServer']
            if isLocal == 'False':
                token = get_session(username, password, remote_server, remote_port)
                url = "https://{}:{}/servicesNS/-/splunkupgrader/run-backup?output_mode=json".format(remote_server, remote_port)
                data = 'message=install&isLocal=True&username={}&password={}&mgmtPort={}&curServer={}'.format(username, quote(password), remote_port, remote_server)
                headers = {'Content-Type': 'application/x-www-form-urlencoded','Authorization': 'Bearer {}'.format(token)}
                response = requests.request('POST', url, headers=headers, data=data, verify=False)
                resp_txt = json.loads(response.text)
                payload.update(resp_txt)    
            else:
                logger.info('Starting the upgrade process.')
                upgrader.splunk_upgrade(logger)
                # reload(logger)
                payload.update({'text': 'The upgrade process has completed. Please restart Splunk.'})
                logger.info('The upgrade process has completed. Please restart Splunk.')
        
        elif form_values['message'] == "restore":
            username = form_values['username']
            password = form_values['password']
            isLocal = form_values['isLocal']
            remote_port = form_values['mgmtPort']
            remote_server = form_values['curServer']
            if isLocal == 'False':
                token = get_session(username, password, remote_server, remote_port)
                url = "https://{}:{}/servicesNS/-/splunkupgrader/run-backup?output_mode=json".format(remote_server, remote_port)
                data = 'message=restore&isLocal=True&username={}&password={}&mgmtPort={}&curServer={}'.format(username, quote(password), remote_port, remote_server)
                headers = {'Content-Type': 'application/x-www-form-urlencoded','Authorization': 'Bearer {}'.format(token)}
                # dbg.set_breakpoint()
                response = requests.request('POST', url, headers=headers, data=data, verify=False)
                resp_txt = json.loads(response.text)
                payload.update(resp_txt)    
            else:
                logger.info('Starting the restore process.')
                restore_output = restore.run_restore(logger)
                payload.update({'text': restore_output})
        
        elif form_values['message'] == 'backup':
            username = form_values['username']
            password = form_values['password']
            isLocal = form_values['isLocal']
            remote_port = form_values['mgmtPort']
            remote_server = form_values['curServer']
            if password == 'undefined':
                payload.update({'text': 'The credentials have not been added. Please add the credentials in the setup page.'})
            else:
                if isLocal == 'False':
                    token = get_session(username, password, remote_server, remote_port)
                    url = "https://{}:{}/servicesNS/-/splunkupgrader/run-backup?output_mode=json".format(remote_server, remote_port)
                    data = 'message=backup&isLocal=True&username={}&password={}&mgmtPort={}&curServer={}'.format(username, quote(password), remote_port, remote_server)
                    headers = {'Content-Type': 'application/x-www-form-urlencoded','Authorization': 'Bearer {}'.format(token)}
                    response = requests.request('POST', url, headers=headers, data=data, verify=False)
                    text = json.loads(response.text)
                    payload.update(text)
                else:
                    tar_text = backup.tar_file_cmd(logger, username, password)
                    text = {'text': tar_text}
                    payload.update(text)
        
        elif form_values['message'] == 'deploy':
            username = form_values['username']
            password = form_values['password']
            isLocal = form_values['isLocal']
            remote_port = form_values['mgmtPort']
            remote_server = form_values['curServer']
            dep_server = os.uname()[1]
            dep_port = form_values['mgmtPort']
            if (isLocal == 'True'):
                payload.update({'text': 'The deployment client can\'t be installed on the deployment server'})
                logger.warning('The deployment client can\'t be installed on the deployment server')
            else:
                logger.info('Starting the deployment server setup process.')
                deploy = depClient(username, password, remote_server, remote_port, dep_server, dep_port, logger)
                payload.update(deploy)

        elif form_values['message'] == "restart":
            username = form_values['username']
            password = form_values['password']
            isLocal = form_values['isLocal']
            remote_port = form_values['mgmtPort']
            remote_server = form_values['curServer']
            token = get_session(username, password, remote_server, remote_port)
            url = "https://{}:{}/services/server/control/restart?output_mode=json".format(remote_server, remote_port)
            # data = 'username={}&password={}'.format(username, password, remote_port, remote_server)
            data = {}
            headers = {'Content-Type': 'application/x-www-form-urlencoded','Authorization': 'Bearer {}'.format(token)}
            logger.info('Restarting {}'.format(remote_server))
            response = requests.request('POST', url, headers=headers, data=data, verify=False)
            resp_txt = json.loads(response.text)
            logger.info('Restart Status: {}'.format(resp_txt))
            payload.update(resp_txt)   
        
        # elif form_values['message'] == "restart":
        #     splunk_home = os.getenv('SPLUNK_HOME')
        #     username = form_values['username']
        #     password = form_values['password']
        #     isLocal = form_values['isLocal']
        #     remote_port = form_values['mgmtPort']
        #     remote_server = form_values['curServer']
        #     if (isLocal == 'False'):
        #         token = get_session(username, password, remote_server, remote_port)
        #         url = "https://{}:{}/servicesNS/-/splunkupgrader/run-backup?output_mode=json".format(remote_server, remote_port)
        #         data = 'message=restart&isLocal=True&username={}&password={}&mgmtPort={}&curServer={}'.format(username, password, remote_port, remote_server)
        #         headers = {'Content-Type': 'application/x-www-form-urlencoded','Authorization': 'Bearer {}'.format(token)}
        #         response = requests.request('POST', url, headers=headers, data=data, verify=False)
        #         text = json.loads(response.text)
        #         payload.update(text)
        #     else:
        #         text = restart(splunk_home, logger)
        #         payload.update(text)

        else:
            payload.update({'text': 'No values received. Please contact support.'})
            payload.update({'splunk_version': version()})
        
        return {'payload': payload, 'status': 200}
        

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError("PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass
    
    def convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}

        for key, val in query:

            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]

            # If the entry is already included as a list, then just add the entry
            elif key in parameters:
                parameters[key].append(val)

            # Otherwise, just add the entry
            else:
                parameters[key] = val

        return parameters

    def parse_in_string(self, in_string):
        """
        Parse the in_string
        """
        
        params = json.loads(in_string)
        

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))

        return params

