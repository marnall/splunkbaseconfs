#==============================================================================#
# Continuous Automation and Visibility Engine                    Set Solutions #
# REST Enrichments                                 Engineering and Development #
#==============================================================================#


#------------------------------------------------------------------------------#
# Include Libraries and Configuration                                          #
#------------------------------------------------------------------------------#
#
#-- Library Imports and Global Variables -------------------------------------
import os,sys,time,json,re
from cavecommon import conf,spkv
from splunklib.searchcommands import dispatch,ReportingCommand,Configuration,Option,validators
import requests
#-----------------------------------------------------------------------------
#
#-- Endpoint Specifications --------------------------------------------------
basefile = os.path.dirname(os.path.realpath(__file__))+"/enrichrest.json"
try: dictvals = json.loads("".join([x.strip() for x in open(basefile).read().split("\n") if x.strip()[0:1] != "#" and len(x.strip()) > 0]))
except: raise Exception("Failed to load endpoint specifications")
if not isinstance(dictvals,dict): Exception("Failed to parse endpoint specifications")
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# OpenDNS Detective                                                            #
#------------------------------------------------------------------------------#
#
#-- OpenDNS API Function -----------------------------------------------------
def opendns_apif(self,config,method,target):
    import time
    restgets = list()
    reststat = list()
    gathered = {self.source+"_restname":[],self.source+"_restcode":[]}
    #
    # First perform the quick method if relevant to do so with method
    if method in ["quick","smart","extended"]:
        restdata = opendns_apifcall(self,config,dict((dictvals[self.source]["restend"]["dsc"]).items()+({"target":target}).items()))
        gathered[self.source+"_restname"].append("dsc")
        if isinstance(restdata,dict) and len(restdata) > 0:
            gathered[self.source+"_restcode"].append(restdata[self.source+"_restcode"] if self.source+"_restcode" in restdata else "ERR:C4")
            for field in dictvals[self.source]["restend"]["dsc"]["fields"]:
                srcfield = field.split(":")[0] if ":" in field else field
                dstfield = field.split(":")[1] if ":" in field else field
                if srcfield in restdata and len(str(restdata[srcfield])) > 0: gathered[dstfield] = restdata[srcfield]
            if method == "smart" and "status" in restdata and restdata["status"] < 0: restgets.append("sid")
        else: gathered[self.source+"_restcode"].append("ERR:C1")
    #
    # Gather additional data based on the quick results or if method relevant
    if method == "extended" and "sid" not in restgets: restgets.append("sid")
    if method in ["extended"]: restgets.extend(["cod","rdd"])
    if method in ["extended","whois"]: restgets.append("wid")
    for rest in restgets:
        restdata = opendns_apifcall(self,config,dict((dictvals[self.source]["restend"][rest]).items()+({"target":target}).items()))
        gathered[self.source+"_restname"].append(rest)
        if isinstance(restdata,dict) and len(restdata) > 0:
            gathered[self.source+"_restcode"].append(restdata[self.source+"_restcode"] if self.source+"_restcode" in restdata else "ERR:C4")
            for field in dictvals[self.source]["restend"][rest]["fields"]:
                srcfield = field.split(":")[0] if ":" in field else field
                dstfield = field.split(":")[1] if ":" in field else field
                if srcfield in restdata and len(str(restdata[srcfield])) > 0: gathered[dstfield] = restdata[srcfield]
        else: gathered[self.source+"_restcode"].append("ERR:C1")
    #
    # Return the new dictionary of gathered data from the API
    return gathered
#-----------------------------------------------------------------------------
#
#-- OpenDNS API Call Function ------------------------------------------------
def opendns_apifcall(self,config,restdict):
    import requests,json
    restdata = dict()
    restcode = None
    #
    # Call the endpoint as defined handling errors
    u = config["enrichrest_opendns"]["enrichrest_opendns_baseurl"]+(restdict["endpoint"]%restdict["target"])
    h = {"Authorization":"Bearer "+config["enrichrest_opendns"]["enrichrest_opendns_apikey"]}
    try: response = requests.get(u,headers=h,verify=config["enrichrest_opendns"]["requests_verify"],cert=config["enrichrest_opendns"]["requests_cert"])
    except: restcode = "ERR:C2"
    else:
        if response.status_code == 200:
            try: restdata = json.loads(response.text)
            except: restcode = "ERR:C3"
        if restcode is None: restcode = response.status_code
    #
    # Return the new dictionary of gathered data based on method provided
    if isinstance(restdata,dict) and restdict["target"] in restdata: restdata = restdata[restdict["target"]]
    return dict(restdata.items()+({self.source+"_restcode":restcode}).items())
