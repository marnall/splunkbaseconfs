import splunk.Intersplunk
import json
import splunk.rest
import logger_manager as log
import splunk.search as splunkSearch
import os
import urllib
# Set up logger
logger = log.setup_logging('trustar_whitelist_indicator')
app_name = __file__.split(os.sep)[-3]

events, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
session_key = settings.get("sessionKey")

def get_query_list(events):
    collections_mapping = { 
        "IP" : ["ip_intel", "ip"],
        "MD5" : ["file_intel", "file_hash"],
        "SHA256" : ["file_intel", "file_hash"],
        "SHA1" : ["file_intel", "file_hash"], 
        "SOFTWARE" : ["file_intel","file_name"], 
        "URL" : ["http_intel", "url"], 
        "REGISTRY_KEY" : ["registry_intel", "registry_path"], 
        "EMAIL_ADDRESS" : ["email_intel", "src_user"]
    }
    # Create collection based query list
    query_list = {}
    for result in events:
        if result["type"] in collections_mapping:
            collection_name = collections_mapping[result["type"]][0]
            collection_field = collections_mapping[result["type"]][1]
            result["indicator_value"] = (result["indicator_value"]).replace("\\","\\\\\\\\")
            if not collection_name in query_list:
                query = '| inputlookup ' + collection_name + ' where description="TruSTAR Threats" ' + collection_field + '="' + result["indicator_value"] + '"'
                query_list[collection_name] = query
            else:
                query = query_list[collection_name] + ' OR ' + collection_field + '="' + result["indicator_value"] + '"'
                query_list[collection_name] = query
        else:
            logger.error("%s indicator type not supported in Threat Intelligence" % str(result["type"]))
    return query_list

def whitelist_indicator(events):

    query_list = get_query_list(events)
        
    key_list = {}
    # Execute the queries to fetch key from threat intelligence lookup
    for key,query in query_list.items():
        query = query + " | eval item_key=_key | table item_key"
        try:
            results = splunkSearch.searchAll(query, sessionKey=session_key, namespace=app_name, owner='nobody')
            if len(results) > 0:
                key_list[key] = []
                for result in results:
                    value = {"_key":str(result["item_key"])}
                    key_list[key].append(value)
            else:
                logger.info("No matching trustar indicators found in Threat Intelligence collection: %s" % str(key))
        except Exception as e:
            logger.error("Failed to fetch threat keys from Threat Intelligence collection. %s " % str(e))

    # Rest call to delete the key found from threat intelligence lookup
    for key,value in key_list.items():
        list_of_keys = json.dumps(value, separators=(',', ':'))
        dummy_dict = {"trustar_key":list_of_keys}
        encoded_url = urllib.urlencode(dummy_dict)
        final_argument = encoded_url.lstrip("trustar_key=")
        rest_endpoint = "/services/data/threat_intel/item/" + key + "?item=" + final_argument
        try:
            response = splunk.rest.simpleRequest(rest_endpoint, sessionKey=session_key, method='DELETE', raiseAllErrors=True)
            result = json.loads(response[1])
            if str(result["status"] == "true"):
                logger.info("Successfully deleted threats from Threat Intelligence collection %s" % str(key))
            else:
                logger.info("Failed to delete threats from Threat Intelligence collection. %s" % str(result["message"]))
        except Exception as e:
            logger.error("Failed to delete threats from Threat Intelligence collection. %s" % str(e))

whitelist_indicator(events)