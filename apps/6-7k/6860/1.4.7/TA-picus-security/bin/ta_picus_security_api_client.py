import json
import urllib.parse
import time

class ApiClient:

    acc_tok=""

    def __init__(self, helper, ew):

        self.helper = helper
        self.ew = ew
        self.account = self.helper.get_arg('picus_account')


    def get_access_token(self):

        self.ref_tok = self.account['refresh_token']
        api_url = self.account['picus_api_url']

        api_url = api_url.replace("/v1/activity-logs","")
        api_url = api_url + "/v1/auth/token"
        payload_data = "{\"refresh_token\":\"" + self.ref_tok + "\"}"

        response = self.helper.send_http_request(api_url, "POST", payload=payload_data, headers={'Content-Type': 'application/json'}, verify="/opt/splunk/etc/apps/TA-picus-security/bin/ta_picus_security/aob_py3/certifi/cacert.pem", use_proxy=False)
        global acc_tok

        response_data = json.loads(response.text)
        try:
            acc_tok = response_data['token']
        except:
            event = self.helper.new_event(
                    source=self.helper.get_input_type(),
                    index=self.helper.get_arg('index'),
                    sourcetype=self.helper.get_sourcetype(),
                    data="Could not retrieve access token. Please check your refresh token."
                    )
            self.ew.write_event(event)


    def make_request(self, req_type, api_endpt, payld_data):

        global acc_tok

        api_url = self.account['picus_api_url']
        api_url = api_url + api_endpt
        auth = "Bearer " + acc_tok
        header_list = {'Content-Type': 'application/json', 'Authorization': auth}

        response = self.helper.send_http_request(api_url, req_type, payload=payld_data, headers=header_list, verify=True, use_proxy=False)

        if response.status_code == 200:
            resp_data = json.loads(response.text)
            return resp_data


    def get_simulation_list(self):

        try:
            return self.make_request("GET", "/v1/simulations?limit=50", "")
        except:
            self.helper.log_error("Please make sure you have added at least one simulation.")


    def get_audit_logs(self, latest_time, end_time, interval, offset):

        try:
            early_time = str(latest_time)
            end_time = str(end_time)
            if latest_time == 0:
                craft = "?offset=" + str(offset) + "&limit=50"
            else:
                craft = "?date_start=" + early_time + "&date_end=" + end_time + "&offset=" + str(offset) + "&limit=50"
            return self.make_request("GET", craft, "")
        except:
            self.helper.log_error("Could not collect audit logs.")


    def get_latest_runs(self):

        sim_list = self.get_simulation_list()
        latest_runs = []
        if sim_list is not None:
            for sim in sim_list['simulations']:

                sim_id = sim['simulation_id']
                endpt = "/v1/simulations/" + str(sim_id) + "/run/latest"
                latest_run = self.make_request("GET", endpt, "")

                if latest_run is not None:
                    latest_runs.append(latest_run)

            return latest_runs

    def get_agent_list(self):

        try:
            return self.make_request("GET", "/v1/agents", "")
        except:
            self.helper.log_error("Please make sure you have configured agents.")


    def get_agent_detail(self):

        agent_list = self.get_agent_list()

        if agent_list is not None:
            id_count = len(agent_list['agents'])

            details = []

            for i in range(0, id_count):

                endpt = "/v1/agents/" + str(agent_list['agents'][i]['id'])            
                details.append(self.make_request("GET", endpt, ""))

            return details


    def get_integrations(self):

        try:
            integrations = self.make_request("GET", "/v1/integrations", "")
            int_count = len(integrations['integrations'])
            int_update = []

            for i in range(0, int_count):

                int_update.append(integrations['integrations'][i])

            return int_update

        except:
            self.helper.log_error("You have no integrations.")


    def get_integration_agents(self):

        try:
            int_agents = self.make_request("GET", "/v1/integrations/agents", "")
            int_count = len(int_agents['integration_agents'])
            intag_update = []

            for i in range(0, int_count):

                intag_update.append(int_agents['integration_agents'][i])

            return intag_update
        except:
            self.helper.log_error("You have no integration agents.")


    def get_mitigation_devices(self):

        try:
            return self.make_request("GET","/v1/mitigation/devices","")
        except:
            self.helper.log_error("Please make sure you have configured mitigation devices.")