#-----------------------------------------------------------------------------
#
#-- OpenDNS: Parent Function -------------------------------------------------
def opendns(self,config,record,parent=False):
    #
    # Validate the required configuration is present and makes sense
    if "enrichrest_opendns_baseurl" not in config["enrichrest_opendns"] or config["enrichrest_opendns"]["enrichrest_opendns_baseurl"] in [None,"None"]: record[self.source+"_output"].append("ERROR: Missing or undefined configuration option (enrichrest_opendns_baseurl)")
    elif not re.match(r'^https\:\/\/.+?$',config["enrichrest_opendns"]["enrichrest_opendns_baseurl"]): record[self.source+"_output"].append("ERROR: Invalid value specified for configuration option (enrichrest_opendns_baseurl)")
    elif "enrichrest_opendns_apikey" not in config["enrichrest_opendns"] or config["enrichrest_opendns"]["enrichrest_opendns_apikey"] in [None,"None"]: record[self.source+"_output"].append("ERROR: Missing or undefined configuration option (enrichrest_opendns_apikey)")
    elif len(config["enrichrest_opendns"]["enrichrest_opendns_apikey"]) == 0: record[self.source+"_output"].append("ERROR: Invalid value specified for configuration option (enrichrest_opendns_apikey)")
    #
    # Validate the required options have values which make sense
    if self.target not in record or len(record[self.target]) == 0: record[self.source+"_output"].append("Field specified was not found in the event")
    else:
        try: rdomain = re.search(r'^(https?\:\/\/)?(([\w\d\-]+\.){1,}([\w\d\-]+))',record[self.target].lower(),re.UNICODE)
        except: record[self.source+"_output"].append("Unable to parse the target field")
        else:
            try: tdomain = rdomain.group(2)
            except: record[self.source+"_output"].append("Target field specified is invalid")
    if self.method.lower() in dictvals[self.source]["methods"]: method = self.method.lower()
    else: record[self.source+"_output"].append("Valid methods are: "+(", ".join(dictvals[self.source]["methods"])))
    if not parent and len(record[self.source+"_output"]) > 0: return record
    #
    # Query for any usable data already in the KV Store for caching
    selectkv = spkv(self,conf(self),str(self._metadata.searchinfo.app),"select","cave_dt_opendns_cache",{"query":{"target":tdomain}})
    if selectkv["failed"]: record[self.source+"_output"].append("Failed to query KV Store for caching: "+selectkv["reason"] if not parent else str())
    elif "data" in selectkv and len(selectkv["data"]) > 0:
        kvscache = None
        #
        # Determine if this cache data is usable before proceeding
        for cache in sorted(selectkv["data"],key=lambda k:k["fetched"],reverse=True):
            if method == "quick" and cache["method"] in ["quick","smart","extended"]: kvscache = cache
            elif method == "smart" and cache["method"] in ["smart","extended"]: kvscache = cache
            elif method == "extended" and cache["method"] == "extended": kvscache = cache
            elif method == "extended" and cache["method"] == "smart" and cache["stance"] == "bad": kvscache = cache
            elif method == "whois" and cache["method"] in ["extended","whois"]: kvscache = cache
            if kvscache is not None: break
        if isinstance(kvscache,dict): record[self.source+"_output"].append("Cache data was found for target" if not parent else str())
        else: record[self.source+"_output"].append("No usable cache data was found for target" if not parent else str())
    else: record[self.source+"_output"].append("No cache data found for target" if not parent else str())
    #
    # If recursive call return only the data from the KV Store for caching
    if isinstance(parent,bool) and parent: return kvscache if "kvscache" in vars() and kvscache is not None and isinstance(kvscache,dict) else False
    elif not isinstance(parent,bool):
        record[self.source+"_output"].append("The parent parameter must be boolean")
        return record
    #
    # Reach out to API if there is no data in the KV Store for caching
    if "kvscache" not in vars() or not isinstance(kvscache,dict):
        apifdict = opendns_apif(self,config,method,tdomain)
        if len(apifdict[self.source+"_restcode"]) == 0: record[self.source+"_output"].append("Failed to query OpenDNS API")
        elif len([scode for scode in apifdict[self.source+"_restcode"] if scode not in [200,404]]) > 0: record[self.source+"_output"].append("Errors when querying OpenDNS API - "+str(apifdict[self.source+"_restcode"]))
        elif 200 in apifdict[self.source+"_restcode"]:
            record[self.source+"_output"].append("Data was found via data provider API")
            #
            # Prepare and store the record in the KV store for caching
            apifdict.update({"fetched":int(time.time()),"method":method,"target":tdomain,"stance":None})
            if method in ["quick","smart","extended","whois"]:
                if "status" not in apifdict or method == "whois": apifdict["stance"] = "neutral"
                else: apifdict["stance"] = "neutral" if int(apifdict["status"]) == 0 else ("bad" if int(apifdict["status"]) < 0 else "good")
            insert = spkv(self,conf(self),str(self._metadata.searchinfo.app),"insert","cave_dt_opendns_cache",{"data":apifdict})
            if insert["failed"]: record[self.source+"_output"].append("Failed to insert record into KV Store: "+insert["reason"])
            else: record[self.source+"_output"].append("Cache data was stored for target")
        #
        # Indicate when there were no results found via the API
        elif 404 in apifdict[self.source+"_restcode"]:
            record[self.source+"_output"].append("No data was found via data provider API")
            insert = spkv(self,conf(self),str(self._metadata.searchinfo.app),"insert","cave_dt_opendns_cache",{"data":{"fetched":int(time.time()),"method":method,"target":tdomain,"stance":"neutral"}})
            if insert["failed"]: record[self.source+"_output"].append("Failed to insert record into KV Store: "+insert["reason"])
            else: record[self.source+"_output"].append("Cache entry created for target")
    #
    # Refetch cache if there was data returned by the API and stored
    if ("insert" in vars() and not insert["failed"]) and ("kvscache" not in vars() or not isinstance(kvscache,dict)):
        kvscache = opendns(self,config,dict(record.items()),parent=True)
        if kvscache is None or not isinstance(kvscache,dict): record[self.source+"_output"].append("Refetch failed for target")
        else: record[self.source+"_output"].append("Refetch succeeded for target")
    #
    # Integrate OpenDNS data from either the cache or from refetch
    if "kvscache" in vars() and isinstance(kvscache,dict):
        for rest in dictvals[self.source]["restend"]:
            for field in dictvals[self.source]["restend"][rest]["fields"]:
                fname = field.split(":")[1] if ":" in field else field
                if fname in kvscache: fdata = kvscache[fname]
                else: continue #fdata = None
                record[dictvals[self.source]["prefix"]+"_"+rest+"_"+fname] = fdata
        for field in ["fetched","method","target","stance"]: record[field] = kvscache[field] if field in kvscache else None
    #
    # Return the requested data to the upstream calling routine
    record[self.source+"_output"].extend(apifdict[self.source+"_output"] if "apifdict" in vars() and isinstance(apifdict,dict) and self.source+"_output" in apifdict else list())
    record.update({self.source+"_restname":apifdict[self.source+"_restname"] if "apifdict" in vars() and isinstance(apifdict,dict) and self.source+"_restname" in apifdict else None})
    record.update({self.source+"_restcode":apifdict[self.source+"_restcode"] if "apifdict" in vars() and isinstance(apifdict,dict) and self.source+"_restcode" in apifdict else None})
    return record
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# VirusTotal Detective                                                         #
#------------------------------------------------------------------------------#
#
#-- VirusTotal API Function --------------------------------------------------
def virustotal_apif(self,config,method,target):
    import time,re,json
    restgets = list()
    reststat = list()
    gathered = {self.source+"_restname":[],self.source+"_restcode":[]}
    #
    # Define which endpoints to make request of and what data to gather
    restdata = virustotal_apifcall(self,config,dict((dictvals[self.source]["restend"][method]).items()+({"target":target}).items()))
    gathered[self.source+"_restname"].append(method)
    if isinstance(restdata,dict) and len(restdata) > 0:
        gathered[self.source+"_restcode"].append(restdata[self.source+"_restcode"])
        for field in dictvals[self.source]["restend"][method]["fields"]:
            if (isinstance(dictvals[self.source]["restend"][method]["fields"],dict) and field in dictvals[self.source]["restend"][method]["fields"] and not isinstance(dictvals[self.source]["restend"][method]["fields"][field],list)) \
               or isinstance(dictvals[self.source]["restend"][method]["fields"],list):
                srcfield = field.split(":")[0] if ":" in field else field
                dstfield = field.split(":")[1] if ":" in field else field
                if srcfield in restdata and len(str(restdata[srcfield])) > 0: gathered[dstfield] = json.dumps(restdata[srcfield]) if isinstance(restdata[srcfield],dict) else restdata[srcfield]
            elif isinstance(dictvals[self.source]["restend"][method]["fields"],dict):
                if field not in restdata: continue
                if isinstance(dictvals[self.source]["restend"][method]["fields"][field],list):
                    for child in dictvals[self.source]["restend"][method]["fields"][field]:
                        srcfield = child.split(":")[0] if ":" in child else child
                        dstfield = field+"_"+child.split(":")[1] if ":" in child else field+"_"+child
                        if srcfield in restdata[field] and len(str(restdata[field][srcfield])) > 0: gathered[dstfield] = json.dumps(restdata[field][srcfield]) if isinstance(restdata[field][srcfield],dict) else restdata[field][srcfield]
    else: gathered[self.source+"_restcode"].append("ERR:C1")
    #
    # Define the positives value if does not exist by enumerating results
    if "positives" not in gathered and "positives" in dictvals[self.source]["restend"][method]["fields"]:
        positives = 0
        for field in gathered:
            try: posearch = re.findall(r'\{((.+?)|)((u\')|(\"))positives(\'|\")\:(\s+)?(\d+).+?\}',str(gathered[field]))
            except: continue
            for result in posearch:
                try: positives += int(result[7])
                except: continue
        gathered["positives"] = positives
    #
    # Return the new dictionary of gathered data from the API
    return gathered
