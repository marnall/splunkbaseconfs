import sys,os
import requests
import json
import ccm_module
import splunk_module


from requests.sessions import session
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.modularinput import *
import splunklib.client as client
from requests.packages.urllib3.util.retry import Retry
import logging
import re
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)
app = __file__.split(os.sep)[-3]
BASE_URL = "https://api.tdm.socprime.com/v1/"

class MyScript(Script):
    def __init__(self):
        self.mask = "*****************"

    def get_scheme(self):
        scheme = Scheme("SOC Prime CCM App for Splunk")
        scheme.use_external_validation = True
        scheme.use_single_instance = False
        scheme.description = "Stream Splunk Alerts from the SOC Prime Platform."

        client_secret_id = Argument("client_secret_id")
        client_secret_id.title = "CCM API key"
        client_secret_id.description = "Copy it from https://tdm.socprime.com/api-access/"
        client_secret_id.data_type = Argument.data_type_string
        client_secret_id.required_on_create = True
        client_secret_id.required_on_edit = True
        scheme.add_argument(client_secret_id)

        job_names_list = Argument("job_names_list")
        job_names_list.title = "Jobs"
        job_names_list.description = "Specify the names of Jobs configured in CCM. Format: [\"<job1>\", \"<job2>\", ... ]."
        job_names_list.data_type = Argument.data_type_string
        job_names_list.required_on_create = True
        job_names_list.required_on_edit = True
        scheme.add_argument(job_names_list)

        splunk_default_host_port_list = Argument("splunk_default_host_port_list")
        splunk_default_host_port_list.title = "Splunk REST API host and port"
        splunk_default_host_port_list.description = "May be necessary for remote content installation. Format: [\"<splunk_host>:<port>\"]. Default: [\"localhost:8089\"]."
        splunk_default_host_port_list.data_type = Argument.data_type_string
        splunk_default_host_port_list.required_on_create = False
        splunk_default_host_port_list.required_on_edit = False
        scheme.add_argument(splunk_default_host_port_list)

        splunk_default_restapi_user = Argument("splunk_default_restapi_user")
        splunk_default_restapi_user.title = "Splunk REST API username"
        splunk_default_restapi_user.description = "May be necessary for remote content installation."
        splunk_default_restapi_user.data_type = Argument.data_type_string
        splunk_default_restapi_user.required_on_create = False
        splunk_default_restapi_user.required_on_edit = False
        scheme.add_argument(splunk_default_restapi_user)

        splunk_default_restapi_password = Argument("splunk_default_restapi_password")
        splunk_default_restapi_password.title = "Splunk REST API password"
        splunk_default_restapi_password.description = "May be necessary for remote content installation."
        splunk_default_restapi_password.data_type = Argument.data_type_string
        splunk_default_restapi_password.required_on_create = False
        splunk_default_restapi_password.required_on_edit = False
        scheme.add_argument(splunk_default_restapi_password)

        proxy_server = Argument("proxy_server")
        proxy_server.title = "Proxy server"
        proxy_server.description = "Optionally, specify proxy server for connection to CCM. Format: <host>:<port>."
        proxy_server.data_type = Argument.data_type_string
        proxy_server.required_on_create = False
        proxy_server.required_on_edit = False
        scheme.add_argument(proxy_server)

        rule_exception_list = Argument("rule_exception_list")
        rule_exception_list.title = "Rule exceptions"
        rule_exception_list.description = "Optionally, specify rules to exclude from deployment. Format: [\"<rule_name1>\", \"<rule_name2>\", ... ]."
        rule_exception_list.data_type = Argument.data_type_string
        rule_exception_list.required_on_create = False
        rule_exception_list.required_on_edit = False
        scheme.add_argument(rule_exception_list)

        return scheme

    def get_job_list_from_tdm(self, client_secret_id, proxy_server):
        URL_PREFIX = "ccm/jobs"
        headers = {
            'client_secret_id': client_secret_id
        }
        try:
            response = requests.get(url=f'{BASE_URL}{URL_PREFIX}/', headers=headers, proxies=proxy_server)
        except Exception as e:
            raise ValueError(f'Error while validation session. Error message: {e}')
        if response.ok:
            return response.json()
        else:
            raise ValueError(f'Error during validation process. Response status code: {response.status_code}. Error message: {response.text}.')

    def get_id_from_name(self, job_names_list, get_job_list_from_tdm):
        id_list = []
        for a in job_names_list:
            for b in get_job_list_from_tdm:
                if a == b['name']:
                    id_list.append(b['id'])
        return id_list

    def validate_input(self, validation_definition):

        if "proxy_server" in validation_definition.parameters:
            if validation_definition.parameters["proxy_server"] is not None:
                proxy_server = {"http": validation_definition.parameters["proxy_server"], "https": validation_definition.parameters["proxy_server"]}
            else:
                proxy_server = {}
        else:
            proxy_server = {}

        def check_array_validation(param_name):
            if param_name in validation_definition.parameters:
                if validation_definition.parameters[param_name] is not None:
                    rule_exception_list = str(validation_definition.parameters[param_name])
                    try:
                        ist_obj = json.loads(validation_definition.parameters[param_name])
                        if not isinstance(ist_obj,list):
                            raise ValueError(f'Error during validation process. Error message: Please specify {param_name} in array format.')
                    except:
                        raise ValueError(f'Error during validation process. Error message: {param_name} is not in array format.')
        for elem in ["rule_exception_list", "splunk_default_host_port_list", "job_names_list"]:
            check_array_validation(elem)

        if validation_definition.parameters["client_secret_id"] != self.mask:
            if "job_names_list" in validation_definition.parameters:
                if validation_definition.parameters["job_names_list"] != "" and validation_definition.parameters["job_names_list"] is not None:
                    job_names_list = json.loads(validation_definition.parameters["job_names_list"])
                    get_job_list_from_tdm = self.get_job_list_from_tdm(validation_definition.parameters["client_secret_id"], proxy_server)
                    if len(job_names_list) > 0 and len(get_job_list_from_tdm) > 0:
                        id_list = self.get_id_from_name(job_names_list,get_job_list_from_tdm)
                        if len(id_list) == 0:
                            raise ValueError(f'Error during validation process. Check your Jobs List settings in Splunk and TDM.')
                    else:
                        raise ValueError(f'Error during validation process. Jobs list error.')
                else:
                    raise ValueError(f'Error during validation process. Job list is empty.')
            else:
                raise ValueError(f'Error during validation process. Job list is empty.')

    def encrypt_password(self, username, password, session_key):
        args = {"token":session_key, "app": app}
        service = client.connect(**args)
        try:
            for storage_password in service.storage_passwords:
                if storage_password.username == username:
                    service.storage_passwords.delete(username=storage_password.username)
            service.storage_passwords.create(password, username)
        except Exception as e:
            message = f'An error occurred updating credentials. Please ensure your user account has admin_all_objects and/or list_storage_passwords capabilities. Details: {str(e)}'
            logging.info(message)
            raise Exception(message)

    def mask_password(self, session_key, kwargs):
        try:
            args = {"token":session_key, "app": app}
            service = client.connect(**args)
            kind, input_name = self.input_name.split("://")
            item = service.inputs.__getitem__((input_name, kind))
            item.update(**kwargs).refresh()
        except Exception as e:
            message = f'Error updating inputs.conf: {str(e)}'
            logging.error(message)
            raise Exception(message)

    def get_password(self, session_key, username):
        args = {"token":session_key, "app": app}
        service = client.connect(**args)

        for storage_password in service.storage_passwords:
            if storage_password.username == username:
                return storage_password.content.clear_password

    def stream_events(self, inputs, ew):

        session_key = self._input_definition.metadata["session_key"]
        logging.info(f'Starting input script. All saved searches will be installed in to the {app} application.')
        for self.input_name, self.input_item in inputs.inputs.items():
            kind, input_name = self.input_name.split("://")
            client_secret_id = self.input_item["client_secret_id"]
            logging.info(f'Start Input processing: {input_name}')

            if "splunk_default_restapi_user" in self.input_item:
                splunk_default_restapi_user = self.input_item["splunk_default_restapi_user"]
            else:
                splunk_default_restapi_user = ""

            if "splunk_default_restapi_password" in self.input_item:
                splunk_default_restapi_password = self.input_item["splunk_default_restapi_password"]
            else:
                splunk_default_restapi_password = ""

            if "splunk_default_host_port_list" in self.input_item:
                if self.input_item["splunk_default_host_port_list"] is not None:
                    splunk_default_host_port_list = json.loads(self.input_item["splunk_default_host_port_list"])
                else:
                    splunk_default_host_port_list = ["localhost:8089"]
            else:
                splunk_default_host_port_list = ["localhost:8089"]

            if "rule_exception_list" in self.input_item:
                if self.input_item["rule_exception_list"] is not None:
                    rule_exception_list = json.loads(self.input_item["rule_exception_list"])
                else:
                    rule_exception_list = []
            else:
                rule_exception_list = []

            if "job_names_list" in self.input_item:
                job_names_list = json.loads(self.input_item["job_names_list"])
                job_names_list_str = self.input_item["job_names_list"]
            else:
                job_names_list = []
                job_names_list_str = ''

            if "proxy_server" in self.input_item:
                if self.input_item["proxy_server"] is not None and self.input_item["proxy_server"] != '':
                    proxy_server = {"http": self.input_item["proxy_server"], "https": self.input_item["proxy_server"]}
                else:
                    proxy_server = {}
            else:
                proxy_server = {}

            # #encrypt and mask credentials###
            mylistofcreds = [(job_names_list_str, client_secret_id, "job_names_list"), (splunk_default_restapi_user, splunk_default_restapi_password, "splunk_default_restapi_user")]
            for k,v,z in mylistofcreds:
                try:
                    if v != self.mask and v != "" and v is not None:
                        self.encrypt_password(k, v, session_key)
                        if z == "job_names_list":
                            kwargs = {
                            "job_names_list": job_names_list_str,
                            "client_secret_id": self.mask,
                            "splunk_default_restapi_user": splunk_default_restapi_user,
                            "splunk_default_restapi_password": splunk_default_restapi_password
                            }
                        if z == "splunk_default_restapi_user":
                             kwargs = {
                            "job_names_list": job_names_list_str,
                            "client_secret_id": client_secret_id,
                            "splunk_default_restapi_user": splunk_default_restapi_user,
                            "splunk_default_restapi_password": self.mask
                             }
                        self.mask_password(session_key, kwargs)
                except Exception as e:
                    logging.error(f'Error: {str(e)}')

            client_secret_id = self.get_password(session_key, job_names_list_str)
            splunk_default_restapi_password = self.get_password(session_key, splunk_default_restapi_user)

            logging.info(f'Start processing all Jobs.')
            get_job_list_from_tdm = self.get_job_list_from_tdm(client_secret_id, proxy_server)
            results = []
            if len(job_names_list) > 0 and len(get_job_list_from_tdm) > 0:
                id_list = self.get_id_from_name(job_names_list,get_job_list_from_tdm)
                if len(id_list) == 0:
                    logging.info(f'Job ID list is empty. Check your Job List parameter.')
                    exit(0)
                elif len(id_list) > 0:
                    for job_id in id_list:
                        cntnt = ccm_module.InputCCM(client_secret_id, job_id, BASE_URL, proxy_server)
                        result = cntnt.get_data_from_ccm()
                        logging.info(f'Processing Job ID:{job_id}. Results count: {len(result)}.')
                        if len(result) > 0:
                            results += result
            if len(results) > 0:
                for savedsearch in results:
                    if savedsearch["case"]["name"] in rule_exception_list:
                        logging.info(f'The savedsearch \"{savedsearch["case"]["name"]}\" will be deleted from results because this rule in the Exception List.')
                        results.remove(savedsearch)
            logging.info(f'The total number of savedsearches according to your Job Lists: {len(results)}')
            if len(results) < 0:
                exit(0)
            successfully_installed_rules = []
            for splunk_host_port in splunk_default_host_port_list:
                if splunk_host_port in ["localhost:8089", "127.0.0.1:8089"]:
                    conf = {
                            "host": "localhost",
                            "port": 8089,
                            "token": session_key,
                            "app": app
                            }
                    splout = splunk_module.OutputSplunk(conf)
                else:
                    splunk_default_hostname, splunk_default_port = splunk_host_port.split(":")
                    if splunk_default_restapi_user is None or splunk_default_restapi_password is None:
                        raise ValueError(f'Error. Splunk API User or Password is not set.')
                    conf = {
                            "host": splunk_default_hostname,
                            "port": int(splunk_default_port),
                            "username": splunk_default_restapi_user,
                            "password": splunk_default_restapi_password,
                            "app": app
                            }
                    logging.info(conf)
                    splout = splunk_module.OutputSplunk(conf)
                splout.bulk_create_saved_search(results)
                if len(splout.successfully_installed_rules) > 0 and splout.successfully_installed_rules not in successfully_installed_rules:
                    successfully_installed_rules += splout.successfully_installed_rules
                if len(successfully_installed_rules) > 0:
                    cntnt.post_ccm_stat_gen_chunks(successfully_installed_rules)

if __name__ == "__main__":
    sys.exit(MyScript().run(sys.argv))
