#!/usr/bin/env python3
import sys,os
import time
from datetime import date, timedelta
#sys.path.append(r"polyswarmsdk")
from polyswarm_api.api import PolyswarmAPI
from polyswarm_api import exceptions
from polyswarm_api import *

from splunklib.modularinput import *
import json
import log
import environment


logger = log.get_logger(__file__)

class pdata(Script):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_name = None
        self.field_type = None
        self.ps_env = None
        self.polyapi = None
        self.errors = set()
        self.eventkeys= []
        self.eventvalue=[]

    def get_scheme(self):
        scheme = Scheme("Get PolySwarm Malware Intelligence") 
        scheme.use_external_validation = False
        scheme.use_single_instance = False
        scheme.description = "Use Malware Family or your Industry/Sector Tags to collect Latest Malware Intelligence. You can schedule a auto update using more settings"
        
        starttime_malware_family = Argument("starttime_malware_family")
        starttime_malware_family.title = "Enter the number of days for your query (default: 1 day / 24 hours):"
        starttime_malware_family.data_type = Argument.data_type_number
        starttime_malware_family.description = "Specify the start time for malware intelligence retrieval. The end time will default to the today 00:00 hrs."
        starttime_malware_family.required_on_create = False
        starttime_malware_family.required_on_edit = False
        scheme.add_argument(starttime_malware_family)
        
        list_malware_family = Argument("list_malware_family")
        list_malware_family.title = "List up to three Malware Families (e.g. redline,godfather,ryuk):"
        list_malware_family.data_type = Argument.data_type_string
        list_malware_family.description = "To see all available malware families, use the command '| ptilistmalwarefamily' in the search bar."
        list_malware_family.required_on_create = False
        list_malware_family.required_on_edit = False
        scheme.add_argument(list_malware_family)

        list_tags = Argument("list_tags")
        list_tags.title = "List up to three Malware Intelligence Tags (e.g. sector:healthcare,sector:government,ransomware):"
        list_tags.data_type = Argument.data_type_string
        list_tags.description = "Note: If No Malware family and NO Tags are selected, the input  will default to retrieving top active malware intelligence.To see all available tags, use the command '| ptilisttags' in the search bar."
        list_tags.required_on_create = False
        list_tags.required_on_edit = False
        scheme.add_argument(list_tags)
        
        list_pscore = Argument("list_pscore")
        list_pscore.title = "Enter the minimum PolyScore (malware score) [0 (benign) - 1 (malicious)] (default value0.75):"
        list_pscore.data_type = Argument.data_type_string
        list_pscore.description = "This will retrieve malware samples with a PolyScore above your specified value. The default value is 0.75"
        list_pscore.required_on_create = False
        list_pscore.required_on_edit = False
        scheme.add_argument(list_pscore)
        
        list_limitresult = Argument("list_limitresult")
        list_limitresult.title = "Limit the number of hashes/results to download per execution/job (default value  100):"
        list_limitresult.data_type = Argument.data_type_number
        list_limitresult.description = "Specify the maximum number of malware samples to retrieve per execution/job. The  default is 100"
        list_limitresult.required_on_create = False
        list_limitresult.required_on_edit = False
        scheme.add_argument(list_limitresult)

        return scheme

    def process_data(self,data, parent_key=""):
        """
        Recursively processes the JSON data to extract keys and values.
        Args:
        data:  A dictionary or a value.
        parent_key: The key of the parent dictionary (used for nested structures).
        """
        if isinstance(data, dict):
            for key, value in data.items():
                new_key = f"{parent_key}.{key}" if parent_key else key
                self.process_data(value,new_key)  # Recursive call for nested structures
        elif isinstance(data, list):
            for i, item in enumerate(data):
                new_key = f"{parent_key}[{i}]"  # Represent list indices in keys
                self.process_data(item,new_key)
        else:
            self.eventkeys.append(parent_key)
            self.eventvalue.append(str(data))
        return

    def apicall(self,global_api_key,list_malware_family,list_tags,list_limitresult,starttime_malware_family,pscore):
        dataload=[]
        list_limitresult=int(list_limitresult)
        try:
            community_name="default"
            self.polyapi = PolyswarmAPI(key=global_api_key,community=community_name)
        except Exception as error:
            logger.error('%s',error)
            dataload.append({'API Error': error,'error': 'apicall - Setting PolySwarm Error', 'APIKEY': global_api_key,'Community':community_name})
            return dataload

        #time parameter
        # setting the datetime object containing current date query time
        today=date.today()
        # dd/mm/YY H:M:S T %H:%M:%S
        endd = today.strftime("%Y-%m-%d")
        start_date = today - timedelta(days=int(starttime_malware_family))
        startd = start_date.strftime("%Y-%m-%d")
        #Create the query
        qp = 'artifact.created:['+startd+'T00:00:00 TO '+endd+'T00:00:00]'
        qp += ' AND scan.latest_scan.polyscore:>='+pscore+' AND ('
       

       #ADD THE MALWARE FAMILY
        if list_malware_family:
            split_string = list_malware_family.split(',')
            i=0
            for mname in split_string:
                i+=1
                if i>3:
                    break
                if i>1:
                    qp += ' OR '
                qp += 'polyunite.malware_family:'+mname+' OR families:'+mname+' OR scan.\*.\*.metadata.malware_family:*'+mname+'* OR triage_sandbox_v0.analysis.family:'+mname+' OR cape_sandbox_v2.malware_family:'+mname
                print("in for loop for list_malware_family:",mname)
        #Add Tags
        if list_tags:
            if list_malware_family:
                qp += ' OR '
            split_string = list_tags.split(',')
            i=0
            for mtags in split_string:
                i+=1
                if i>3:
                    break
                if i>1:
                    qp += ' OR '
                qp += 'tags:"'+mtags+'"'
            
        qp += ')'    

        # FILED TO BE ADDED
        include_fields=["hash","exiftool.originalfilename","exiftool.originalfilename2","exiftool.rawfilename","exiftool.filetype","exiftool.mimetype","exiftool.type","scan.first_seen","scan.last_seen","scan.detections","scan.mimetype","scan.latest_scan.polyscore","polyunite","artifact.first_seen","triage_sandbox_v0.analysis","triage_sandbox_v0.malware_family","triage_sandbox_v0.targets.score","triage_sandbox_v0.extracted.config","triage_sandbox_v0.targets.iocs","triage_sandbox_v0.ttp","triage_sandbox_v0.extracted_c2_ips","cape_sandbox_v2.malfamily_tag","cape_sandbox_v2.malscore","cape_sandbox_v2.malware_family","cape_sandbox_v2.ttp","cape_sandbox_v2.extracted","tags"]
        i=0       
       
        #RUN THE API CALL
        try:
            results = self.polyapi.search_by_metadata(qp,include=include_fields)
            try:
                for result in results:
                    i+=1
                    if  i >list_limitresult:
                        break
                    try:
                        data = result._content
                        self.eventkeys=[]
                        self.eventvalue=[]
                        self.process_data(data)
                        dataload.append(dict(zip(self.eventkeys,self.eventvalue)))
                    except Exception as error:
                        #logger.error('%s',error)
                        dataload.append({'Result': type(error).__name__,'PolySwarm Error':'Error in Result (keys/value pair)','query':qp})
                return dataload
            except Exception as error:
                #logger.error('%s',error)
                dataload.append({'Result': type(error).__name__,'PolySwarm Error':'NO Results','query':qp})
                return dataload
        except exceptions.NoResultsException as error:
            #logger.error('%s',error)
            dataload.append({'Result':'NO Result Found','PolySwarm Error':'Query Got No Result','error':type(error).__name__,'query':qp})
            return dataload
        except Exception as error:
            #logger.error('%s',error)
            dataload.append({'Query Error':type(error).__name__,'PolySwarm Error':'Error in Running Query','query':qp,'error':error})
            return dataload
        return dataload

    def validate_input(self, validation_definition):
        # Validates input.
        pass

    def stream_events(self, inputs, ew):
        dataerror=[]
        # Get API Key from Store
        #splunkd_uri = self._input_definition.metadata["server_uri"]
        session_key = self._input_definition.metadata["session_key"]
        #skey=session_key
        try:
            community_name="default"
            self.ps_env = environment.psEnv(session_key)
            self.ps_env.api_key
            global_api_key=self.ps_env.api_key
            #get the parameter from input config
        except Exception as error:
            #logger.error('%s',error)
            dataerror.append({'API Error':type(error).__name__,'error': 'Getting API Key from Store', 'APIKEY': global_api_key,'Community':community_name})
            for drr3 in dataerror:
                event = Event()
                event.stanza = input_name
                event.data = json.dumps(drr3)
                ew.write_event(event)
            return

        for input_name,input_item in inputs.inputs.items():
            try: 
                if "list_malware_family" in input_item:
                    list_malware_family = input_item["list_malware_family"]
                    if list_malware_family == " " or list_malware_family == "" or not list_malware_family:
                        list_malware_family = ""
                    else:                    
                        list_malware_family = list_malware_family.replace(" ", "")
                else:
                    list_malware_family = ""
        
                if "list_tags" in input_item:
                    list_tags = input_item["list_tags"]
                    if list_tags == " " or list_tags == "" or not list_tags:
                        list_tags = ""
                    else:    
                        list_tags = list_tags.replace(" ", "")
                else:    
                    list_tags = ""
            

                if  list_malware_family == "" and list_tags == "":
                    list_tags = 'feed:premium' 
                
                if "list_limitresult" in input_item:    
                    list_limitresult = input_item["list_limitresult"]
                else:    
                    list_limitresult = 100
                
                if "starttime_malware_family" in input_item:
                    starttime_malware_family = input_item["starttime_malware_family"]    
                else:    
                    starttime_malware_family = 1
        
                if "list_pscore" in input_item:    
                    list_pscore = input_item["list_pscore"]
                else:    
                    list_pscore = "0.75"        
            except Exception as error:
                #if hasattr(error, 'message'):
                #    current_error=error.message
                #else:
                #    current_error=error
                #logger.error('%s',error)
                dataerror.append({'API Error':type(error).__name__,'error': 'Error in Schema Setup', 'APIKEY': global_api_key})
                for drr3 in dataerror:
                    event = Event()
                    event.stanza = input_name
                    event.data = json.dumps(drr3)
                    ew.write_event(event)
                return
            try:
                results=self.apicall(global_api_key,list_malware_family,list_tags,list_limitresult,starttime_malware_family,list_pscore)
            except Exception as error:
                #logger.error('%s',error)
                dataerror.append({'API Error':type(error).__name__,'error': 'Error in in API Search query and result call', 'APIKEY': global_api_key})
                for drr3 in dataerror:
                    event = Event()
                    event.stanza = input_name
                    event.data = json.dumps(drr3)
                    ew.write_event(event)
                    #get results to events 
                return
            try:
                for r in results:
                    event = Event()
                    event.stanza = input_name
                    #event.data = r
                    event.time = time.time()
                    #event.data = json.dumps(r(sort_keys=True,separators=(',',':'))
                    event.data=json.dumps(r)
                    ew.write_event(event)
            except Exception as error:
                logger.error('%s',error)
                dataerror.append({'Event Write Error':type(error).__name__,'error': 'PolySwarm Event Write Error','Community':community_name})
                for drr1 in dataerror:
                    event = Event()
                    event.stanza = input_name
                    event.data = json.dumps(drr1)
                    ew.write_event(event)
                return
        pass
if __name__ == "__main__":
    sys.exit(pdata().run(sys.argv))