#-----------------------------------------------------------------------------
#
#-- VirusTotal API Call Function ---------------------------------------------
def virustotal_apifcall(self,config,restdict):
    import requests,json
    restdata = dict()
    restcode = None
    #
    # Call the endpoint as defined handling errors
    u = config["enrichrest_virustotal"]["enrichrest_virustotal_baseurl"]+restdict["endpoint"]
    h = {"Authorization":"Bearer "+config["enrichrest_virustotal"]["enrichrest_virustotal_apikey"]}
    p = {"apikey":config["enrichrest_virustotal"]["enrichrest_virustotal_apikey"],restdict["farget"]:restdict["target"]}
    try: response = requests.get(u,headers=h,params=p,verify=config["enrichrest_virustotal"]["requests_verify"],cert=config["enrichrest_virustotal"]["requests_cert"])
    except: restcode = "ERR:C2"
    else:
        if response.status_code == 200:
            try: restdata = json.loads(response.text)
            except: restcode = "ERR:C3"
        if restcode is None: restcode = response.status_code
    #
    # Return the new dictionary of gathered data based on method provided
    return dict(restdata.items()+({self.source+"_restcode":restcode}).items())
#-----------------------------------------------------------------------------
#
#-- VirusTotal: Parent Function ----------------------------------------------
def virustotal(self,config,record,parent=False):
    #
    # Validate the required configuration is present and makes sense
    if "enrichrest_virustotal_baseurl" not in config["enrichrest_virustotal"] or config["enrichrest_virustotal"]["enrichrest_virustotal_baseurl"] in [None,"None"]: record[self.source+"_output"].append("ERROR: Missing or undefined configuration option (enrichrest_virustotal_baseurl)")
    elif not re.match(r'^https\:\/\/.+?$',config["enrichrest_virustotal"]["enrichrest_virustotal_baseurl"]): record[self.source+"_output"].append("ERROR: Invalid value specified for configuration option (enrichrest_virustotal_baseurl)")
    elif "enrichrest_virustotal_apikey" not in config["enrichrest_virustotal"] or config["enrichrest_virustotal"]["enrichrest_virustotal_apikey"] in [None,"None"]: record[self.source+"_output"].append("ERROR: Missing or undefined configuration option (enrichrest_virustotal_apikey)")
    elif len(config["enrichrest_virustotal"]["enrichrest_virustotal_apikey"]) == 0: record[self.source+"_output"].append("ERROR: Invalid value specified for configuration option (enrichrest_virustotal_apikey)")
    #
    # Validate the required options have values which make sense
    if self.target not in record or len(record[self.target]) == 0: record[self.source+"_output"].append("Field specified was not found in the event")
    try:
        if self.method.lower() in ["filereport","filebehaviour"]: rhash = re.search(r'^([a-zA-Z0-9]+)$',record[self.target].lower(),re.UNICODE)
        elif self.method.lower() in ["urlreport","domainreport"]: rhash = re.search(r'^(\S+)$',record[self.target].lower(),re.UNICODE)
        elif self.method.lower() in ["ipreport"]: rhash = re.search(r'^([\d\.]+)$',record[self.target].lower(),re.UNICODE)
    except: record[self.source+"_output"].append("Unable to parse the target field")
    else:
        try: thash = rhash.group(1)
        except: record[self.source+"_output"].append("Target field specified is invalid")
    if self.method.lower() in dictvals[self.source]["methods"]: method = self.method.lower()
    else: record[self.source+"_output"].append("Valid methods are: "+(", ".join(dictvals[self.source]["methods"])))
    if not parent and len(record[self.source+"_output"]) > 0: return record
    #
    # Query for any usable data already in the KV Store for caching
    selectkv = spkv(self,conf(self),str(self._metadata.searchinfo.app),"select","cave_dt_virustotal_cache",{"query":{"target":thash,"method":method}})
    if selectkv["failed"]: record[self.source+"_output"].append("Failed to query KV Store for caching: "+selectkv["reason"] if not parent else str())
    elif "data" in selectkv and len(selectkv["data"]) > 0:
        kvscache = sorted(selectkv["data"],key=lambda k:k["fetched"],reverse=True)[0]
        #
        # Determine if this cache data is usable before proceeding
        if isinstance(kvscache,dict): record[self.source+"_output"].append("Cache data was found for target" if not parent else str())
        else: record[self.source+"_output"].append("No usable cache data was found for target" if not parent else str())
    else: record[self.source+"_output"].append("No cache data found for target" if not parent else str())
    #
    # If recursive call return only the data from the KV Store for caching
    if isinstance(parent,bool) and parent: return kvscache if "kvscache" in vars() and kvscache is not None and isinstance(kvscache,dict) else False
    elif not isinstance(parent,bool):
        record[self.source+"_output"].append("The parent parameter must be boolean")
        return record
    #
    # Reach out to API if there is no data in the KV Store for caching
    if "kvscache" not in vars() or not isinstance(kvscache,dict):
        apifdict = virustotal_apif(self,config,method,thash)
        if len(apifdict[self.source+"_restcode"]) == 0: record[self.source+"_output"].append("Failed to query VirusTotal API")
        elif len([scode for scode in apifdict[self.source+"_restcode"] if scode not in [200,404]]) > 0: record[self.source+"_output"].append("Errors when querying VirusTotal API - "+str(apifdict[self.source+"_restcode"]))
        elif 200 in apifdict[self.source+"_restcode"]:
            record[self.source+"_output"].append("Data was found via data provider API")
            #
            # Prepare and store the record in the KV store for caching
            apifdict.update({"fetched":int(time.time()),"method":method,"target":thash,"stance":None})
            if "positives" not in apifdict: apifdict["stance"] = "neutral"
            else: apifdict["stance"] = "neutral" if int(apifdict["positives"]) == 1 else ("bad" if int(apifdict["positives"]) > 1 else "good")
            insert = spkv(self,conf(self),str(self._metadata.searchinfo.app),"insert","cave_dt_virustotal_cache",{"data":apifdict})
            if insert["failed"]: record[self.source+"_output"].append("Failed to insert record into KV Store: "+insert["reason"])
            else: record[self.source+"_output"].append("Cache data was stored for target")
        #
        # Indicate when there were no results found via the API
        elif 404 in apifdict[self.source+"_restcode"]:
            record[self.source+"_output"].append("No data was found via data provider API")
            insert = spkv(self,conf(self),str(self._metadata.searchinfo.app),"insert","cave_dt_virustotal_cache",{"data":{"fetched":int(time.time()),"method":method,"target":thash,"stance":"neutral"}})
            if insert["failed"]: record[self.source+"_output"].append("Failed to insert record into KV Store: "+insert["reason"])
            else: record[self.source+"_output"].append("Cache entry created for target")
    #
    # Refetch cache if there was data returned by the API and stored
    if ("insert" in vars() and not insert["failed"]) and ("kvscache" not in vars() or not isinstance(kvscache,dict)):
        kvscache = virustotal(self,config,dict(record.items()),parent=True)
        if kvscache is None or not isinstance(kvscache,dict): record[self.source+"_output"].append("Refetch failed for target")
        else: record[self.source+"_output"].append("Refetch succeeded for target")
    #
    # Integrate VirusTotal data from either the cache or from refetch
    if "kvscache" in vars() and isinstance(kvscache,dict):
        for field in dictvals[self.source]["restend"][method]["fields"]:
            if (isinstance(dictvals[self.source]["restend"][method]["fields"],dict) and field in dictvals[self.source]["restend"][method]["fields"] and not isinstance(dictvals[self.source]["restend"][method]["fields"][field],list)) \
               or isinstance(dictvals[self.source]["restend"][method]["fields"],list):
                fname = field.split(":")[1] if ":" in field else field
                if fname in kvscache: fdata = kvscache[fname]
                else: continue #fdata = None
                record[dictvals[self.source]["prefix"]+"_"+method+"_"+fname] = fdata
            elif isinstance(dictvals[self.source]["restend"][method]["fields"],dict):
                for child in dictvals[self.source]["restend"][method]["fields"][field]:
                    fname = field+"_"+child.split(":")[1] if ":" in child else field+"_"+child
                    if fname in kvscache: fdata = kvscache[fname]
                    else: continue #fdata = None
                    record[dictvals[self.source]["prefix"]+"_"+method+"_"+fname] = fdata
        for field in ["fetched","method","target","stance"]: record[field] = kvscache[field] if field in kvscache else None
    #
    # Return the requested data to the upstream calling routine
    record[self.source+"_output"].extend(apifdict[self.source+"_output"] if "apifdict" in vars() and isinstance(apifdict,dict) and self.source+"_output" in apifdict else list())
    record.update({self.source+"_restname":apifdict[self.source+"_restname"] if "apifdict" in vars() and isinstance(apifdict,dict) and self.source+"_restname" in apifdict else None})
    record.update({self.source+"_restcode":apifdict[self.source+"_restcode"] if "apifdict" in vars() and isinstance(apifdict,dict) and self.source+"_restcode" in apifdict else None})
    return record
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# REST Enrichments                                                             #
#------------------------------------------------------------------------------#
#
#-- Iterate Records ----------------------------------------------------------
@Configuration()
class EnrichrestCommand(ReportingCommand):
    #
    # Basic options that can be used with this Splunk SPL command
    source = Option(require=True, validate=validators.Fieldname())
    method = Option(require=True, validate=validators.Fieldname())
    target = Option(require=False,validate=validators.Fieldname())
    update = Option(require=False,validate=None)
    @Configuration()
    #
    # Perform the map and reduce functions when called to do so by Splunk
    def map(self,records): return records
    def reduce(self,records):
        necords = list()
        #
        # Load configuration saved into dictionary for later iteration
        config = conf(self)
        if config["httpsproxy"]["httpsproxy_address"] is not None and len(config["httpsproxy"]["httpsproxy_address"]) > 0:
            os.environ["https_proxy"] = config["httpsproxy"]["httpsproxy_address"]
            os.environ["no_proxy"] = "127.0.0.1"+((","+config["httpsproxy"]["httpsproxy_bypass"]) if config["httpsproxy"]["httpsproxy_bypass"] is not None and len(config["httpsproxy"]["httpsproxy_bypass"]) > 0 else "")
        #
        # Iterate the current records into new records to be returned
        if self.source in ["opendns","virustotal"] and self.method in dictvals[self.source]["methods"]:
            for record in records:
                #
                # Process the records with the appropriate REST endpoints
                sepoch = round(time.time(),2)
                if self.source == "opendns": necord = opendns(self,config,dict(record.items()+({self.source+"_output":[]}).items()))
                elif self.source == "virustotal": necord = virustotal(self,config,dict(record.items()+({self.source+"_output":[]}).items()))
                #
                # Update the new record and append it to the list
                necord.update({self.source+"_durtime":"{:.2f}".format(round(abs(time.time()-sepoch),2))})
                necords.append(necord)
        #
        # Return the new processed list of dictionary event records
        else: return records
        return necords
#
# Dispatch the Splunk SDK call to the appropriate class to process the records
if __name__ == "__main__": dispatch(EnrichrestCommand,sys.argv,sys.stdin,sys.stdout,__name__)
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#
