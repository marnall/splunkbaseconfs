from ta_picus_security_api_client import ApiClient
import json
import time

class Collector:

    def __init__(self, helper, ew):

        self.helper = helper
        self.ew = ew
        self.account = helper.get_arg('picus_account')
        self.apiClient = ApiClient(helper,ew)
        self.input_name = helper.get_input_stanza_names()
        self.index = helper.get_arg('index')


    def write_index(self, resp_data):

        event = self.helper.new_event(
                    source=self.helper.get_input_type(),
                    index=self.index,
                    sourcetype=self.helper.get_sourcetype(),
                    data=resp_data
                )

        self.ew.write_event(event)


    def collect_simulation_list(self):

        simDet_list = self.apiClient.get_simulation_list()
        if simDet_list is not None:
            for i in simDet_list['simulations']:
                resp_data = json.dumps(i)
                self.write_index(resp_data)


    def collect_agent_detail(self):

        agent_list = self.apiClient.get_agent_detail()
        #id_count = len(agent_list['agents'])
        if agent_list is not None:

            id_count = len(agent_list)

            for i in range(0, id_count):
                #resp_data = json.dumps(agent_list['agents'][i])
                resp_data = json.dumps(agent_list[i])
                self.write_index(resp_data)


    def collect_integrations(self):

        int_list = self.apiClient.get_integrations()

        if int_list is not None:
            id_count = len(int_list)

            for i in range(0, id_count):

                resp_data = json.dumps(int_list[i])
                self.write_index(resp_data)


    def collect_integration_agents(self):

        int_agentlist = self.apiClient.get_integration_agents()

        if int_agentlist is not None: 
            id_count = len(int_agentlist)

            for i in range(0, id_count):

                resp_data = json.dumps(int_agentlist[i])
                self.write_index(resp_data)

    def collect_mitigation_devices(self):

        m_devices = self.apiClient.get_mitigation_devices()
        if m_devices is not None:
            for i in m_devices:
                resp_data = json.dumps(i)
                self.write_index(resp_data)


    def collect_latest_runs(self):

        latest_runs = self.apiClient.get_latest_runs()
        if latest_runs is not None:
            for run in latest_runs:
                resp_data = json.dumps(run)
                self.write_index(resp_data)


    def collect_audit(self, latest_time, interval):

        # First Run
        offset = 0
        total_count = 0
        updated_time = latest_time
        end_time = int(time.time())
        at_log = self.apiClient.get_audit_logs(latest_time, end_time, interval, offset)
        if at_log is not None:
            # Get Pagination Info
            total_count = at_log['pages']['total_count']
            for log in at_log['activity_logs']:
                resp_data = json.dumps(log)
                self.write_index(resp_data)

            # Get latest log time
            # updated_time = at_log['activity_logs'][0]['event_epoch_time']



        # Do not collect all logs if its the first run.
        if latest_time == 0:
            total_count = 50

        total_count = int(total_count)
        # Other Runs
        if total_count > 50:
            for offset in range(50, total_count, 50):
                time.sleep(0.5)
                at_log = self.apiClient.get_audit_logs(latest_time, end_time, interval, offset)
                if at_log is not None:
                    for log in at_log['activity_logs']:
                        resp_data = json.dumps(log)
                        self.write_index(resp_data)


        updated_time = end_time

        return updated_time
