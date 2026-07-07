import ta_elysiumanalytics_declare  # noqa: F401
import sys
import traceback
import time
import json
import elysiumanalytics_com as com
import elysiumanalytics_const as const
import elysiumanalytics_common_utils as utils
from log_manager import setup_logging
import os
import itertools

from splunklib.searchcommands import (
    dispatch,
    GeneratingCommand,
    Configuration,
    Option,
    validators,
)
import requests
import sys
import datetime
import xmltodict
import splunklib.client as client
import re
import datetime
import splunklib.results as results


_LOGGER = setup_logging("elysiumquery_command")




@Configuration(type="events")
class ElysiumanalyticsQueryCommand(GeneratingCommand):

    # Take input from user using parameters
    # database = Option(require=False)
    # schema = Option(require=False)
    # warehouse = Option(require=False)
    # role = Option(require=False)
    statement = Option(require=True)
    timeout = Option(require=False, validate=validators.Integer(minimum=1))
    timecolumn = Option(require=False)
    timefilter = Option(require=False)
    
    def generate(self):
        
        command_timeout_in_seconds = self.timeout     
        earliest_time_epoch = self._metadata.searchinfo.earliest_time       
        latest_time_epoch = self._metadata.searchinfo.latest_time
        sid = self._metadata.searchinfo.sid

        # Get session key
        session_key = self._metadata.searchinfo.session_key
        splunkd_uri = self._metadata.searchinfo.splunkd_uri
        

        try:
            
           
            # warehouse = self.warehouse or utils.get_elysiumanalytics_configs().get("snowflake_warehouse")
            # role = self.role or utils.get_elysiumanalytics_configs().get("snowflake_role")
           
            # schema = self.schema or utils.get_elysiumanalytics_configs().get("snowflake_schema")
            statement = self.statement or utils.get_elysiumanalytics_configs().get("statement")
            timecolumn = self.timecolumn or utils.get_elysiumanalytics_configs().get("timecolumn")
            timefilter = self.timefilter or utils.get_elysiumanalytics_configs().get("timefilter")
            

            # timeout = self.timeout or utils.get_elysiumanalytics_configs().get("timeout")

            tokens_list_retrieved = utils.get_elysiumanalytics_clear_token(session_key)
           
            if len(tokens_list_retrieved) == 0:
                self.write_error("Please configure the addon with proper configurations")
            else:
                snowflake_refresh_token = tokens_list_retrieved[0]
                client_id = tokens_list_retrieved[1]
                client_secret = tokens_list_retrieved[2]
                
                snowflake_instance = utils.get_elysiumanalytics_configs().get("snowflake_instance")
                
              
                
                if snowflake_instance == None:
                    self.write_error("Please configure the addon with proper Data lake Insance")
                else:                   
              
                    snowflake_instance = snowflake_instance+'.snowflakecomputing.com'
                    
                    cust_options = utils.get_elysiumanalytics_configs().get("cust_options")
                    cust_id = utils.get_elysiumanalytics_configs().get("cust_id")

                    if cust_options == 'Customer':
                        
                        role = "PUBLIC"
                        warehouse = cust_id+'_EA_QUERY_WH'
                        database = cust_id+'_ELYSIUM_DB'
                        schema = "ANALYTICS"
                        
                    else:
                       
                        # database = self.database or utils.get_elysiumanalytics_configs().get("snowflake_database")
                        role = "DEMO_ELYSIUM_ANALYST"
                        warehouse = "DEMO_EA_QUERY_WH"
                        database = "DEMO_ELYSIUM_DB"
                        schema = "ANALYTICS"
                        # database = "TENANT2"
                        # schema = "ENRICHEDNEW"
                        
                    if  timecolumn != None:
                        timecolumn  = timecolumn.lower()
                    else:
                        pass
                        
                    if timefilter != None:   
                        timefilter  =timefilter.lower()
                    else:
                        pass
                        
                    
                    
                    
                    if ((timecolumn == None  or timecolumn == 'event_time' ) and (timefilter == None or timefilter == 'true') and (earliest_time_epoch != 0.0 and latest_time_epoch != 0.0 )):
                        
                        extracted_statement = com.query_extraction(statement,earliest_time_epoch,latest_time_epoch)
                    elif ((timecolumn != None and timecolumn != 'event_time') and (timefilter == None or timefilter == 'true') and (earliest_time_epoch != 0.0 and latest_time_epoch != 0.0 )):
                        
                        extracted_statement = com.query_extraction_timecolumn(statement,earliest_time_epoch,latest_time_epoch,timecolumn)
                    elif ((timecolumn == None  or timecolumn == 'event_time' ) and (timefilter == 'false') or (timecolumn != None and timecolumn != 'event_time') or (earliest_time_epoch == 0.0 and latest_time_epoch == 0.0 )):
                        
                        extracted_statement = com.query_extraction_without_timefilter(statement)
                    
                    else:
                        pass
                        
                        
                    

                    payload = {
                                "timeout": 5000,  
                                "role": role,
                                "warehouse" : warehouse,
                                "database": database,
                                "schema": schema,    
                                "statement" : extracted_statement,
                                "parameters": {"TIMESTAMP_NTZ_OUTPUT_FORMAT": "YYYY-MM-DD HH:MM:SS"}
                                # "parameters": {"DATE_OUTPUT_FORMAT": "YYYY/MM/DD"  }
                                }
                                
                    service = client.connect(token=session_key, autologin=True)
                    storage_passwords = service.storage_passwords                      
                    storage_names = []                    
                    for storage_password in storage_passwords.list():
                        storage_names.append(storage_password.name)
                        
                    name = self._metadata.searchinfo.username
                    _LOGGER.info(name)
                    check_name = ":"+name+":"
                        
                    if check_name in storage_names:
                        
                        oauth_response = com.get_clear_token(splunkd_uri,name,session_key)
                      
                    else:
                        oauth_response = com.oauth_key_gen(name,splunkd_uri,session_key,client_id,client_secret,snowflake_refresh_token,snowflake_instance)
                    
                   
                    response = com.elysiumanalytics_api(
                                 "post", oauth_response,const.CLUSTER_ENDPOINT, session_key, data=payload
                                )
                    
                 
                    key_list_1 = []
                    for key in response:
                        key_list_1.append(key)
                    if response['code'] == '002003':
                        # self.write_error("provided schema Object  does not exist or not authorized")
                        self.write_error(response['message'])
                    elif response['code'] == '390318':
                        
                        response = com.oauth_key_gen_390318("post",name,splunkd_uri,session_key,client_id,client_secret,snowflake_refresh_token,snowflake_instance,data=payload)
                        oauth_response = com.get_clear_token(splunkd_uri,name,session_key)
                        key_list_2 = []
                        
                        for key in response:
                            key_list_2.append(key)
                        
                        if response['code'] == '390186':
                            self.write_error(response['message'])
                            # self.write_error("Role  specified in the connect string is not granted to this user. Contact your local system administrator, or attempt to login with another role, e.g. PUBLIC.")
                        else:
                            final_data = com.partitions_response(response,oauth_response)
                           
                            if 'resultSetMetaData' in key_list_2:
                                response_headers = response['resultSetMetaData']['rowType']
                              
                                schema = []
                                for header in range(0,len(response_headers)):
                                    t2 = response_headers[header]
                                    
                                    header_name = t2['name']
                                    schema.append(header_name)
                                # pulling mechanisma
                                _LOGGER.info("Fetching query execution status.")
                                status = None
                                total_wait_time = 0
                                if total_wait_time <= 5000:
                                    status = response.get("message")
                                    # self.write_warning("Query execution status: {}.".format(status))
                                    if status in ("Cancelled", "Error"):
                                        raise Exception(
                                            "Could not complete the query execution. Status: {}.".format(status)
                                        )
                                    elif status == "Statement executed successfully.":
                                       
                                       
                                       
                                        for d in final_data:
                                            yield dict(zip(schema, d))
                                            
                                        _LOGGER.info("Data parsed successfully.")
                                else:
                                    # Timeout scenario
                                    msg = "Command execution timed out. Last status: {}.".format(status)
                                    
                                    self.write_error(msg)
                            else:
                                self.write_error(response['message'])
                       
                    
                    
                    elif response['code'] == '000904':
                        # t1 = "Invalid Identifier "+"'"+ timecolumn +"'"+ " check your SQL Statement"
                        self.write_error(response['message'])
                        
                    elif response['code'] == '390186':
                        self.write_error(response['message'])
                        # self.write_error("Role  specified in the connect string is not granted to this user. Contact your local system administrator, or attempt to login with another role, e.g. PUBLIC.")
                        
                    else:
                        if 'resultSetMetaData' in key_list_1:
                            if response['resultSetMetaData']['numRows'] == 0:
                               
                                response_headers = response['resultSetMetaData']['rowType']
                                schema = []
                                for header in range(0,len(response_headers)):
                                    t2 = response_headers[header]
                                   
                                    header_name = t2['name']
                                    schema.append(header_name)
                                
                                schema_dictionary = { stu : "" for stu in schema }  
                                yield schema_dictionary
                                
                            else:
                                final_data = com.partitions_response(response,oauth_response)
                              
                                response_headers = response['resultSetMetaData']['rowType']
                                schema = []
                                for header in range(0,len(response_headers)):
                                    t2 = response_headers[header]
                                 
                                    header_name = t2['name']
                                    schema.append(header_name)
                                # pulling mechanisma
                                _LOGGER.info("Fetching query execution status.")
                                status = None
                                total_wait_time = 0
                                if total_wait_time <= 5000:
                                    status = response.get("message")
                                    # self.write_warning("Query execution status: {}.".format(status))
                                    if status in ("Cancelled", "Error"):
                                        raise Exception(
                                            "Could not complete the query execution. Status: {}.".format(status)
                                        )
                                    elif status == "Statement executed successfully.":
                                       
                                        
                                        # Fetch Data
                                        # data = response["data"]
                                        for d in final_data:
                                            yield dict(zip(schema, d))
                                        _LOGGER.info("Data parsed successfully.")
                                else:
                                    # Timeout scenario
                                    msg = "Command execution timed out. Last status: {}.".format(status)
                                   
                                    self.write_error(msg)
                        else:
                            
                            self.write_error(response['message'])
                            
                            
                
            
        except Exception as e:
            _LOGGER.error(e)
            _LOGGER.error(traceback.format_exc())
            self.write_error(str(e))


dispatch(ElysiumanalyticsQueryCommand, sys.argv, sys.stdin, sys.stdout, __name__)

