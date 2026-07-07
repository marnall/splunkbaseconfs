import json
import sys
from datetime import datetime

from Send_to_Splunk import Post_to_Splunk
from Status_Code_Errors_Splunk import Status_Code_Errors

class Alerts():
    
    alerts_collection = []
    raw_id_list = []
    id_list = []
    alerts_id_total = 0
    reported_total = 0
    current_time = datetime.utcnow()
    meta_data = ''
    
    def get_alert_ids(updated_timestamp, stanza_checkpoint, chkpt_value, user_agent, log_label, falcon, proxy_settings, cs_base_url, ta_data, helper, ew):

        limit = 10000
        sort = "updated_timestamp.asc"
        #determine if this is an initial call or a follow on call - follow ons should be greater than or equal to try an account for events with the same timestamps
        if chkpt_value  == True:
            time_filter = f"updated_timestamp:>'{updated_timestamp}'"
        else:
            time_filter = f"updated_timestamp:>='{updated_timestamp}'"

        if 'all' not in ta_data['Products']:
            alert_filter = f"({time_filter})+(product:{ta_data['Products']})"
        else:
            alert_filter = f"{time_filter}"
        
        helper.log_debug(f"{log_label}: Filter for API details call is {alert_filter}")
        helper.log_info(f"{log_label}: Calling API for alert details")
        api_endpoint = 'GetQueriesAlertsV1'

        try:
            alert_id_response = falcon.command("GetQueriesAlertsV1", limit=limit, user_agent=user_agent, filter=alert_filter, sort=sort, proxy=proxy_settings, base_url=cs_base_url)
            status_code = str(alert_id_response['status_code'])
        except Exception as issue:
            helper.log_error(f"{log_label}: Unable to make contact with the CrowdStrike API endpoint -{api_endpoint}. The TA will now shutdown. Exception: {issue}")
            sys.exit()

        if status_code.startswith('2'):  
            helper.log_info(f"{log_label}: API call successful")      
            alert_id_body = alert_id_response ['body']
            alert_ids = alert_id_body['resources']
            helper.log_debug(f"{log_label}: API call details: {alert_id_body['meta']}")
            Alerts.reported_total = alert_id_body['meta']['pagination']['total']
            alert_id_count = len(alert_ids)
            
            #store original data into global variables
            if alert_id_count > 0:
                helper.log_info(f"{log_label}: There are alerts IDs to process")
                if Alerts.meta_data == '':
                    Alerts.meta_data = alert_id_body['meta']

                #account for the fact that if pagination takes place past 10k IDs that the same timestamp values maybe split
                removed_duplication =[]
                helper.log_info(f"{log_label}: There were {len(alert_ids)} returned for this query")
                helper.log_debug(f"{log_label}: Alert IDs: {alert_ids}")
                Alerts.raw_id_list.extend(alert_ids)
                for id in alert_ids:
                    if id in Alerts.id_list:
                        helper.log_debug(f"{log_label}: Dupicate id found - {id}")
                        removed_duplication.append(id)
                
                #eval the ids and remove any that have already been identified
                num_dups = len(removed_duplication)
                if num_dups > 0:
                    for id in removed_duplication:
                        alert_ids.remove(id)
                    helper.log_debug(f"{log_label}: {num_dups} duplications were removed")

                alert_id_count = len((alert_ids))
                Alerts.alerts_id_total = Alerts.alerts_id_total + alert_id_count
                Alerts.id_list.extend(alert_ids)
                helper.log_info(f"{log_label}: Current number of IDs identified is {alert_id_count}")

                Alerts.get_alert_details(falcon, limit, alert_ids, updated_timestamp, stanza_checkpoint, user_agent, log_label, proxy_settings, cs_base_url, ta_data, helper, ew )
            
            else:
                helper.log_info(f"{log_label}: There are no Alert IDs that currently meet the requirements, nothing to process")
                helper.log_info(f"{log_label}: The TA will now shutdown until the next collection interval")
                sys.exit()
        else:
            Status_Code_Errors.status_code_errors(alert_id_response, api_endpoint, log_label, helper, ew)

    def get_alert_details(falcon, limit, alert_ids, updated_timestamp, stanza_checkpoint, user_agent, log_label, proxy_settings, cs_base_url, ta_data, helper, ew):
        details_query_limit = 1000
        
        num_ids = len(alert_ids)
        id_collection = []

        helper.log_info(f"{log_label}: Beginning details collection for  {num_ids}")
        
        if num_ids > details_query_limit:
            helper.log_info(f"{log_label}: The number of IDs exceeds the maximum of the details endpoints, creating query groups")
            while num_ids != 0:
                helper.log_info(f"{log_label}: Creating alert ID groups: {len(id_collection)}")
                id_collection.append(alert_ids[:details_query_limit])
                del alert_ids[:details_query_limit]
                num_ids = len(alert_ids)
        elif num_ids > 0:
            helper.log_info(f"{log_label}: The number of IDs can be handled with a single details endpoint call")
            id_collection.append(alert_ids)
        else:
            helper.log_info(f"{log_label}: There are no IDs to collect details on - TA is shutting down")
            sys.exit()

        for id_list in id_collection:
            print(id_list)
            helper.log_info(f"{log_label}: Querying the details API for {len(id_list)} ids")
            ids = id_list
            api_endpoint='PostEntitiesAlertsV1'

            try:
                alert_details_response = falcon.command("PostEntitiesAlertsV1", limit=details_query_limit, ids=ids, base_url=cs_base_url, user_agent=user_agent, proxy_settings=proxy_settings)
            except Exception as issue:
                helper.log_error(f"{log_label}: Unable to make contact with the CrowdStrike API endpoint -{api_endpoint}. The TA will now shutdown. Exception: {issue}")
                sys.exit()
            
            status_code = str(alert_details_response['status_code'])
            
            if status_code.startswith('2'):
                alert_details = alert_details_response['body']['resources']
  
                helper.log_info(f"{log_label}: Details for {len(alert_details)} collected")

                Alerts.alerts_collection.extend(alert_details) 
                saved_checkpoint = Post_to_Splunk.send_to_splunk(alert_details, updated_timestamp, stanza_checkpoint, log_label, ta_data, helper, ew)

            else:
                api_endpoint = 'PostEntitiesAlertsV1'
                Status_Code_Errors.status_code_errors(alert_details_response, api_endpoint, log_label, helper, ew)
    
        #check the timestamp to see if it's within a minute of the start time to determine if another check should be made
        helper.log_info(f"{log_label}: Evaluating the need the check for additional queries ")

        alert_details = (sorted(Alerts.alerts_collection, key=lambda x: x['updated_timestamp']))
        updated_timestamp = alert_details[-1]['updated_timestamp']

        helper.log_info(f"{log_label}: Latest timestamp is {updated_timestamp}")
        helper.log_debug(f"{log_label}: Last reported total was is {Alerts.reported_total}")
        
        #check to see if the updated timestamp is within a minute of the start time
        updated_timestamp2 = updated_timestamp[:23]   
        timestamp_check = datetime.fromisoformat(updated_timestamp2)
        c = Alerts.current_time - timestamp_check
        minutes = c.total_seconds() / 60
        if minutes > 1: #and Alerts.reported_total > limit:
            helper.log_info(f"{log_label}: Additional query/s will be made")
            chkpt_value = False
            Alerts.get_alert_ids(updated_timestamp, stanza_checkpoint, chkpt_value, user_agent, log_label, falcon, proxy_settings, cs_base_url, ta_data, helper, ew)
        else:
            helper.log_info(f"{log_label}: Additional query/s are not required")

        total_details = len(Alerts.alerts_collection)
        total_ids = len(Alerts.id_list)
        totals_match = (total_ids == total_details)
        helper.log_info(f"{log_label}: Total number of collectable IDs matches total number of collected details is {totals_match}.  {total_ids} | {total_details} ")
        helper.log_info(f"{log_label}: Last saved checkpoint was {saved_checkpoint}")
        helper.log_info(f"{log_label}: The TA has completed data collection and is shutting down")

        sys.exit()