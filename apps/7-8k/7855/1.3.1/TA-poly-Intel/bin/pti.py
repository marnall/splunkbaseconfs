import sys
import time
from datetime import date, timedelta
import json
#sys.path.append(r"polyswarm_api")
import log
import environment
from polyswarm_api.api import * 
from polyswarm_api import *
from splunklib.searchcommands import Configuration
from splunklib.searchcommands import dispatch
from splunklib.searchcommands import Option
from splunklib.searchcommands import StreamingCommand
from splunklib.searchcommands import validators
#from splunklib.searchcommands import GeneratingCommand
import concurrent.futures
logger = log.get_logger(__file__)
#retainsevents=true


#@Configuration(streaming=True)
@Configuration(distributed=False)
class pticommand(StreamingCommand):
    get_hash_data = Option(
    doc="""
    **Syntax:** hash=<field>
    **Description:** get malware hash data from Polyswarm
    """, validate=validators.Fieldname())

    get_hash_by_ip = Option(
    doc="""
    **Syntax:** ip=<field>
    **Description:** IP field name to lookup in PolySwarm
    """, validate=validators.Fieldname() )

    get_hash_by_domain = Option(
    doc="""
    **Syntax:** domain=<field>
    **Description:** lookup in PolySwarm hashes by domain
    """, validate=validators.Fieldname() )
    
    get_hash_by_ttp = Option(
    doc="""
    **Syntax:** ttp=<field>
    **Description:** lookup in PolySwarm hashes by TTP
    """, validate=validators.Fieldname() )

    get_hash_by_tags = Option(
    doc="""
    **Syntax:** tags=<field>
    **Description:**  lookup in PolySwarm hashes by tags
    """, validate=validators.Fieldname() )

    get_hash_by_malware_family = Option(
    doc="""
    **Syntax:** malware_family=<field>
    **Description:** lookup in PolySwarm hashes by malware family
    """, validate=validators.Fieldname() )
    
    get_iocs_by_hash = Option(
    doc="""
    **Syntax:** url=<field>
    **Description:** get all IOC's for a given hash list
    """, validate=validators.Fieldname() )

    
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.field_name = None
        self.field_type = None
        self.ps_env = None
        self.polyapi = None 
        self.errors = set()
        self.eventkeys=[]
        self.eventvalue=[]
    
    def stream(self,events):
        
        ## Get Argument Type
        avgtype =["get_hash_data","get_hash_by_ip","get_hash_by_domain","get_hash_by_ttp","get_hash_by_tags","get_hash_by_malware_family","get_iocs_by_hash","apitest","accountdetails"]
        for avg_type in avgtype:
            if hasattr(self, avg_type):
                try:
                    self.field_name = getattr(self, avg_type)
                except Exception: # pylint: disable=broad-except
                    pass
                if self.field_name:
                    self.field_type = avg_type
                    break
        if not self.field_name or not self.field_type:
            return
        
        ## Get PolySwarm Environment
        self.ps_env = environment.psEnv(self._metadata.searchinfo.session_key)
        
        ## Get API Key from Store
        try:
            self.ps_env.api_key
            global_api_key=self.ps_env.api_key
        except Exception as error:
            #logger.error('%s',error.message)
            datacheck=[{'_time':time.time(),'apikey':'key errro','name':'Error in getting API KEY'}]
            yield from datacheck
            return
        
        ## Set PolySwarm API Connection
        try:
            community_name='default'
            self.polyapi = PolyswarmAPI(key=global_api_key,community=community_name)
        except Exception as error:
            #logger.error('%s',error.message)
            datacheck=[{'_time':time.time(),'apikey':global_api_key ,'name':'Error in setting up Polyswarm Connection'}]
            yield from datacheck
            return

        ##Get Hash Details
        if self.field_type == "get_hash_data": 
            with concurrent.futures.ThreadPoolExecutor() as executor:
                hashresult = executor.map(self.fn_getdata,events)
            for result in hashresult:
                yield from result
            logger.info('Command PTICOAMMAND  executed successfully')
            return
        ##End of HASH Search
        ##get_IOCs
        if self.field_type == "get_iocs_by_hash":
            with concurrent.futures.ThreadPoolExecutor() as executor:
                iocresult = executor.map(self.fn_get_ioc_by_hash,events)
                for result in iocresult:
                    yield from result
            logger.info('Command PTICOAMMAND  executed successfully')
            return         
        ##  ioc_ip_to_hash
        if self.field_type == "get_hash_by_ip" or self.field_type == "get_hash_by_domain" or self.field_type == "get_hash_by_ttp":
            with concurrent.futures.ThreadPoolExecutor() as executor:
                iocresult = executor.map(self.fn_get_hash_by_ioc,events)
                for result in iocresult:
                    yield from result     
            logger.info('Command PTICOAMMAND  executed successfully')
            return
        ## end of IOC_IP
        ## TAGS and malware family
        if self.field_type == "get_hash_by_tags" or self.field_type == "get_hash_by_malware_family":
            with concurrent.futures.ThreadPoolExecutor() as executor:
                malfamilyresult = executor.map(self.fn_get_data_by_malware,events)
                for result in malfamilyresult:
                    yield from result
                    # 
                    # yield from result
            logger.info('Command PTICOAMMAND  executed successfully')
            return
        ## end of TAGS and malware family 
        logger.info('Command PTI COAMMAND  executed successfully')
        return
    
