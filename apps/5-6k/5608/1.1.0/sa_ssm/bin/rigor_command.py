#!/usr/bin/env python
# coding=utf-8
#
# Copyright © 2011-2015 Splunk, Inc.
#
# Licensed under the Apache License, Version 2.0 (the 'License'): you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS IS' BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
 
from __future__ import absolute_import, division, print_function, unicode_literals
import datetime, os, sys, time, json, requests, re
import logging
import uuid

current_path = os.path.dirname(__file__)
sys.path.append(os.path.join(current_path, 'libs'))

from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

import requests
 
@Configuration()
class RigorCommand(GeneratingCommand):
    
    # rigor command parameters
    id                      = Option()
    metric_name             = Option()
    check_id                = Option()
    test_id                 = Option()
    snapshot_id             = Option()
    defect_check_policy_id  = Option()

    # Constants
    SPLUNK_PASSWORD_REALM = 'realm'
    SPLUNK_PASSWORD_USER_NAME  = 'username'
    SPLUNK_PASSWORD_CLEAR_PASSWORD  = 'clear_password'
    SPLUNK_KV_STORE_RIGOR_CONFIG_COLLECTION_NAME = 'ssm_api_config'
    SPLUNK_RIGOR_CONFIG_API_URL_KEY = 'api_url'
    SPLUNK_PASSWORDS_STORAGE_RIGOR_API_TOKEN_REALM = 'ssm_search_command'
    SPLUNK_PASSWORDS_STORAGE_RIGOR_API_TOKEN_USER_NAME  = 'access_token'
    SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME = 'access_token_wo'
    SPLUNK_RIGOR_CONF_NAME = 'rigor'
    SPLUNK_RIGOR_CONF_API_STANZA_NAME = 'rigor_api'
    
    RIGOR_API_TIMEOUT_DEFAULT = 5
    RIGOR_API_VERIFY_SSL = True
    RIGOR_API_CHECKS_PER_PAGE = 100
    RIGOR_API_RUNS_PER_PAGE = 100


    EMPTY_SEARCH_RESULTS = []

    RIGOR_API_CHECKS_ENDPOINT = "checks"
    RIGOR_API_KPI_ENDPOINT = "checks/real_browsers/{id}/performance_kpis/data?metrics[]={metric_name}"
    RIGOR_API_RUNS_ENDPOINT = "checks/real_browsers/{check_id}/runs"
    RIGOR_API_RUN_ENDPOINT = "checks/real_browsers/{check_id}/runs/{id}"
    #RIGOR_API_WO_TESTS_ENDPOINT = "tests"
    RIGOR_API_TESTS_ENDPOINT = "tests"
    RIGOR_API_TEST_ENDPOINT = "tests/{test_id}"
    RIGOR_API_SNAPSHOTS_ENDPOINT = "tests/{test_id}/snapshots"
    RIGOR_API_SNAPSHOT_ENDPOINT = "tests/{test_id}/snapshots/{snapshot_id}"
    RIGOR_API_POLICIES_ENDPOINT = "defect_policies"
    RIGOR_API_POLICY_CHECKS_ENDPOINT = "defect_policies/{defect_check_policy_id}/defect_checks"
    RIGOR_API_DEFECTS_ENDPOINT = "tests/{test_id}/snapshots/{snapshot_id}/defects"

    class SubCommands:
        CHECKS        = 'checks'
        KPI           = 'kpi'
        RUNS          = 'runs'
        RUN           = 'run' 
        TESTS         = 'tests'
        TEST          = 'test'
        SNAPSHOTS     = 'snapshots'
        SNAPSHOT      = 'snapshot'
        POLICIES      = 'policies'
        POLICY_CHECKS = 'policy_checks'
        DEFECTS       = 'defects'
        #WO = 'wo'

    COMMAND_TO_API_TOKENS = {}
    COMMAND_TO_API_TOKENS[SubCommands.CHECKS]        = SPLUNK_PASSWORDS_STORAGE_RIGOR_API_TOKEN_USER_NAME
    COMMAND_TO_API_TOKENS[SubCommands.KPI]           = SPLUNK_PASSWORDS_STORAGE_RIGOR_API_TOKEN_USER_NAME           
    COMMAND_TO_API_TOKENS[SubCommands.RUNS]          = SPLUNK_PASSWORDS_STORAGE_RIGOR_API_TOKEN_USER_NAME          
    COMMAND_TO_API_TOKENS[SubCommands.RUN]           = SPLUNK_PASSWORDS_STORAGE_RIGOR_API_TOKEN_USER_NAME          
    COMMAND_TO_API_TOKENS[SubCommands.TESTS]         = SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME         
    COMMAND_TO_API_TOKENS[SubCommands.TEST]          = SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME          
    COMMAND_TO_API_TOKENS[SubCommands.SNAPSHOTS]     = SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME     
    COMMAND_TO_API_TOKENS[SubCommands.SNAPSHOT]      = SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME     
    COMMAND_TO_API_TOKENS[SubCommands.POLICIES]      = SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME      
    COMMAND_TO_API_TOKENS[SubCommands.POLICY_CHECKS] = SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME 
    COMMAND_TO_API_TOKENS[SubCommands.DEFECTS]       = SPLUNK_PASSWORDS_STORAGE_RIGOR_WO_API_TOKEN_USER_NAME       

    # internal class variables
    rigor_api_url = "https://monitoring-api.rigor.com/v2/"
    rigor_api_wo_url = "https://optimization-api.rigor.com/v2/"
    rigor_api_token = None  

    class LoggerContextFilter(logging.Filter):
        """
        This is a filter which injects command invocation instance UUID in the logs.
        """
        request_id = uuid.uuid4().hex
        def filter(self, record):
            record.request_id = self.request_id
            return True

    def generate(self):

        self.logger.addFilter(self.LoggerContextFilter())

        # get subcommand. ex: 'checks' 
        if not self.fieldnames:
            self.logger.error('status=error, action=execute_rigor_command, error_code=no_sub_command')
            self.write_command_error('Invalid arguments. No subcommand specified.')
            return self.EMPTY_SEARCH_RESULTS

        self.rigor_sub_command = self.fieldnames[0]

        # Search Command parameters initialization #####################################################################################
        self.logger.info('status=start, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))
        self.timeout = self.RIGOR_API_TIMEOUT_DEFAULT
        #trailing slash sanity check
        self.rigor_api_url = self.rigor_api_url if self.rigor_api_url[-1] == '/' else self.rigor_api_url+"/"
        
        self.rigor_api_token = self.get_rigor_api_token(self.COMMAND_TO_API_TOKENS[self.rigor_sub_command])
        if self.rigor_api_token is None:
            self.logger.error('status=error, action=get_rigor_api_token, sub_command={0}, error_msg=Rigor API Access token not configured.'.format(self.rigor_sub_command))
            self.write_command_error('Rigor API Access token not configured.')
            return self.EMPTY_SEARCH_RESULTS
        
        
        # get search search_earliest_time and search_latest_time 
        if self.metadata and self.metadata.searchinfo and self.metadata.searchinfo.latest_time:
            self.search_latest_time = int(self.metadata.searchinfo.latest_time * 1000)
        else:
            # set 10 min from current time as search_latest_time
            self.search_latest_time = int(time.time()*1000) - 600000
            self.logger.info('action=set_default_latest_time, sub_command={0}, value={1}'.format(self.rigor_sub_command, str(self.search_latest_time)))
            
        if self.metadata and self.metadata.searchinfo and self.metadata.searchinfo.earliest_time:
            self.search_earliest_time = int(self.metadata.searchinfo.earliest_time * 1000)
        else:
            # set 10 min from search_latest_time as search_earliest_time
            self.search_earliest_time = self.search_latest_time - 600000
            self.logger.info('action=set_default_earliest_time, sub_command={0}, value={1}'.format(self.rigor_sub_command, str(self.search_earliest_time)))


        # Search Command Execution #######################################################################################################
        if self.rigor_sub_command == self.SubCommands.CHECKS:
            #param validation
            #|rigor checks
            return self.execute_checks_sub_command()
        elif self.rigor_sub_command == self.SubCommands.KPI:
            #param validation
            #|rigor kpi id=123 name=first_request_ssl_time_ms
            if self.id is None or self.id.strip() is "":
                self.write_command_error('Missing parameter "id" for subcommand "kpi". See https://monitoring-api.rigor.com/docs?url=/v2/docs#!/Real_Browser_Checks/getRealBrowserPerformanceKPIs')
                return self.EMPTY_SEARCH_RESULTS
            else:
                if self.metric_name is None or self.metric_name.strip() is "":
                    self.write_command_error('Missing parameter "metric_name" for subcommand "kpi". See https://monitoring-api.rigor.com/docs?url=/v2/docs#!/Real_Browser_Checks/getRealBrowserPerformanceKPIs')
                    return self.EMPTY_SEARCH_RESULTS
            return self.execute_kpi_sub_command()
        elif self.rigor_sub_command == self.SubCommands.RUNS:
            #param validation
            #| rigor runs check_id=123
            if self.check_id is None or self.check_id.strip() is "":
                self.write_command_error('Missing parameter "check_id" for subcommand "runs". See https://monitoring-api.rigor.com/docs?url=/v2/docs#!/Real_Browser_Checks/getRealBrowserCheckRuns')
                return self.EMPTY_SEARCH_RESULTS
            return self.execute_runs_sub_command()
        elif self.rigor_sub_command == self.SubCommands.RUN:
            #param validation
            #| rigor run check_id=123 id=456
            if self.check_id is None or self.check_id.strip() is "":
                self.write_command_error('Missing parameter "check_id" for subcommand "runs". See https://monitoring-api.rigor.com/docs?url=/v2/docs#!/Real_Browser_Checks/getRealBrowserCheckRun')
                return self.EMPTY_SEARCH_RESULTS
            else:
                if self.id is None or self.id.strip() is "":
                    self.write_command_error('Missing parameter "id" for subcommand "runs". See https://monitoring-api.rigor.com/docs?url=/v2/docs#!/Real_Browser_Checks/getRealBrowserCheckRun')
                    return self.EMPTY_SEARCH_RESULTS
            return self.execute_run_sub_command()
        elif self.rigor_sub_command == self.SubCommands.TESTS:
            #none
#            Checking to seew what is returned for the tests endpoint, which is a generator object
#            my_variable = self.execute_tests_sub_command()
#            self.logger.error('action=sending all tests: ' + str(my_variable))
            return self.execute_tests_sub_command()

        elif self.rigor_sub_command == self.SubCommands.TEST:
            #test_id
            if self.test_id is None or self.test_id.strip() is "":
                self.write_command_error('Missing parameter "test_id" for subcommand "test".')
                return self.EMPTY_SEARCH_RESULTS
#            Checking to see what is returned for the test endpoint, which is a dict that is not _raw
#            my_variable = self.execute_test_sub_command()
#            self.logger.error('action=sending one test: ' + str(my_variable))
            return self.execute_test_sub_command()

        elif self.rigor_sub_command == self.SubCommands.SNAPSHOTS:
            #test_id
            if self.test_id is None or self.test_id.strip() is "":
                self.write_command_error('Missing parameter "test_id" for subcommand "snapshots".')
                return self.EMPTY_SEARCH_RESULTS
            return self.execute_snapshots_sub_command()

        elif self.rigor_sub_command == self.SubCommands.SNAPSHOT:
            #test_id snapshot_id
            if self.test_id is None or self.test_id.strip() is "":
                self.write_command_error('Missing parameter "test_id" for subcommand "snapshot".')
                return self.EMPTY_SEARCH_RESULTS
            else:
                if self.snapshot_id is None or self.snapshot_id.strip() is "":
                    self.write_command_error('Missing parameter "snapshot_id" for subcommand "snapshot".')
                    return self.EMPTY_SEARCH_RESULTS
            return self.execute_snapshot_sub_command()

        elif self.rigor_sub_command == self.SubCommands.POLICIES:
            #none
            return self.execute_policies_sub_command()

        elif self.rigor_sub_command == self.SubCommands.POLICY_CHECKS:
            #defect_check_policy_id
            if self.defect_check_policy_id is None or self.defect_check_policy_id.strip() is "":
                self.write_command_error('Missing parameter "defect_check_policy_id" for subcommand "snapshot".')
                return self.EMPTY_SEARCH_RESULTS
            return self.execute_policy_checks_sub_command()

        elif self.rigor_sub_command == self.SubCommands.DEFECTS:
            #test_id snapshot_id
            if self.test_id is None or self.test_id.strip() is "":
                self.write_command_error('Missing parameter "test_id" for subcommand "defects".')
                return self.EMPTY_SEARCH_RESULTS
            else:
                if self.snapshot_id is None or self.snapshot_id.strip() is "":
                    self.write_command_error('Missing parameter "snapshot_id" for subcommand "defects".')
                    return self.EMPTY_SEARCH_RESULTS
            return self.execute_defects_sub_command()

        else:
            self.logger.error('status=error, action=execute_rigor_command, error_code=invalid_sub_command, sub_command={0}'.format(self.rigor_sub_command))
            self.write_command_error('Invalid arguments. Subcommand {0} not found.'.format(self.rigor_sub_command))
            return self.EMPTY_SEARCH_RESULTS


    ################################################################################################################################# 
    # CHECKS SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  
     
    def execute_checks_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_checks, sub_command={0}'.format(
        self.rigor_sub_command))
        checks_count, checks_size = 0, 0
        try:
            session = self.get_session()

            params = { 
                "page": 1,
                "per_page": self.RIGOR_API_CHECKS_PER_PAGE
            }

            pages_remain = True

            while pages_remain:

                checks_json = self.rigor_api(session,self.RIGOR_API_CHECKS_ENDPOINT,params)

                if not checks_json:
                    return

                if "current_page" in checks_json:
                    if checks_json['current_page'] == checks_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = checks_json['current_page'] + 1
                else:
                    pages_remain = False

                checks_json = self.process_checks_response(checks_json)

                for check_json in checks_json:
                    try:
                        yield {'_time':self.normalize_time(check_json['timestamp']),'_raw':json.dumps(check_json)}
    
                        checks_size += sys.getsizeof(str(check_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_checks, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
            
                checks_count = checks_count + len(list(checks_json))
            

        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_checks, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Checks endpoint. error_msg={0}'.format(str(e)))
            return
            
            
        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_checks, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_checks_response(self,response):
        raw_events = []
        if type(response) == list or 'checks' in response:
            if 'checks' in response:
                response = response['checks']
    
            for result in response:
                if 'timestamp' not in result:
                    result['timestamp'] = time.time()
                raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # KPI SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  
     
    def execute_kpi_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_kpi, sub_command={0} '.format(
        self.rigor_sub_command))
        kpis_count, kpis_size = 0, 0
        try:
            session = self.get_session()

            endpoint = self.RIGOR_API_KPI_ENDPOINT.replace('{id}',self.id).replace('{metric_name}',self.metric_name)

            params = { 
                "from": self.epoch_to_string(self.search_earliest_time),
                "to": self.epoch_to_string(self.search_latest_time)
            }

            kpis_json = self.rigor_api(session,endpoint,params=params)

            if not kpis_json:
                self.write_error("Unable to find kpi for id={0} and metric_name={1}".format(self.id,self.metric_name))
                return

            kpis_json = self.process_kpis_response(kpis_json)

            for kpi_json in kpis_json:
                try:
                    yield {'_time':self.normalize_time(kpi_json['timestamp']),'_raw':json.dumps(kpi_json)}

                    kpis_size += sys.getsizeof(str(kpi_json))
                except Exception as e:
                    self.logger.error('status=error, action=execute_rigor_sub_command_kpi, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
            kpis_count = len(list(kpis_json))
            return

        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_kpi, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Checks endpoint. error_msg={0}'.format(str(e)))
            return

        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_kpi, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(kpis_count), str(kpis_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_kpis_response(self,response):
        raw_events = []


        if type(response) == list or 'series' in response:

            if 'series' in response:
                metric_data = response['series']
                del response['series']
                result_meta = response
    
                for series in metric_data:
                    
                    for metric in series['data']:
                        result = {}
                        result['meta'] = response
                        if 'time' in metric:
                            result['timestamp'] = time.mktime(time.strptime(metric['time'],"%Y-%m-%dT%H:%M:%S.%fZ"))
                        result['data'] = metric

                        raw_events.append(result)
            else:
                return self.EMPTY_SEARCH_RESULTS
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # RUNS SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  
     
    def execute_runs_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_runs, sub_command={0} '.format(
        self.rigor_sub_command))
        runs_count, runs_size = 0, 0
        try:
            session = self.get_session()

            endpoint = self.RIGOR_API_RUNS_ENDPOINT.replace('{check_id}',str(self.check_id))

            params = { 
                "from": self.epoch_to_string(self.search_earliest_time),
                "to": self.epoch_to_string(self.search_latest_time),
                "page": 1,
                "per_page": self.RIGOR_API_RUNS_PER_PAGE
            }

            pages_remain = True

            while pages_remain:

                runs_json = self.rigor_api(session,endpoint,params)

                if "current_page" in runs_json:
                    if runs_json['current_page'] == runs_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = runs_json['current_page'] + 1
                else:
                    pages_remain = False
    
                if not runs_json:
                    self.write_error("Unable to find runs for check_id={0}".format(self.check_id))
                    return
    
                runs_json = self.process_runs_response(runs_json)
    
                for run_json in runs_json:
                    try:
                        yield {'_time':self.normalize_time(run_json['timestamp']),'_raw':json.dumps(run_json)}
    
                        runs_size += sys.getsizeof(str(run_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_runs, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
            
                runs_count = runs_count + len(list(runs_json))
            return


        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_runs, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Checks endpoint. error_msg={0}'.format(str(e)))
            return

        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_runs, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(runs_count), str(runs_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_runs_response(self,response):
        raw_events = []
        if type(response) == list or 'runs' in response:
                for run in response['runs']:
                    result = run
                    if 'timestamp' in run:
                        result['timestamp'] = time.mktime(time.strptime(run['timestamp'],"%Y-%m-%dT%H:%M:%S.%fZ"))

                    raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # RUN SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  
     
    def execute_run_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_run, sub_command={0} '.format(
        self.rigor_sub_command))
        run_count, run_size = 0, 0
        try:
            session = self.get_session()

            endpoint = self.RIGOR_API_RUN_ENDPOINT.replace('{check_id}',str(self.check_id)).replace('{id}',str(self.id))

            run_json = self.rigor_api(session,endpoint)

            if not run_json:
                self.write_error("Unable to find run for check_id={0} and id={1}".format(self.check_id,self.id))
                return

            run_json = self.process_run_response(run_json)

            try:
                yield {'_time':self.normalize_time(run_json['timestamp']),'_raw':json.dumps(run_json)}

                run_size += sys.getsizeof(str(run_json))
            except Exception as e:
                self.logger.error('status=error, action=execute_rigor_sub_command_run, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
            run_count = len(list(run_json))
            return

        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_run, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Checks endpoint. error_msg={0}'.format(str(e)))
            return

        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_run, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(run_count), str(run_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_run_response(self,response):
        raw_events = []
        response['timestamp'] = time.mktime(time.strptime(response['timestamp'],"%Y-%m-%dT%H:%M:%S.%fZ"))
        return response

    ################################################################################################################################# 
    # TESTS SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  

    def execute_tests_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_tests, sub_command={0}'.format(
        self.rigor_sub_command))
        checks_count, checks_size = 0, 0
        try:
            session = self.get_session()

            params = { 
                "page": 1,
                "per_page": self.RIGOR_API_CHECKS_PER_PAGE
            }

            pages_remain = True

            while pages_remain:

                checks_json = self.rigor_wo_api(session,self.RIGOR_API_TESTS_ENDPOINT,params)

                if not checks_json:
                    return

                if "current_page" in checks_json:
                    if checks_json['current_page'] == checks_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = checks_json['current_page'] + 1
                else:
                    pages_remain = False

                checks_json = self.process_tests_response(checks_json)

                for check_json in checks_json:
                    try:
                        yield {'_time':self.normalize_time(check_json['timestamp']),'_raw':json.dumps(check_json)}
    
                        checks_size += sys.getsizeof(str(check_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_tests, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
            
                checks_count = checks_count + len(list(checks_json))
            

        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_tests, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Tests endpoint. error_msg={0}'.format(str(e)))
            return
            
            
        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_tests, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_tests_response(self,response):
        raw_events = []
        if type(response) == list or 'tests' in response:
            if 'tests' in response:
                response = response['tests']
    
            for result in response:
                if 'timestamp' not in result:
                    result['timestamp'] = time.time()
                raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # TEST SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  

    def execute_test_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_test, sub_command={0}'.format(
        self.rigor_sub_command))
        
        try:
            session = self.get_session()

            endpoint = self.RIGOR_API_TEST_ENDPOINT.replace('{test_id}',str(self.test_id))
     
            response_json = self.rigor_wo_api(session,endpoint)

            response_json['timestamp'] = time.time()
      
            yield {'_time':self.normalize_time(response_json['timestamp']),'_raw':json.dumps(response_json)}


        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_test, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Test endpoint. error_msg={0}'.format(str(e)))
            return
            
        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            #self.logger.info('status=complete, action=execute_rigor_sub_command_test, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

#    def process_test_response(self,response):
#        raw_events = []
#        if type(response) == list or 'test' in response:
#            if 'test' in response:
#                response = response['test']
    
#            for result in response:
#                if 'timestamp' not in result:
#                    result['timestamp'] = time.time()
#                raw_events.append(result)
#        else:
#            response['timestamp'] = time.time()
#            return [response]

#        return raw_events

    ################################################################################################################################# 
    # SNAPSHOTS SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  

    def execute_snapshots_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_snapshots, sub_command={0}'.format(
        self.rigor_sub_command))
        checks_count, checks_size = 0, 0
        try:
            session = self.get_session()

            params = {
                "page": 1,
                "per_page": 50
            }

            pages_remain = True

            while pages_remain:

                self.logger.error('status=error, action=execute_rigor_sub_command_snapshots, endpoint value: ' + self.RIGOR_API_SNAPSHOTS_ENDPOINT.replace('{test_id}',str(self.test_id)))

                checks_json = session.get("https://optimization-api.rigor.com/v2/" + self.RIGOR_API_SNAPSHOTS_ENDPOINT.replace('{test_id}',str(self.test_id)))
