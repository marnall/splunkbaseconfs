import splunk.Intersplunk
import json
import splunk.rest
import logger_manager as log
import splunk.search as splunkSearch
import os

# Set up logger
logger = log.setup_logging('trustar_remove_whitelist_indicator')
app_name = __file__.split(os.sep)[-3]

results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
session_key = settings.get("sessionKey")

def update_collection(session_key, result, query_results, collection_name, collection_field, app_name):
    if query_results:
        rest_endpoint = "/services/data/threat_intel/item/" + collection_name
        for res in query_results:
            value = {"item":json.dumps({"_key" : str(res["item_key"]), "disabled":"false"})}
            try:
                splunk.rest.simpleRequest(rest_endpoint, sessionKey=session_key, method='PUT', postargs=value, getargs={"output_mode": "json"}, raiseAllErrors=True)
                logger.info("Successfully updated threat to Threat Intelligence collections.")
            except Exception as e:
                logger.error("TruSTAR Error: Failed to update indicator in {} lookup ".format(collection_name) + str(e))
    else:
        query = '| makeresults | eval ' + collection_field + '="' + result['value'] + '" | eval description="TruSTAR Threats" | eval weight="' + result["weight"] +'" | outputlookup append=true local_' + collection_name
        try:
            splunkSearch.searchAll(query, sessionKey=session_key, namespace=app_name, owner='nobody')
            logger.info("Successfully added threat to Threat Intelligence collections.")
        except Exception as e:
            logger.error("TruSTAR error: Error while adding indicator in local_{} lookup ".format(collection_name) + str(e))

def remove_whitelisted_indicator(results):
    collections_mapping = { "IP" : ["ip_intel", "ip"],
                            "MD5" : ["file_intel", "file_hash"],
                            "SHA256" : ["file_intel", "file_hash"],
                            "SHA1" : ["file_intel", "file_hash"],
                            "SOFTWARE" : ["file_intel","file_name"],
                            "URL" : ["http_intel", "url"],
                            "REGISTRY_KEY" : ["registry_intel", "registry_path"],
                            "EMAIL_ADDRESS" : ["email_intel", "src_user"] }
    for result in results:
        if result["type"] in collections_mapping:
            collection_name = collections_mapping[result["type"]][0]
            collection_field = collections_mapping[result["type"]][1]
            result["value"] = (result["value"]).replace("\\","\\\\\\\\")
            query = '| inputlookup ' + collection_name + ' where description="TruSTAR Threats" ' + collection_field + '="' + result["value"] + '" | eval item_key=_key | table item_key'
            try:
                query_results = splunkSearch.searchAll(query, sessionKey=session_key, namespace=app_name, owner='nobody')
            except Exception as e:
                logger.error("TruSTAR error: Error while searching in {} lookup ".format(collection_name)+ str(e))
                break
            update_collection(session_key, result, query_results, collection_name, collection_field, app_name)     
        else:
            logger.error("%s indicator type not supported in Threat Intelligence" % str(result["type"]))

remove_whitelisted_indicator(results)