## HASH FUNCTION 
    def fn_getdata(self,current_hash): # get api data for each hash
        results_list = []
        try:
            hash_md5= None
            hash_sha256= None
            hash_polyscore= None
            hash_polyunite = None
            hash_extended_type= None
            hash_permalink= None
            for result in self.polyapi.search(current_hash[self.field_name]): # Use regular 'for' loop
                if result.failed:
                    hash_md5="HASH NOT FOUND"
                    hash_sha256="HASH NOTFOUND"
                else:
                    if not result.assertions:
                        hash_md5="HASH FOUND BUT NOT SCANNED YET"
                        hash_sha256="HASH FOUND BUT NOT SCANNED YET"
                    else:
                        try:
                            pmal = result.metadata.polyunite["malware_family"]
                        except KeyError:
                            pmal = "None"
                        except Exception as error:
                            pmal = "None"
                        hash_md5= result.md5
                        hash_sha256= result.sha256
                        hash_polyscore= result.polyscore
                        hash_polyunite = pmal
                        hash_extended_type= result.extended_type
                        hash_permalink= result.permalink
        except exceptions.NoResultsException:
            hash_md5="HASH NOT FOUND"
            hash_sha256="HASH NOT FOUND"
        except exceptions.RequestException:
            hash_md5="PolySwarm API or connection error. Setup the APP"
            hash_sha256="PolySwarm API or connection error. Setup the APP"
        except exceptions.InvalidValueException:
            hash_md5="Invalid HASH Found"
            hash_sha256="Invalid HASH Found"
        except Exception as error:
            hash_md5=type(error).__name__
            hash_sha256= error    
        results_list.append({'hash_md5':hash_md5,'hash_sha256':hash_sha256,'MalwareScore_polyscore':hash_polyscore,'MalwareFamilyName_polyunite':hash_polyunite,'file_extended_type':hash_extended_type,'full_scan_result_link':hash_permalink})
        return results_list

              ## END of Stream
   
#### hash to IOC FUNCTION 
    def fn_get_ioc_by_hash(self,current_hash): 
        result_list=[]
        result_sha256 = current_hash[self.field_name]
        try:
            ioc_results = self.polyapi.iocs_by_hash('sha256',current_hash[self.field_name], beta=True)
        except exceptions.NoResultsException:
            result_list.append({'ioc_type': "NO IOC FOUND", 'ioc': 'N/A' ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'Error', 'polyscore_malwarescore': 'Error'})
            return result_list
        except exceptions.RequestException:
            result_list.append({'ioc_type': "REQUEST ERROR FOUND", 'ioc': 'N/A' ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'Error', 'polyscore_malwarescore': 'Error'})
            return result_list
        except exceptions.InvalidValueException:
            result_list.append({'ioc_type': "INVALID HASH VALUE FOUND", 'ioc': 'N/A' ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'Error', 'polyscore_malwarescore': 'Error'})
            return result_list
        except Exception as error:
            result_list.append({'ioc_type': type(error).__name__, 'ioc': error ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'Error', 'polyscore_malwarescore': 'Error'})
            return result_list
        try:
            jsonData = ioc_results.json
            imphash = jsonData["iocs"]["imphash"]
            malware_family = jsonData["malware_family"]
            polyscore = jsonData["polyscore"]
            #print(f'hash_ioc_impash: : {imphash}, Malware Family: {malware_family}, Polyscore: {polyscore}')
            try:
                for domain in jsonData["iocs"]["domains"]:
                    #event['hash_ioc_domain'] = domain["domain"]
                    #event['hash_ioc_confidence']= domain["confidence"]
                    #yield event
                    result_list.append({'ioc_type': 'domain', 'ioc': domain["domain"],'ioc_confidence': domain["confidence"],'hash_sha256': result_sha256,'ioc_impash':imphash, 'malwarefamily': malware_family, 'polyscore_malwarescore': polyscore})
            except Exception as error:
                result_list.append({'ioc_type': type(error).__name__, 'ioc': error ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'Domain', 'polyscore_malwarescore': 'Error'})
                pass
            
            try:
                for url in jsonData["iocs"]["urls"]:
                #event['hash_ioc_url'] = url["url"]
                #event['hash_ioc_confidence']= url["confidence"]
                #yield event
                    result_list.append({'ioc_type': 'url', 'ioc': url["url"],'ioc_confidence': url["confidence"],'hash_sha256': result_sha256,'ioc_impash':imphash, 'malwarefamily': malware_family, 'polyscore_malwarescore': polyscore})
            except Exception as error:
                result_list.append({'ioc_type': type(error).__name__, 'ioc': error ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'url', 'polyscore_malwarescore': 'Error'})
                pass
    
            try:
                for iip in jsonData["iocs"]["ips"]:
                    #event['hash_ioc_ip'] = iip["ip"]
                    #event['hash_ioc_confidence']= iip["confidence"]
                    #yield event
                    result_list.append({'ioc_type': 'ip', 'ioc': iip["ip"],'ioc_confidence': iip["confidence"],'hash_sha256': result_sha256,'ioc_impash':imphash, 'malwarefamily': malware_family, 'polyscore_malwarescore': polyscore})
                    
            except Exception as error:
                result_list.append({'ioc_type': type(error).__name__, 'ioc': error ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'IP', 'polyscore_malwarescore': 'Error'})
                pass
            try:
                for ttp in jsonData["iocs"]["ttps"]:
                    #event['hash_ioc_ttp'] = ttp
                    #event['hash_ioc_confidence']= 'N/A'
                    #yield event
                    result_list.append({'ioc_type': 'ttp', 'ioc': ttp,'ioc_confidence': 'N/A','hash_sha256': result_sha256,'ioc_impash':imphash, 'malwarefamily': malware_family, 'polyscore_malwarescore': polyscore})
            except Exception as error:
                result_list.append({'ioc_type': type(error).__name__, 'ioc': error ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'ttp', 'polyscore_malwarescore': 'Error'})
                pass
        except Exception as error:
            #event['hash_ioc_ip'] = type(error).__name__
            #event['hash_ioc_url'] = 'Error in assigning iocs data '
            result_list.append({'ioc_type': type(error).__name__, 'ioc': error ,'ioc_confidence': 'Error','hash_sha256': result_sha256,'ioc_impash':'Error', 'malwarefamily': 'jsondata assigning', 'polyscore_malwarescore': 'Error'})
            return result_list
        return result_list

