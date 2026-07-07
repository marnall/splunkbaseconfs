#==============================================================================#
# Continuous Automation and Visibility Engine                    Set Solutions #
# Library of Common Functions                      Engineering and Development #
#==============================================================================#


#------------------------------------------------------------------------------#
# Splunk KV Store                                                              #
#------------------------------------------------------------------------------#
#
#-- Splunk KV Store ----------------------------------------------------------
# This function performs queries against the Splunk API in order to manipulate
# KV Store collection data. It is capable of creating, modifying, and deleting
# records. Returned is a dictionary with information about success or failure.
#-----------------------------------------------------------------------------
# More details for statistics collected for each Splunk KV Stores can be found
# https://docs.mongodb.com/manual/reference/command/collStats
#-----------------------------------------------------------------------------
def spkv(self,config,appname,method,kvstore=None,params=None):
    import requests,json
    from xml.dom import minidom
    #
    # Prepare basic data values for connecting based on provided parameters
    headers = {"Authorization":("Splunk "+str(self._metadata.searchinfo.session_key))}
    if method in ["insert","select","update","stats"]: headers.update({"Content-Type":"application/json"})
    if method in ["insert","select","update","delete"]:
        baseurl = str(self._metadata.searchinfo.splunkd_uri)+"/servicesNS/nobody/"+appname+"/storage/collections/data/"+kvstore
        if method == "update": baseurl = baseurl+"/"+params["_key"]
        elif method in ["select","delete"]: baseurl = baseurl+"?query="+json.dumps(params["query"])
    elif method == "stats": baseurl = str(self._metadata.searchinfo.splunkd_uri)+"/services/server/introspection/kvstore/collectionstats"
    sslspec = {"cert":config["splunkrest"]["requests_cert"],"verify":config["splunkrest"]["requests_verify"]}
    #
    # Execute the request against Splunk and handle any exceptions
    try:
        if method in ["insert","update"]: response = requests.post(baseurl,data=json.dumps(params["data"]),headers=headers,verify=sslspec["verify"],cert=sslspec["cert"])
        elif method in ["select","stats"]: response = requests.get(baseurl,headers=headers,verify=sslspec["verify"],cert=sslspec["cert"])
        elif method == "delete": response = requests.delete(baseurl,headers=headers,verify=sslspec["verify"],cert=sslspec["cert"])
    except Exception as exception: return {"failed":True,"reason":"Exception occurred when executing Splunk API request ("+str(exception)+")"}
    if response.status_code not in [200,201]: return {"failed":True,"reason":"Unexpected status code returned by Splunk API ("+str(response.status_code)+"/"+response.text+")"}
    #
    # Collect statistics from Splunk based on the provided parameters
    if method == "stats":
        spkvstat = dict()
        for node in minidom.parseString(response.text).getElementsByTagName("s:item"):
            try: itemdict = json.loads(node.firstChild.data)
            except: continue
            else:
                if "ns" not in itemdict or itemdict["ns"].split(".")[0] != appname: continue
                specdict = dict()
                for field in ["numExtents","storageSize","count","size","avgObjSize"]: specdict.update({field:itemdict[field] if field in itemdict else None})
                try: spkvstat.update({itemdict["ns"].split(".")[1]:specdict})
                except: continue
        if len(spkvstat) == 0: return {"failed":True,"reason":"No statistics were found for any KV Stores"}
        else: return {"failed":False,"data":spkvstat}
    #
    # Parse information returned from Splunk for standard operations
    else:
        if method != "delete":
            try: respdata = json.loads(response.text)
            except: return {"failed":True,"reason":"Exception occurred when parsing Splunk API response"}
        if method in ["insert","update"]:
            if "_key" in respdata: return {"failed":False,"_key":respdata["_key"]}
            else: return {"failed":True,"reason":"There was no key returned by the Splunk API"}
        elif method in ["select","stats"]: return {"failed":False,"data":respdata}
        elif method == "delete": return {"failed":False}
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#


#------------------------------------------------------------------------------#
# CAVE Configuration                                                           #
#------------------------------------------------------------------------------#
#
#-- CAVE Configuration -------------------------------------------------------
# This function loads configuration from the local or default directory. There
# could be parameters required before a successful API connection can be made.
#-----------------------------------------------------------------------------
def conf(self):
    config = dict()
    fields = {"splunkrest":["splunkrest_verify","splunkrest_certauth","splunkrest_clientcrt","splunkrest_clientkey"],
              "enrichrest_opendns":["enrichrest_opendns_verify","enrichrest_opendns_baseurl","enrichrest_opendns_apikey","enrichrest_opendns_certauth","enrichrest_opendns_clientcrt","enrichrest_opendns_clientkey","enrichrest_opendns_retain_bad","enrichrest_opendns_retain_neutral","enrichrest_opendns_retain_good"],
              "enrichrest_virustotal":["enrichrest_virustotal_verify","enrichrest_virustotal_baseurl","enrichrest_virustotal_apikey","enrichrest_virustotal_certauth","enrichrest_virustotal_clientcrt","enrichrest_virustotal_clientkey","enrichrest_virustotal_retain_bad","enrichrest_virustotal_retain_neutral","enrichrest_virustotal_retain_good"],
              "httpsproxy":["httpsproxy_address","httpsproxy_bypass"]}
    #
    # Iterate through the configuration as provided by the Splunk SDK defining
    # dictionary entries for returning to the upstream function
    for stanza in fields:
        if stanza not in config: config.update({stanza:dict()})
        for field in fields[stanza]:
            try: config[stanza].update({field:self.service.confs[str(self._metadata.searchinfo.app)][stanza][field]})
            except: config[stanza].update({field:None})
    #
    # Prepare the necessary values for future requests to the Splunk API
    for stanza in ["splunkrest","enrichrest_opendns","enrichrest_virustotal"]:
        config[stanza].update({"requests_cert":None,"requests_verify":False})
        if config[stanza][stanza+"_clientcrt"] != None and len(config[stanza][stanza+"_clientcrt"]) >= 1:
            if config[stanza][stanza+"_clientkey"] != None and len(config[stanza][stanza+"_clientkey"]) >= 1:
                config[stanza].update({"requests_cert":(config[stanza][stanza+"_clientcrt"],config[stanza][stanza+"_clientkey"])})
        if config[stanza][stanza+"_certauth"] != None and len(config[stanza][stanza+"_certauth"]) >= 1:
            if str(config[stanza][stanza+"_certauth"]) in ["0","1"]: config[stanza][stanza+"_certauth"] = True if str(config[stanza][stanza+"_certauth"]) == "1" else False
    #
    # Return the complete dictionary of the CAVE configuration
    return config
#-----------------------------------------------------------------------------
#
#------------------------------------------------------------------------------#