#                checks_json = session.get("https://optimization-api.rigor.com/v2/tests/104505/snapshots")
                checks_json = checks_json.json()
                checks_json['timestamp'] = time.time()

                if not checks_json:
                    return

                if "current_page" in checks_json:
                    if checks_json['current_page'] == checks_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = checks_json['current_page'] + 1
                else:
                    pages_remain = False

                checks_json = self.process_snapshots_response(checks_json)

                for check_json in checks_json:
                    try:
                        yield {'_time':self.normalize_time(check_json['timestamp']),'_raw':json.dumps(check_json)}

                        checks_size += sys.getsizeof(str(check_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_snapshots, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
                checks_count = checks_count + len(list(checks_json))


        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_snapshots, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Snapshots endpoint. error_msg={0}'.format(str(e)))
            return

        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_snapshots, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

 
    def process_snapshots_response(self,response):
        raw_events = []
        if type(response) == list or 'snapshots' in response:
            if 'snapshots' in response:
                response = response['snapshots']
    
            for result in response:
                if 'timestamp' not in result:
                    result['timestamp'] = time.time()
                raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # SNAPSHOT SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  

    def execute_snapshot_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_snapshot, sub_command={0}'.format(
        self.rigor_sub_command))
        checks_count, checks_size = 0, 0
        try:
            session = self.get_session()

            params = {
                "page": 1,
                "per_page": 50
            }

            pages_remain = True

            while pages_remain:

                self.logger.error('status=error, action=execute_rigor_sub_command_snapshot, endpoint value: ' + self.RIGOR_API_SNAPSHOT_ENDPOINT.replace('{test_id}',str(self.test_id)).replace('{snapshot_id}',str(self.snapshot_id)))

                checks_json = session.get("https://optimization-api.rigor.com/v2/" + self.RIGOR_API_SNAPSHOT_ENDPOINT.replace('{test_id}',str(self.test_id)).replace('{snapshot_id}',str(self.snapshot_id)))

                checks_json = checks_json.json()
                checks_json['timestamp'] = time.time()

                if not checks_json:
                    return

                if "current_page" in checks_json:
                    if checks_json['current_page'] == checks_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = checks_json['current_page'] + 1
                else:
                    pages_remain = False

                checks_json = self.process_snapshot_response(checks_json)

                for check_json in checks_json:
                    try:
                        yield {'_time':self.normalize_time(check_json['timestamp']),'_raw':json.dumps(check_json)}

                        checks_size += sys.getsizeof(str(check_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_snapshot, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
                checks_count = checks_count + len(list(checks_json))
        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_snapshot, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Snapshot endpoint. error_msg={0}'.format(str(e)))
            return

        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_snapshot, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_snapshot_response(self,response):
        raw_events = []
        if type(response) == list or 'snapshot' in response:
            if 'snapshot' in response:
                response = response['snapshot']
    
            for result in response:
                if 'timestamp' not in result:
                    result['timestamp'] = time.time()
                raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # POLICIES SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  

    def execute_policies_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_policies, sub_command={0}'.format(
        self.rigor_sub_command))
        checks_count, checks_size = 0, 0
        try:
            session = self.get_session()

            params = { 
                "page": 1,
                "per_page": self.RIGOR_API_CHECKS_PER_PAGE
            }

            pages_remain = True

            while pages_remain:

                checks_json = self.rigor_wo_api(session,self.RIGOR_API_POLICIES_ENDPOINT,params)

                if not checks_json:
                    return

                if "current_page" in checks_json:
                    if checks_json['current_page'] == checks_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = checks_json['current_page'] + 1
                else:
                    pages_remain = False

                checks_json = self.process_policies_response(checks_json)

                for check_json in checks_json:
                    try:
                        yield {'_time':self.normalize_time(check_json['timestamp']),'_raw':json.dumps(check_json)}
    
                        checks_size += sys.getsizeof(str(check_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_policies, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
            
                checks_count = checks_count + len(list(checks_json))
            

        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_policies, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Policies endpoint. error_msg={0}'.format(str(e)))
            return
            
        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            self.logger.info('status=complete, action=execute_rigor_sub_command_policies, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_policies_response(self,response):
        raw_events = []
        if type(response) == list or 'policies' in response:
            if 'policies' in response:
                response = response['policies']
    
            for result in response:
                if 'timestamp' not in result:
                    result['timestamp'] = time.time()
                raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # POLICY_CHECKS SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  

    def execute_policy_checks_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_policy_checks, sub_command={0}'.format(self.rigor_sub_command))
        checks_count, checks_size = 0, 0

        try:

            session = self.get_session()

            params = {
                "page": 1,
                "per_page": self.RIGOR_API_CHECKS_PER_PAGE
            }

            pages_remain = True

            while pages_remain:

                endpoint = self.RIGOR_API_POLICY_CHECKS_ENDPOINT.replace('{defect_check_policy_id}',str(self.defect_check_policy_id))
                checks_json = self.rigor_wo_api(session,endpoint)

                if not checks_json:
                    return

                if "current_page" in checks_json:
                    if checks_json['current_page'] == checks_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = checks_json['current_page'] + 1
                else:
                    pages_remain = False

                checks_json = self.process_policy_checks_response(checks_json)

                for check_json in checks_json:
                    try:
                        yield {'_time':self.normalize_time(check_json['timestamp']),'_raw':json.dumps(check_json)}

                        checks_size += sys.getsizeof(str(check_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_policy_checks, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
                pages_remain = False
                #checks_count = checks_count + len(list(checks_json))

        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_policy_checks, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Policy Checks endpoint. error_msg={0}'.format(str(e)))
            return
            
        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            #self.logger.info('status=complete, action=execute_rigor_sub_command_policy_checks, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_policy_checks_response(self,response):
        raw_events = []
        if type(response) == list or 'defects' in response:
            if 'defects' in response:
                response = response['defects']
    
            for result in response:
                if 'timestamp' not in result:
                    result['timestamp'] = time.time()
                raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events

    ################################################################################################################################# 
    # DEFECTS SUB COMMAND ############################################################################################################## 
    #################################################################################################################################  

    def execute_defects_sub_command(self):
        self.logger.info('status=start, action=execute_rigor_sub_command_defects, sub_command={0}'.format(self.rigor_sub_command))
        checks_count, checks_size = 0, 0
        try:
            session = self.get_session()

            params = {
                "page": 1,
                "per_page": 50
            }

            pages_remain = True

            while pages_remain:

                self.logger.error('status=error, action=execute_rigor_sub_command_defects, endpoint value: ' + self.RIGOR_API_DEFECTS_ENDPOINT.replace('{test_id}',str(self.test_id)).replace('{snapshot_id}',str(self.snapshot_id)))

                endpoint = self.RIGOR_API_DEFECTS_ENDPOINT.replace('{test_id}',str(self.test_id)).replace('{snapshot_id}',str(self.snapshot_id))
                checks_json = self.rigor_wo_api(session,endpoint)
                
#                checks_json = session.get("https://optimization-api.rigor.com/v2/" + self.RIGOR_API_DEFECTS_ENDPOINT.replace('{test_id}',str(self.test_id)).replace('{snapshot_id}',str(self.snapshot_id)))
#
#                checks_json = checks_json.json()
#                checks_json['timestamp'] = time.time()

                if not checks_json:
                    return

                if "current_page" in checks_json:
                    if checks_json['current_page'] == checks_json['total_pages']:
                        pages_remain = False
                    else:
                        params['page'] = checks_json['current_page'] + 1
                else:
                    pages_remain = False

                checks_json = self.process_defects_response(checks_json)

                for check_json in checks_json:
                    try:
                        yield {'_time':self.normalize_time(check_json['timestamp']),'_raw':json.dumps(check_json)}

                        checks_size += sys.getsizeof(str(check_json))
                    except Exception as e:
                        self.logger.error('status=error, action=execute_rigor_sub_command_defects, sub_command={0} error_msg='.format(self.rigor_sub_command) + str(e))
                pages_remain = False
#                checks_count = checks_count + len(list(checks_json))

        except Exception as e:
            self.logger.error('status=error, action=execute_rigor_sub_command_defects, sub_command={0}, error_msg= '.format(self.rigor_sub_command) + str(e), exc_info=True)
            self.write_command_error('Error calling Rigor API Defects endpoint. error_msg={0}'.format(str(e)))
            return
            
        finally:
            session.close()
            self.logger.info('status=process, action=close_rest_client_connection, sub_command={0}'.format(self.rigor_sub_command))
            #self.logger.info('status=complete, action=execute_rigor_sub_command_defects, sub_command={0}, events_count={1}, events_size={2}'.format(self.rigor_sub_command, str(checks_count), str(checks_size)))
            self.logger.info('status=complete, action=execute_rigor_command, sub_command={0}'.format(self.rigor_sub_command))

    def process_defects_response(self,response):
        raw_events = []
        if type(response) == list or 'defects' in response:
            if 'defects' in response:
                response = response['defects']
    
            for result in response:
                if 'timestamp' not in result:
                    result['timestamp'] = time.time()
                raw_events.append(result)
        else:
            response['timestamp'] = time.time()
            return [response]

        return raw_events


    ################################################################################################################################# 
    # Common Functions ############################################################################################################## 
    #################################################################################################################################  
    
    # Main Rigor API ############################################################################################################## 

    def rigor_api(self,session,endpoint,params={}):
        url = self.rigor_api_url + endpoint

        response_json = {}
        
        api_response = session.get(url)
        
#        if api_response.status_code == 401:
#            self.write_error("Rigor returned an error: Invalid or unauthorized access token.")
#            self.logger.error("status=error action=rigor_api error_msg=Invalid or unauthorized access token.")
#            #api_response.raise_for_status()
#            return False
        
#        if api_response.status_code == 404:
#            self.write_error("Rigor returned an error: Unable to find requested resource (%s)."%(url))
#            self.logger.error("status=error action=rigor_api error_msg=Unable to find requested resource(%s)."%(url))
            #api_response.raise_for_status()
#            return False
        
#        try:
        response_json = json.loads(api_response.text)
        
#            if 'code' in response_json and response_json['code'] != 200:
#                self.write_error("Rigor returned an error: %s. Status Code: %s"%(response_json['message'],response_json['code']))
#                self.logger.error("status=error action=rigor_api error_msg=Rigor returned an error: %s. Status Code: %s"%(response_json['message'],response_json['code']))
#                #api_response.raise_for_status()
#                return False

        return response_json

#        except:
#            self.write_error('Rigor was unable to process the request.')
#            self.logger.error("status=error action=rigor_api error_msg=Rigor was unable to process the request.")
#            return False

# Web Optimization Rigor API ############################################################################################################## 

    def rigor_wo_api(self,session,endpoint,params={}):
        url = self.rigor_api_wo_url + endpoint
        
        response_json = {}
        
        api_response = session.get(url)
        # api_response = session.get(url,timeout=self.timeout,params=params)

        
#        if api_response.status_code == 401:
#            self.write_error("Rigor Web Optimization returned an error: Invalid or unauthorized access token.")
#            self.logger.error("status=error action=rigor_api error_msg=Invalid or unauthorized access token.")
#            #api_response.raise_for_status()
#            return False
        
#        if api_response.status_code == 404:
#            self.write_error("Rigor Web Optimization returned an error: Unable to find requested resource (%s)."%(url))
#            self.logger.error("status=error action=rigor_api error_msg=Unable to find requested resource(%s)."%(url))
#            #api_response.raise_for_status()
#            return False
        
#        try:
        response_json = json.loads(api_response.text)
#            if 'code' in response_json and response_json['code'] != 200:
#                self.write_error("Rigor Web Optimization returned an error: %s. Status Code: %s"%(response_json['message'],response_json['code']))
#                self.logger.error("status=error action=rigor_api error_msg=Rigor Web Optimization returned an error: %s. Status Code: %s"%(response_json['message'],response_json['code']))
                #api_response.raise_for_status()
#                return False

        return response_json

#        except:
#            self.write_error('Rigor Web Optimization was unable to process the request.')
#            self.logger.error("status=error action=rigor_api error_msg=Rigor Web Optimization was unable to process the request.")
#            return False
        

    def get_rigor_api_token(self, token_name):
        try:
            for credential in self.service.storage_passwords:
                if ( credential.content.get(self.SPLUNK_PASSWORD_REALM, None) == self.SPLUNK_PASSWORDS_STORAGE_RIGOR_API_TOKEN_REALM and 
                    credential.content.get(self.SPLUNK_PASSWORD_USER_NAME, None) ==  token_name):
                    return credential.content.get(self.SPLUNK_PASSWORD_CLEAR_PASSWORD, None)
        except Exception as e:
            self.logger.error('status=error, action=get_rigor_api_token, sub_command={0}, error_msg='.format(self.rigor_sub_command) + str(e), exc_info=True)
        return None
    
    def write_command_error(self,message):
        message='Error in "synthetics" command: '+message
        self.write_error(message)

    def epoch_to_string(self,timestamp):
        return time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime(self.normalize_time(timestamp)))

    def normalize_time(self,timestamp):
        if timestamp is not None:
            if len(str(int(float(timestamp)))) == 10:
                #ex: 1586473882.963976
                return float(timestamp)
            else:
                ts_str = str(timestamp)
                if len(ts_str) > 10 and '.' not in ts_str:
                    return float(ts_str[:10] + '.' +ts_str[10:])

    def get_session(self):
        session = requests.Session()
        session.headers.update({
            'Content-Type': 'application/json',
            'API-KEY': self.rigor_api_token,
        })
        return session

   #################################################################################################################################
dispatch(RigorCommand, sys.argv, sys.stdin, sys.stdout, __name__)
