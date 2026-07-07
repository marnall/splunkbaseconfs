
import os, sys
import subprocess
import shlex
from shutil import copytree, ignore_patterns
from server_connection import get_session
import requests

# sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
# from dep_client import logger

# username = 'admin'
# password = 'password'
# remote_server='localhost'
# remote_port = 51670
# dep_server = 'dmc'
# dep_server = os.uname()[1]
# dep_port = 8089
# token = get_session(username, password, remote_server, remote_port)
#Default setting for allow Remote Login is requireSetPassword.

# def set_remote_login(token, remote_server, remote_port):
#     # payload = 'allowRemoteLogin=always'
#     headers = {
#         'Content-Type': 'application/x-www-form-urlencoded',
#         'Authorization': 'Bearer {}'.format(token)
#     }
#     payload = 'allowRemoteLogin=always'
#     # headers = {
#     #     'Content-Type': 'application/x-www-form-urlencoded',
#     #     'Authorization': 'Basic YWRtaW46cGFzc3dvcmQ='
#     # }
#     url = "https://{}:{}/services/properties/server/general/?output_mode=json".format(remote_server, remote_port)
#     get_remote_login_url = "https://{}:{}/services/properties/server/general/allowRemoteLogin".format(remote_server, remote_port)
#     login_settings = requests.request("GET", get_remote_login_url, headers=headers, data={}, verify=False)
#     print(login_settings.text)
#     response = requests.request("POST", url, headers=headers, data=payload, verify=False)
#     print(response.text)
    
# def disable_remote_login(token, remote_server, remote_port):
#     # payload = 'allowRemoteLogin=always'
#     headers = {
#         'Content-Type': 'application/x-www-form-urlencoded',
#         'Authorization': 'Bearer {}'.format(token)
#     }
#     payload = 'allowRemoteLogin=requireSetPassword'
#     # headers = {
#     #     'Content-Type': 'application/x-www-form-urlencoded',
#     #     'Authorization': 'Basic YWRtaW46cGFzc3dvcmQ='
#     # }
#     url = "https://{}:{}/services/properties/server/general/?output_mode=json".format(remote_server, remote_port)
#     get_remote_login_url = "https://{}:{}/services/properties/server/general/allowRemoteLogin".format(remote_server, remote_port)
#     login_settings = requests.request("GET", get_remote_login_url, headers=headers, data={}, verify=False)
#     print(login_settings.text)
#     response = requests.request("POST", url, headers=headers, data=payload, verify=False)
#     print(response.text)

    

def depClient(username, password, remote_server, remote_port, dep_server, dep_port, logger):
    logger.info('Checking for app in deployment-apps.')
    addApp(logger)
    
    splunk = os.path.join(os.getenv('SPLUNK_HOME'), 'bin', 'splunk')
    command = "{} set deploy-poll {}:{} -uri https://{}:{} -auth {}:{}".format(splunk, dep_server, dep_port, remote_server, remote_port, username, password)
    command = shlex.split(command)
    run_cmd = subprocess.check_output(command)
    run_cmd = str(run_cmd)[1:]
    # run_resp = run_cmd.replace('b', '')
    run_cmd = run_cmd.replace('\\n', '')
    run_cmd = run_cmd.replace('\'', '')
    dep_payload = {} 
    if ("Configuration updated" in run_cmd):
    # payload.update({'text': run_cmd})
        
        logger.info('The deployment process completed successfully on {}. Splunk will restart.'.format(remote_server))
        dep_payload.update({'text': 'The deployment process completed successfully on {}. Splunk will restart.'.format(remote_server), 'deploy_response': '{}'.format(run_cmd)})
    else:
        logger.error("The deploy process was unsuccessful.")
        dep_payload.update({'text': 'The deploy process was unsuccessful.'})

    token = get_session(username, password, remote_server, remote_port)
    splunk_restart(token, remote_server, remote_port, logger)
    return dep_payload
    
def splunk_restart(token, remote_server, remote_port, logger):
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Authorization': 'Bearer {}'.format(token)
    }
    data={}
    url = "https://{}:{}/services/server/control/restart/?output_mode=json".format(remote_server, remote_port)
    logger.info('Restarting Splunk')
    response = requests.request("POST", url, headers=headers, data=data, verify=False)
    logger.info(response.text)
    
   
    
# Use the knowledge bundle
# /opt/splunk/var/run/searchpeers/dmc-1701354899/apps

def addApp(logger):
    src_dir = os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'apps', 'splunkupgrader')
    ignore_local = os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'apps', 'splunkupgrader', 'local')
    dest_dir = os.path.join(os.getenv('SPLUNK_HOME'), 'etc', 'deployment-apps', 'splunkupgrader')
    if os.path.exists(dest_dir):
        logger.info("Directory already exists. Skipping adding splunkupgrader to deployment-apps.")
    else:
        logger.info("Adding splunkupgrader app to deployment-apps.")
        copytree(src_dir, dest_dir, ignore=ignore_patterns('local', 'serverclass.conf'))



    
    
# set_remote_login(token, remote_server, remote_port)

# depClient(username, password, remote_server, remote_port, dep_server, dep_port)
# splunk_restart(token, remote_server, remote_port)
# disable_remote_login(token, remote_server, remote_port)
