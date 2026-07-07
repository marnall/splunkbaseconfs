#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os,sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import galib
from defapi import get_aadToken

APPNAME = "defender_advanced_hunting_query"
COMMANDNAME = 'defkqls'
CREDUSER = 'defenderapp_user1'
CREDREALM = 'defender_realm'
logger = galib.setup_logging(APPNAME)

@Configuration()
class defkqls(StreamingCommand):
    api = Option(doc=''' API kinds whether "queries" or "hunting" ''',require=True,validate=validators.Set('queries','hunting'))
    primary_field = Option(doc='''a primary_field field which the value matched to that of defender field in order to append the defender result. you must use this field in where/filter KQL query as `field` ''',require=True,validate=validators.Fieldname())
    kql = Option(doc=''' KQL query to run ''',require=True)

    def prepare(self):
        self.configuration.required_fields = [self.api,self.primary_field,self.kql]

    def stream(self, events):
        try:
            try:
                sessionkey = self.metadata.searchinfo.session_key
                if sessionkey is None:
                    raise Exception("[Session Error] Did not receive a session key from splunkd.")
                cred_strings = galib.get_credentials(sessionkey,APPNAME,CREDUSER,CREDREALM)
            except Exception as e:
                raise Exception(f"[Credential Error] Could not retrieve credential from Secret Storage by {str(e)}")

            tenantId = cred_strings.split("&")[0]
            appId = cred_strings.split("&")[1]
            appSecret = cred_strings.split("&")[2]

            if self.api == "queries":
                from defapi import advancedqueries_run as run_query,parse_kql_condition,adjust_kql
            elif self.api == "hunting":
                from defapi import advancedhunting_run as run_query,parse_kql_condition,adjust_kql
            else:
                raise Exception("[Option Error] Please specify 'queries' or 'hunting' for selecting which Defender 365 Advanced Hunting API, caused.")
                return 0

            if not self.primary_field:
                raise Exception("[Option Error] Please specify 'fieldname' in your SPL, the field value ties the defender event by equals. you should use '==' in where/filter query of your KQL.")

            # get aadToken 
            try:
                aadToken = get_aadToken(tenantId,appId,appSecret,self.api)
            except Exception as e:
                raise Exception(f"[Token Error] Could not retrieve aadToken from the Azure AD creds by {str(e)}")
                return 0

        except Exception as e:
            logger.exception(f"Unexpected Error: {str(e)}")
            raise Exception(f"[Unexpected Error]: Please see the error detail in app log or search log. {str(e)}")
            return 1    

        list_events = list(events)
        if len(list_events) == 0:
            raise Exception("[Event Error] no event to pass defkqls command, you may had better use defkqlg instead.")
        
        # process events for adjusting kql fields
        splunk_fields = parse_kql_condition(self.kql,logger)
        logger.info(f"extracted splunk_fields: {splunk_fields}")
        if not self.primary_field in splunk_fields:
            raise Exception("[Parse Error] your 'primary_field' was not appered in your KQL. Please check your KQL again.")
        
        eventmaps = []
        for event in list_events:
            eventdict = {}
            try:
                for splunkfield in splunk_fields:
                    if not splunkfield in event:
                        raise Exception("[Event Error] No matching fields between event's fields and your kql.")
                    eventdict[splunkfield] = { "eventvalue": event[splunkfield], "defenderfield": None }
                    if self.primary_field == splunkfield:
                        eventdict[splunkfield]["primary"] = True
                eventmaps.append(eventdict)
            except Exception as e:
                logger.exception(str(e))                        

        # constructor for final_kql to throw API
        final_kql, eventmaps = adjust_kql(self.kql,eventmaps,logger)
        logger.warning(f"final_kql: {final_kql}")

        # run kql query 
        try:
            results = run_query(aadToken,final_kql)
        except Exception as e:
            raise Exception(f"[DefenderAPIQuery Error] Could not retrieve a valid kql results by {str(e)}")
            return 0

        if len(results) == 0:
            raise Exception("No results from Defender API. Please check your final KQL.")
        logger.info(f"defender result count: {len(results)}")

        # JOIN events and results for splunk output
        if isinstance(results,list): # multi row results 
            c = 0
            for event in list_events:
                for result in results:
                    flag_primary_field = False    
                    counter = 0
                    additional_message = ""
                    for splunkfield,dict_value in eventmaps[c].items():
                        try:
                            # Check whether matching between Splunk field value & Defender Response 
                            if event[splunkfield] == result[dict_value["defenderfield"]] or event[splunkfield].lower() == result[dict_value["defenderfield"]].lower(): 
                                if splunkfield == self.primary_field:
                                    flag_primary_field = True
                                counter += 1
                        except KeyError:
                            logger.warning(f"your `{splunkfield}` field in condition was not projected to output fields. Please add the defender field to project stanza to out its field value.")
                            # if you don't set fields by 'project' stanza for your splunk event fields, this warning will be appeared. 
                        
                        if dict_value["defenderfield"] == "Timestamp":
                            if not "(Timerange satisfied)" in additional_message:
                                additional_message += " (Timerange satisfied)"                        
                    if counter == len(eventmaps[c].keys()):     # All KQL condition field values matched.
                        message = f"full matched !({counter})"
                    elif flag_primary_field:
                        message = f"primary_field `{self.primary_field}` matched.({counter})"
                    else:
                        message = "not found." 

                    if "matched" in message:
                        message += additional_message
                        try: event["Defender_app_error"].append(message)
                        except KeyError: event["Defender_app_error"] = [ message ]                         
                        for key,value in result.items():
                            try: event["Defender_%s"%key].append(value)
                            except KeyError: event["Defender_%s"%key] = [ value ]

                c += 1
                if not "Defender_app_error" in event: 
                    event["Defender_app_error"] = "not found."
                
                yield event


dispatch(defkqls, sys.argv, sys.stdin, sys.stdout, __name__)