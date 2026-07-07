
# encoding = utf-8
from urllib.request import Request, urlopen, ProxyHandler, build_opener, install_opener, HTTPBasicAuthHandler, HTTPPasswordMgrWithDefaultRealm
from urllib.error import URLError
from urllib.parse import urlencode, quote
from pathlib import Path
import os
import sys
import time
import datetime
import json
import time
import re
import base64
import ssl
import sys
import csv
import http.client
import logging, logging.handlers
import splunk

    ##########################################################
    #                    START OF SCRIPT                     #
    ##########################################################
    
    
    
          ################################################
          #            HMI VARIABLE DECLARATION          #
          ################################################
def validate_input(helper, definition):
   #Implement your own validation logic to validate the input stanza configurations
    global_account = definition.parameters.get('global_account', None)
    api_url = definition.parameters.get('api_url', None)
    ioc_types = definition.parameters.get('ioc_types', None)
    minimum_threat_value = definition.parameters.get('minimum_threat_value', None)
    last_update_since = definition.parameters.get('last_update_since', None)
    splunk_cloud = definition.parameters.get('splunk_cloud', None)
    indexing = definition.parameters.get('indexing', None)
    pass



          ################################################
          #               IOCs Collecting                #
          ################################################
def collect_events(helper, ew):

 ################# Beginning Of The Variable Decleration ##################
  
    # get arguments of a particular input
    opt_threat_level = int(helper.get_arg('minimum_threat_value'))
    opt_ioc_types = [helper.get_arg('ioc_types')]
    name_ioc = helper.get_arg('ioc_types')
    opt_threat_types = helper.get_arg('threat_types')
    
    # get global variable configuration
    global_account = helper.get_arg('global_account')
    user = global_account['username']
    pwd = global_account['password']
    indexing = helper.get_arg('indexing')
    splunk_cloud = helper.get_arg('splunk_cloud')
    opt_data_url = helper.get_global_setting('api_url')
    last_updated_min = int(helper.get_arg('last_update_since'))
    opt_last_updated = 60 * int(helper.get_arg('last_update_since'))
    urlapi = opt_data_url + "/mrti/bulk-search/"
    proxySettings= helper.get_proxy()
    caractere = "[]'"
    
    # bulk search request
    data_bulk = {"query_body":{"AND":[{"AND":[{"type":"filter","field":"atom_type","multi_values":opt_ioc_types},{"type":"filter","field":"last_updated","value":opt_last_updated},{"type":"filter","field":"risk","range":{"gt":opt_threat_level}}]}]},"query_fields":["atom_value","first_seen","last_updated","threat_hashkey","threat_types","threat_scores","sources","tags"]}
    data_bulk = json.dumps(data_bulk).encode('ascii')
    
    start_time = time.time()
    today = datetime.datetime.today().strftime('%Y-%m-%d-%H-%M-%S')
    yesterday = (datetime.date.today()-datetime.timedelta(2)).strftime('%Y-%m-%d')

  #################### End Of The Variable Decleration ##################
    
    logging.info("IOCType=" + name_ioc + " Status=Start")
    logging.info("IOCType=" + name_ioc + " MinimunThreatValue=" + str(opt_threat_level) + " LastUpdatedSince=" + str(last_updated_min) + " seconds" + " User=" + user + " BulkSearch=" + str(data_bulk))
    
    if (opt_threat_level > 100):
      interval = (time.time() - start_time)
      logging.error("IOCType=" + name_ioc + " MinimumThreatValue = Error")
      logging.error("Status=End Runtime=" + str(interval) + " seconds")
      sys.exit()
    if (opt_threat_level < 0):
      interval = (time.time() - start_time)
      logging.error("IOCType=" + name_ioc + " MinimumThreatValue = Error")
      logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
      sys.exit()
    

  ################# Beginning Of The Proxy Decleration ##################
   
    # warning : splunk cloud does not accept proxy connections
    if splunk_cloud == "no" :
        logging.info("IOCType=" + name_ioc + " Message=\"Proxy configuration in progress\"")
        if proxySettings != {}:
            proxy_type = proxySettings['proxy_type']
            proxy_url = proxySettings['proxy_url']
            proxy_port = proxySettings['proxy_port']
            proxy_username = proxySettings['proxy_username']
            proxy_password = proxySettings['proxy_password']
        
            if ((proxy_port != "") and (proxy_url != "")) :
                proxy_url_port = str(proxy_url) + ":" + str(proxy_port)
                if ((proxy_username != "") and (proxy_password != "")):
                    auth = HTTPPasswordMgrWithDefaultRealm()
                    auth.add_password(None, proxy_url_port, str(proxy_username), str(proxy_password))
                    handler = HTTPBasicAuthHandler(auth)
                    logging.info("IOCType=" + name_ioc + ' Proxy user=' + proxy_username)
                    try :
                        opener = build_opener(handler)
                    except Exeption as e :
                        interval = (time.time() - start_time)
                        logging.error("IOCType=" + name_ioc + " Proxy=Error")
                        logging.error(e)
                        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
                        sys.exit()
                elif (((proxy_username != "") and (proxy_password == "")) or ((proxy_username == "") and (proxy_password != ""))) :
                    interval = (time.time() - start_time)
                    logging.error("IOCType=" + name_ioc + " Proxy=Error")
                    logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
                    sys.exit()
                else :
                    try :
                        handler = ProxyHandler({str(proxy_type): proxy_url_port, 'https': proxy_url_port})
                        opener = build_opener(handler)
                    except Exeption as e :
                        interval = (time.time() - start_time)
                        logging.error("IOCType=" + name_ioc + " Proxy=Error")
                        logging.error(e)
                        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
                        sys.exit()
            try :
                install_opener(opener)
            except Exeption as e :
                interval = (time.time() - start_time)
                logging.error("IOCType=" + name_ioc + " Proxy=Error")
                logging.error(e)
                logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
                sys.exit()
            logging.info("IOCType=" + name_ioc + " Proxy=Configured")
        else :
            logging.info("IOCType=" + name_ioc + " Proxy=NoConfiguration")
    else :
        logging.info("IOCType=" + name_ioc + " Proxy=NoConfiguration")
  ################# End Of The Proxy Decleration ##################
    
  ################# Beginning Of The Function Decleration ##################
    
    #function passing query
    def urlparse(url, head, data=None):
        if url.startswith('https://') :
            if head == None :
                req = Request(url)
            elif data == None :
                req = Request(url, headers=head)
            else :
                req = Request(url, headers=head, data=data)
            try:
                response = urlopen(req)
                return response
            except Exception as e:
                logging.error("IOCType=" + name_ioc + " Parsing=" + "\"" + str(e) + "\"")
                if str(e) == "<urlopen error [Errno 110] Connection timed out>":
                    logging.error("IOCType=" + name_ioc + " Proxy=Error")
                    logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
                if str(e) == "HTTP Error 401: UNAUTHORIZED":
                    logging.error("IOCType=" + name_ioc + " Access=Error")
                    logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")

    
    #function to have a token
    def gettoken(user, pwd):
            data = {'email': user, 'password': pwd}
            data = json.dumps(data).encode('ascii')
            authurl = opt_data_url + "/auth/token/"
            headers = {"content-type": "application/json"}
            try:
                reponse = urlparse(authurl, headers, data)
                page = reponse.read().decode('utf-8')
                json_response = json.loads(page)
                token = json_response['access_token']
                return token
            except Exception as e:
                logging.error("IOCType=" + name_ioc + " TokenError=" + "\"" + str(e) + "\"")


     #function for connecting to the API endpoint and collecting queryhash
    def getid(url, token, data):
        token = "Token " + token
        headers = {"accept": "application/json", "Authorization": token, "Content-Type": "application/json"}
        try :
            reponse = urlparse(url, headers, data)
            page = reponse.read().decode('utf-8')
            json_response = json.loads(page)
            query = json_response['task_uuid']
            return query
        except Exception as e:
             logging.error("IOCType=" + name_ioc + " QueryError=" +  "\"" + str(e) + "\"")
    
    #function for connecting to the API endpoint and collecting IOCs
    def getioc(url, token):
        token = "Token " + token
        header = {"accept": "application/json", "Authorization": token}
        try :
            reponse = urlparse(url, header)
            return reponse
        except Exception as e:
             logging.error("IOCType=" + name_ioc + " ApiError=" + str(e))
            
    ################# End Of The Function Decleration ##################

    ################# Beginning Of IOCs Collect ##################
    
    # Connecting to the API and collect an authentication token
    logging.info("IOCType=" + name_ioc + " Message=\"Connecting to the API and collect an authentication token in progress\"")
    tok = gettoken(user, pwd)
    if tok is None :
        interval = (time.time() - start_time)
        logging.error("IOCType=" + name_ioc + " Token=Error")
        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
        sys.exit()
    else :
        logging.info("IOCType=" + name_ioc + " Token=Collected")
    
    # Connecting to the API and collect aquery hash
    logging.info("IOCType=" + name_ioc + " Messages=\"Connecting to the API and collect a query hash\"")
    query_id = getid(urlapi, tok, data_bulk)
    if query_id is None :
        interval = (time.time() - start_time)
        logging.error("IOCType=" + name_ioc + " Query=Error")
        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
        sys.exit()
    else :
        logging.info("IOCType=" + name_ioc + " Query=Collected")
        
    time.sleep(60)
    
    # Connecting to the API and collect IOCs
    logging.info("IOCType=" + name_ioc + " Message=\"Connecting to the API and collect IOCs\"")
    request_query = urlapi + "task/" + str(query_id) + "/"
    ioc = getioc(request_query, tok)
    if ioc is None :
        interval = (time.time() - start_time)
        logging.error("IOCType=" + name_ioc + " IOC=Error /" +  request_query)
        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
        sys.exit()
    else :
        logging.info("IOCType=" + name_ioc + " IOC=Collected")
        
    pageioc = ioc.read().decode('utf-8')
    json_response = json.loads(pageioc)
    
     ################# End Of The Function Decleration ##################

    ################# Beginning Of IOCs Collect ##################
    
    # Connecting to the API and collect an authentication token
    logging.info("IOCType=" + name_ioc + " Message=\"Connecting to the API and collect an authentication token in progress\"")
    tok = gettoken(user, pwd)
    if tok is None :
        interval = (time.time() - start_time)
        logging.error("IOCType=" + name_ioc + " Token=Error")
        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
        sys.exit()
    else :
        logging.info("IOCType=" + name_ioc + " Token=Collected")
    
    # Connecting to the API and collect aquery hash
    logging.info("IOCType=" + name_ioc + " Messages=\"Connecting to the API and collect a query hash\"")
    query_id = getid(urlapi, tok, data_bulk)
    if query_id is None :
        interval = (time.time() - start_time)
        logging.error("IOCType=" + name_ioc + " Query=Error")
        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
        sys.exit()
    else :
        logging.info("IOCType=" + name_ioc + " Query=Collected")
        
    time.sleep(60)
    
    # Connecting to the API and collect IOCs
    logging.info("IOCType=" + name_ioc + " Message=\"Connecting to the API and collect IOCs\"")
    request_query = urlapi + "task/" + str(query_id) + "/"
    ioc = getioc(request_query, tok)
    if ioc is None :
        interval = (time.time() - start_time)
        logging.error("IOCType=" + name_ioc + " IOC=Error /" +  request_query)
        logging.error("IOCType=" + name_ioc + " Status=End Runtime=" + str(interval) + " seconds")
        sys.exit()
    else :
        logging.info("IOCType=" + name_ioc + " IOC=Collected")
        
    pageioc = ioc.read().decode('utf-8')
    json_response = json.loads(pageioc)
    
 ################# End Of IOCs Collect ##################
 
 ################# Beginning Of Result Processing (json to csv) ##################
    #traitement du résultat (json vers csv)
    path = "../" + name_ioc + "_data.json"
    path1 = Path(__file__).parent / path
    with open(path1,"w") as write_file:
          json.dump(json_response,write_file)
    
    with open(path1) as json_file:
           data = json.load(json_file)
    
    result = data['results']
    if ((name_ioc == "ip") or (name_ioc == "ip_range")):
        head = ["ip", "first_seen", "last_updated", "threat_hashkey", "threat_types", "threat_scores", "sources" , "tags", "description"]
    elif ((name_ioc == "domain") or (name_ioc == "fqdn")) :
        head = ["domain", "first_seen", "last_updated", "threat_hashkey", "threat_types", "threat_scores", "sources" , "tags", "description"]
    elif (name_ioc == "file") :
        head = ["file_hash", "first_seen", "last_updated", "threat_hashkey", "threat_types", "threat_scores", "sources" , "tags", "description"]
    elif (name_ioc == "email"):
           head = ["src_user", "first_seen", "last_updated", "threat_hashkey", "threat_types", "threat_scores", "sources" , "tags", "description"]
    elif (name_ioc == "regkey"):
        head = ["registry_path", "first_seen", "last_updated", "threat_hashkey", "threat_types", "threat_scores", "sources" , "tags", "description"]
    elif (name_ioc == "ssl"):
        head = ["certificate_serial", "first_seen", "last_updated", "threat_hashkey", "threat_types", "threat_scores", "sources" , "tags", "description"]
    else :
        head = [name_ioc, "first_seen", "last_updated", "threat_hashkey", "threat_types", "threat_scores", "sources" , "tags", "description"]
    path = "../lookups/datalake_" + name_ioc + ".csv"
    path2 = Path(__file__).parent / path
    data_file = open(path2, "w")
    csv_writer = csv.writer(data_file)
    csv_writer.writerow(head)
    r=0

    for i in result:
        threat_type = str(i[4])
        threat_score = str(i[5])
        sources = str(i[6])
        tags = str(i[7])
        for y in caractere:
            threat_type = threat_type.replace(y,"")
            threat_score = threat_score.replace(y,"")
            sources = sources.replace(y,"")
            tags = tags.replace(y,"")
        i[4] = threat_type
        i[5] = threat_score
        i[6] = sources
        i[7] = tags
        description = "[" + str(i[4]) + "][" + str(i[5]) + "][" + str(i[6]) + "][" + str(i[7]) +"]"
        csv_writer.writerow(i + [description])
        r = r + 1
    
    data_file.close()
        
    if indexing == "yes" :
        sourcet = "datalake_" + name_ioc
        event_ok = 0
        for i in range(len(result)):
            event = helper.new_event(data=str(result[i]), source="datalake_connect", sourcetype=sourcet)
            ew.write_event(event)
            event_ok = event_ok +1
        logging.info("Datalake Connect number of events processed : " + str(event_ok))
    ################# End Of Result Processing ##################
    os.remove(path1)
        
    interval = (time.time() - start_time)
    logging.info("IOCType=" + name_ioc + " IOCNumber=" + str(r) + " Status=End Runtime=" + str(interval) + " seconds")
    
    ##########################################################
    #                    END OF SCRIPT                     #
    ##########################################################