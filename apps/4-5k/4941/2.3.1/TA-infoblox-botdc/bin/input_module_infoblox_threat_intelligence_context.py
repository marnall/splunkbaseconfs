# encoding = utf-8
import os
import sys
import time
import datetime
import json
import base64
import requests
import splunklib.client as client
import splunklib.results as splunk_results

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):

    # Get variables
    opt_api_token = helper.get_global_setting('csp_api_key')
    interval = helper.get_arg('interval')
    helper.get_input_type()
    loglevel = helper.get_log_level()
    proxy_settings = helper.get_proxy()
    account = helper.get_arg('global_account')
    username = account['username']
    password = account['password']

    helper.log_debug("Parameters correctly obtained")

    # for each entry in KVstore not searched
    service = client.connect(username=username, password=password)
    helper.log_debug("Connection to splunk API OK")
    kwargs_oneshot = {"earliest_time": "2000-01-01T00:00:00.000-00:00", "latest_time": "now", "count": 40}
    
    searchquery_oneshot = "|inputlookup botdc_distinct_threat_indicators | stats values(enriched) as enriched, values(feed_type) as feed_type, min(event_time) as first_time_seen, sum(count) as count by threat_indicator | where NOT (isnull(enriched) OR match(enriched,\"1\"))| sort - count"

    oneshotsearch_results = service.jobs.oneshot(searchquery_oneshot, **kwargs_oneshot)
    
    helper.log_debug("Splunk search executed properly")

    # Get the results and display them using the ResultsReader
    reader = splunk_results.ResultsReader(oneshotsearch_results)
    for item in reader:
        threat_indicator = item.get('threat_indicator')
        if item.get('feed_type') == "IP Address":
            threat_indicator_type = "ip"
        elif item.get('feed_type') == "FQDN":
            threat_indicator_type = "host"

        # Do a Dossier search
        helper.log_info("Start perform an Infoblox Dossier Search for " + threat_indicator)

        url = "https://csp.infoblox.com/tide/api/services/intel/lookup/jobs?wait=true"
        payload = '{"target": {"one": {"type": "'+threat_indicator_type+'","target": "'+threat_indicator+'","sources":[ "alexa", "atp", "ccb", "dns", "gcs", "geo", "gsb", "isight", "malware_analysis", "pdns", "ptr", "rlabs", "rwhois", "sdf", "whois", "inforank", "malware_analysis_v3", "activity", "rpz_feeds", "custom_lists", "whitelist", "zvelo"]}}}'

        headers = {
       'Authorization':'Token %s' % opt_api_token,
       'Content-Type':'application/json',
       'Cache-Control': 'no-cache'
        }
        
        if not proxy_settings:
            response = requests.post(url, headers=headers, data=payload, cookies=None, verify=True, timeout=(600,600), stream=True)
        else:
            response = requests.post(url, headers=headers, data=payload, cookies=None, verify=True, timeout=(600,600), proxies=proxy_settings, stream=True)
        
        if response.encoding is None:
            response.encoding = 'utf-8'
        if response.text:
            try:
                r_json=json.loads(response.text)
            except:
                raise Exception("Unable to load into a json format")

            data = json.dumps(r_json)
            data = data.replace("\"host\":","\"hostname\":")
            data = data.replace("\"source\":","\"src\":")
            
            helper.log_debug("rcode: {}".format(response.status_code))
            helper.log_debug("data: " + data)
            
            
            data = json.loads(data)

            if "results" in data.keys():
                for result in data["results"]:
                    if "params" in result.keys():
                        if "src" in result["params"].keys():
                            if "data" in result.keys():
                                
                                if result["params"]["src"] == "atp":
                                    for threat in result["data"]["threat"]:
                                        threat["threat_indicator"] = threat_indicator
                                        threat["threat_indicator_type"] = threat_indicator_type
                                        result_data= json.dumps(threat)
                                        event = helper.new_event(source=result["params"]["src"], index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                        ew.write_event(event)

                                elif result["params"]["src"] == "malware_analysis":
                                    if "details" in result["data"].keys():
                                        if "detected_communicating_samples" in result["data"]["details"].keys():
                                            for malware_analysis in result["data"]["details"]["detected_communicating_samples"]:
                                                malware_analysis["threat_indicator"] = threat_indicator
                                                malware_analysis["threat_indicator_type"] = threat_indicator_type
                                                result_data= json.dumps(malware_analysis)
                                                event = helper.new_event(source="detected_communicating_samples", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                                ew.write_event(event)
    
                                        if "detected_downloaded_samples" in result["data"]["details"].keys():
                                            for malware_analysis in result["data"]["details"]["detected_downloaded_samples"]:
                                                malware_analysis["threat_indicator"] = threat_indicator
                                                malware_analysis["threat_indicator_type"] = threat_indicator_type
                                                result_data= json.dumps(malware_analysis)
                                                event = helper.new_event(source="detected_downloaded_samples", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                                ew.write_event(event)
    
                                        if "detected_urls" in result["data"]["details"].keys():
                                            for malware_analysis in result["data"]["details"]["detected_urls"]:
                                                malware_analysis["threat_indicator"] = threat_indicator
                                                malware_analysis["threat_indicator_type"] = threat_indicator_type
                                                result_data= json.dumps(malware_analysis)
                                                event = helper.new_event(source="detected_urls", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                                ew.write_event(event)
                                
                                elif result["params"]["src"] == "malware_analysis_v3":
                                    if "data" in result["data"].keys():
                                        if "attributes" in result["data"]["data"].keys():
                                            if "categories" in result["data"]["data"]["attributes"].keys():
                                                categories = result["data"]["data"]["attributes"]["categories"]
                                                categories["threat_indicator"] = threat_indicator
                                                categories["threat_indicator_type"] = threat_indicator_type
                                                result_data= json.dumps(categories)
                                                event = helper.new_event(source="categories", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                                ew.write_event(event)
                                            if "last_analysis_results" in result["data"]["data"]["attributes"].keys():
                                                for last_analysis_result in result["data"]["data"]["attributes"]["last_analysis_results"]:
                                                    if isinstance(last_analysis_result, dict):
                                                        last_analysis_result["threat_indicator"] = threat_indicator
                                                        last_analysis_result["threat_indicator_type"] = threat_indicator_type
                                                        result_data= json.dumps(last_analysis_result)
                                                        event = helper.new_event(source="last_analysis_result", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                                        ew.write_event(event)
                                            if "last_analysis_stats" in result["data"]["data"]["attributes"].keys():
                                                last_analysis_stats = result["data"]["data"]["attributes"]["last_analysis_stats"]
                                                last_analysis_stats["threat_indicator"] = threat_indicator
                                                last_analysis_stats["threat_indicator_type"] = threat_indicator_type
                                                result_data= json.dumps(last_analysis_stats)
                                                event = helper.new_event(source="last_analysis_stats", index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                                ew.write_event(event)  
                                    
                                elif result["params"]["src"] == "pdns":
                                    for pdns in result["data"]["items"]:
                                        pdns["threat_indicator"] = threat_indicator
                                        pdns["threat_indicator_type"] = threat_indicator_type
                                        result_data= json.dumps(pdns)
                                        event = helper.new_event(source=result["params"]["src"], index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                        ew.write_event(event)
                                        
                                elif result["params"]["src"] == "isight":
                                    if "response" in result["data"].keys() and result["data"]["match"] == True:
                                        for isight in result["data"]["response"]:
                                            isight["threat_indicator"] = threat_indicator
                                            isight["threat_indicator_type"] = threat_indicator_type
                                            if "details" in result["data"]["response"]:
                                                if "threatDetail" in result["data"]["response"]["details"]:
                                                    isight["details"].pop("threatDetail")
                                            result_data= json.dumps(isight)
                                            event = helper.new_event(source=result["params"]["src"], index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                            ew.write_event(event)

                                else:
                                    result["data"]["threat_indicator"] = threat_indicator
                                    result["data"]["threat_indicator_type"] = threat_indicator_type
                                    result_data= json.dumps(result["data"])
                                    event = helper.new_event(source=result["params"]["src"], index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data = result_data)
                                    ew.write_event(event)

            searchquery_oneshot_update = "|makeresults | eval threat_indicator=\"" + threat_indicator + "\" | eval enriched=1 | outputlookup botdc_distinct_threat_indicators append=true createinapp=true"
            oneshotsearch_update_results = service.jobs.oneshot(searchquery_oneshot_update, **kwargs_oneshot)

        helper.log_info("Completed an Infoblox Dossier Search for "+ threat_indicator)