### IOC to HASH functions
    def fn_get_hash_by_ioc(self,eventlist):
        results_list = []
        #search_by_ioc(self, ip=None, domain=None, ttp=None, imphash=None):
        try:
            if self.field_type == "get_hash_by_ip":
                results = self.polyapi.search_by_ioc(ip=eventlist[self.field_name])
            elif self.field_type == "get_hash_by_domain":
                results = self.polyapi.search_by_ioc(domain=eventlist[self.field_name])
            elif self.field_type == "get_hash_by_ttp":
                results = self.polyapi.search_by_ioc(ttp=eventlist[self.field_name])
            try:
            #search_by_ioc(self, ip=None, domain=None, ttp=None, imphash=None):
            #results = polyapi.search_by_ioc(ip='4.175.87.197')
                i=0
                for result in results:
                    i+=1
                    if i>100:
                        break
                    results_list.append({'ioc_type': 'hash', 'ioc': result.json,'iocsource_type':self.field_type ,'ioc_value': eventlist[self.field_name]})
            except Exception as error:
                results_list.append({'ioc_type': type(error).__name__, 'ioc': error,'iocsource_type': self.field_type,'ioc_value': eventlist[self.field_name]})
                pass
        except Exception as error:
            results_list.append({'ioc_type': type(error).__name__, 'ioc': error,'iocsource_type': self.field_type,'ioc_value': eventlist[self.field_name]})
            return results_list
            pass
        return results_list  

    def fn_get_data_by_malware(self, eventlist):
        list_malware_family=eventlist[self.field_name]
        list_tags=eventlist[self.field_name]
        list_malware_family = list_malware_family.replace(" ", "")
        list_tags = list_tags.replace(" ", "")
        list_limitresult="500"
        list_limitresult=int(list_limitresult)
        starttime_malware_family="7" 
        pscore = "0.50"
        dataload=[]
        
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
        if self.field_type == "get_hash_by_malware_family":
            split_string = list_malware_family.split(',')
            i=0
            for mname in split_string:
                i+=1
                if i>1:
                    qp += ' OR '
                qp += 'polyunite.malware_family:'+mname+' OR families:'+mname+' OR scan.\*.\*.metadata.malware_family:*'+mname+'* OR triage_sandbox_v0.analysis.family:'+mname+' OR cape_sandbox_v2.malware_family:'+mname
                #print("in for loop for list_malware_family:",mname)
            qp += ')'  
        elif self.field_type == "get_hash_by_tags":
            split_string = list_tags.split(',')
            i=0
            for mtags in split_string:
                i+=1
                if i>1:
                    qp += ' OR '
                qp += 'tags:"'+mtags+'"'
            qp += ')'    

        # FILED TO BE ADDED
        include_fields=["tags","polyunite","hash","scan.first_seen","scan.last_seen","scan.mimetype","scan.latest_scan.polyscore","triage_sandbox_v0.analysis","triage_sandbox_v0.malware_family","triage_sandbox_v0.targets.score","cape_sandbox_v2.malfamily_tag","cape_sandbox_v2.malscore","cape_sandbox_v2.malware_family","exiftool.filetype","exiftool.mimetype","exiftool.type"]
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
            if not parent_key.startswith("artifact"):            
                self.eventkeys.append(parent_key)
                self.eventvalue.append(str(data))
        return

dispatch(pticommand, sys.argv, sys.stdin, sys.stdout, __name__)


