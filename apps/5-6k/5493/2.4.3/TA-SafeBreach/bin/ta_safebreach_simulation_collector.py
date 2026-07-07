"""This module contains the data collection logic."""
import ta_safebreach_declare  # noqa: F401

import datetime
import filecmp
import json
import os
import time
import re

from ta_safebreach_mapping import mapping

from ta_safebreach_api_client import APIClient
from ta_safebreach_parser import parse
from ta_safebreach_errors import APIError
from solnlib.splunkenv import make_splunkhome_path
import traceback
from copy import deepcopy

STATUS_MAP = {
"SUCCESS": 'Not Blocked',
"FAIL": 'Blocked',
"INTERNAL_FAIL": 'Internal Fail',
"ASSUMED_BLOCKED": "Assumed Blocked"
}
class SimulationCollector(object):
    """Simulation collector."""

    def __init__(self, helper, ew):
        """Initialize Env."""
        self.helper = helper
        self.event_writer = ew
        self.input = helper.get_input_stanza_names()
        self.index = helper.get_arg('index')
        self.account = helper.get_arg('safebreach_account')
        self.account_id = self.account.get('account_id')
        self.api_key = self.account.get('api_token')
        self.account_name = self.account.get('name')
        self.start_time = helper.get_arg('start_date_time')
        self.offset = helper.get_arg('offset')
        self.extra_fields_to_parse = [field_to_parse for fields in helper.get_arg('extra_fields_to_parse') for field_to_parse in re.split(r"[,~]+", fields)]
        self.check_point_key = "{}_{}_".format(self.account_name, self.input) + "simulation"
        self.check_point = helper.get_check_point(self.check_point_key)

        self.session_key = self.helper.context_meta["session_key"]
        self.simulation_client = APIClient(self.session_key, self.helper)
        self.header = {
            'x-apitoken': self.api_key
        }
        # Making a copy of mapping to update it with the custom fields to be parsed
        self.mapping = deepcopy(mapping)

        # Adding all the selected custom fields to be added
        for field_to_add in self.extra_fields_to_parse:
            self.mapping[field_to_add] = SimulationCollector.__convert_to_snake_case(field_to_add)

    @staticmethod
    def __convert_to_snake_case(string_to_convert):
        return re.sub(r'([a-z])([A-Z])', r'\1_\2', string_to_convert).lower()

    def get_test_summaries_finished_correlation(self, start_time, end_time):
        query_data = f'siemCorrelationEndTime:[{start_time} TO {end_time}]'
        params = {'query':query_data, 'sortBy':'endTime'}
        return self.simulation_client.get_summaries(params=params, header=self.header, account_id = self.account_id) 
    
    def add_simulations_results_to_splunk(self, plan_run_ids):
        page = 1
        page_size = 500
        query = " OR ".join(f'planRunId:"{id}"' for id in plan_run_ids)
        self.helper.log_info("The query is: " + query)
        while True:
            params = {'pageSize':page_size, 'page':page, 'query':query, 'sortBy':'executionTime', 'orderBy':'asc'}
            results_page = self.simulation_client.get_simulation_data(params, header=self.header, account_id = self.account_id)
            simulations = results_page["simulations"]
            if len(simulations) > 0:
                self.add_simulations_results_as_comments(simulations)
                page += 1
            if len(simulations) < page_size:
                break
        
        

    def add_simulations_results_as_comments(self, simulations):
        for simulation in simulations:
            output = {}
            try:
                parse(simulation, self.mapping, output)
                self.normalize_status_and_result(output)
            except (ValueError, IndexError):
                self.helper.log_error("Error occurred while parsing event with the simulation_id:  {}".format(simulation["jobId"]))  # noqa: E501
                continue
            parsed_event = json.dumps(output, ensure_ascii=False)
            event = self.helper.new_event(
                        source=self.helper.get_input_type(),
                        index=self.index,
                        sourcetype=self.helper.get_sourcetype(),
                        data=parsed_event
                    )
            self.event_writer.write_event(event)
        self.helper.log_info(f"Number of simulations collected:{len(simulations)}")
    
            
    
    def normalize_status_and_result(self, simulation):
        simulation["result"] = STATUS_MAP[simulation["result"]]
        simulation["status"] = simulation["status"].capitalize()
        
    def split_plan_run_ids_into_chunks(self,plan_run_ids_total, chunk_size=5):
        return [plan_run_ids_total[i:i + chunk_size] for i in range(0, len(plan_run_ids_total), chunk_size)]

    def collect_data(self):
        """Collect and ingest data to the splunk."""
        end_time = ((datetime.datetime.utcnow() - datetime.timedelta(minutes=int(self.offset))).strftime("%Y-%m-%dT%H:%M:%S.%fZ"))[:-4] + "Z"  # noqa: E501
        checkpoint = self.helper.get_check_point(self.check_point_key)
        start_time = checkpoint or self.start_time
        self.helper.log_info(f"start time: {start_time} and end time: {end_time} - window time")
        self.helper.log_debug(f"checkpoint of simulations collector value before the collection is: {checkpoint}")   

        try:
            self.helper.log_info("Test summaries Collection Started")
            test_summaries = self.get_test_summaries_finished_correlation(start_time, end_time)
            plan_run_ids_total = [summary.get("planRunId") for summary in test_summaries if summary.get("planRunId")]
            if len(plan_run_ids_total) == 0:
                self.helper.log_info(f"No tests finished on the requested time.")
            else:
                start_event_collection_time = time.time()
                plan_run_ids_total.reverse()
                plan_run_ids_splitted = self.split_plan_run_ids_into_chunks(plan_run_ids_total)
                self.helper.log_info("Simulations Collection Started")
                for plan_run_ids in plan_run_ids_splitted:
                    self.add_simulations_results_to_splunk(plan_run_ids)
                elapsed_time_event_collection = (time.time() - start_event_collection_time)
                self.helper.log_info("Time while simulations collection is {}".format(elapsed_time_event_collection))
                self.helper.log_info("Simulations collection completed")
            self.update_mitre_lookup() 
        except APIError as e:
            self.helper.log_error("Exception occurred while calling API: {}".format(e))
        except Exception as e:
            self.helper.log_error(traceback.format_exc(e))
        finally:
            checkpoint = end_time
            self.helper.save_check_point(self.check_point_key, checkpoint)
            self.helper.log_info(f"Simulation's collector checkpoint value (the end time of the last window) after collection is: {checkpoint}, Account:{self.account_name}")

    def update_mitre_lookup(self):
        '''Update the lookup file of mitre from tactic to techniques'''
        try:
            checkpoint = self.helper.get_check_point("sb_mitre_lookup_checkpoint")
            # if checkpoint is not found then just updating it for the first time
            if checkpoint:
                # checking if its been a day since the last lookup update
                cur_time = datetime.datetime.utcnow()
                previous_lookup_update = datetime.datetime.utcfromtimestamp(checkpoint)
                if (cur_time - previous_lookup_update).total_seconds() < 86400:
                    return
                checkpoint = cur_time.timestamp()
            else:
                cur_time = datetime.datetime.utcnow()
                checkpoint = cur_time.timestamp()

            mitre_data =  self.simulation_client.get_mitre_attck_data(self.header)
            mapping_tt = { element.get("id"):"|".join(element.get("tactics", [])) for element in mitre_data if element.get("id").find(".")<0 }
            csv_str = "\"technique_id\", \"tactic_id\"\n"
            for key in mapping_tt:
                csv_str += '"{}","{}"\n'.format(key,mapping_tt[key])
            temp_file = SimulationCollector.get_lookup_path("sb_mitre_tt_lookup_new.csv")
            main_lookup_file = SimulationCollector.get_lookup_path("sb_mitre_tt_lookup.csv")

            lookup_file = open(temp_file, "w")
            lookup_file.write(csv_str)
            lookup_file.close()

            if (not os.path.exists(main_lookup_file)) or \
                (filecmp.cmp(temp_file, main_lookup_file) == False):
                os.rename(temp_file,main_lookup_file)
            else:
                os.remove(temp_file)

        except APIError as e:
            self.helper.log_error("Exception occured while creating mitre lookup: {}".format(e.message))
        except Exception as e:
            import traceback
            self.helper.log_error(traceback.format_exc(e))
        finally:
            self.helper.save_check_point("sb_mitre_lookup_checkpoint",checkpoint)
            self.helper.log_info(f"Update mitre loopkup checkpoint value is: {checkpoint}")

    @staticmethod
    def get_lookup_path(file_name):
        # create a lookup path uptill file
        lookup_folder = ["etc","apps","TA-SafeBreach","lookups"]
        if file_name:
            lookup_folder.append(file_name)

        return make_splunkhome_path(lookup_folder)
