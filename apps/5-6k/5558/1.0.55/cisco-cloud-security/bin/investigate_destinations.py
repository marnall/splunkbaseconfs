# encoding = utf-8
from __future__ import print_function

import sys
from os.path import dirname, abspath
sys.path.append(dirname(abspath(__file__)))

import json
import splunklib.client as client
from service.app_kvstore_service import KVStoreService
from logger import Logger
import re
from validator import cummulative_validator, date_validator
from reporting_api_client import ReportingAPIClient
from exceptions import ReportingAPIClientException, InvestigateDestinationException


oauth_settings = None
investigate_settings = None

def validator(arg, name):
    if not cummulative_validator(arg):
        raise Exception('KV store data [{0}] validation failed'.format(name))
    return arg

def getCategory(rsp):
    flag_con_cat = 0
    if isinstance(rsp,list):
        sec_cat_list = list(set([ele for obj in rsp for ele in obj['securityCategories']])) #for removing duplicate security categories set is used, which gives unordered collection
        flag_con_cat = 1
    elif isinstance(rsp,dict):
        sec_cat_list = rsp["security_categories"]
    else:
        raise Exception('Invalid API response from category search for a destination')
    #priority is security categories, if the values in security categories is less than 5 then we go for content categories
    if len(sec_cat_list)<5:
        if flag_con_cat==1:
            con_cat_list = list(set([ele for obj in rsp for ele in obj['contentCategories']]))
        else:
            con_cat_list = rsp["content_categories"]
        vl = 5-len(sec_cat_list)
        sec_cat_list = sec_cat_list+con_cat_list[0:vl]
    elif len(sec_cat_list)>5:
        sec_cat_list = sec_cat_list[:5]
    return ','.join(sec_cat_list)

def main():
    try:
        Logger().info("AL: investigate_destinations: execution started")
        if len(sys.argv) > 1 and sys.argv[1] == "--execute":
            main_res = json.loads(sys.stdin.read())
            configur = main_res['configuration']
            org_id = validator(configur['org_id'], 'org_id')
            field = validator(configur['field_name'], 'field_name')
            field_type = validator(configur['field_type'], 'field_type')
            if field_type not in ['domain','url','ip']:
                raise Exception('field_type is not allowed')
            payload_res = main_res['result']
            if field in list(payload_res.keys()) and 'splunk_server' in list(payload_res.keys()):
                Logger().info("AL: investigate_destinations: field found in payload")
                session_token = main_res['session_key']
                api_client = ReportingAPIClient(session_token, org_id=org_id)
                global investigate_settings
                global oauth_settings
                if investigate_settings is None:
                    investigate_settings = KVStoreService('investigate_settings', session_token)
                investigate_settings_data = json.loads(investigate_settings.query_items('investigate_settings', session_token, {
                    "orgId": org_id
                }))
                if len(investigate_settings_data)==0:
                    raise InvestigateDestinationException(error_code=400, error_msg="Investigate Index is not configured")
                if not oauth_settings:
                    oauth_settings = KVStoreService('oauth_settings', session_token)
                    oauth_settings = json.loads(oauth_settings.query_items('oauth_settings', session_token, {
                        "orgId": org_id,
                        "status": "active"
                    }))
                    if len(oauth_settings) == 0:
                        Logger().error("Message: oauth settings are not configured")
                        raise InvestigateDestinationException(error_code=400, error_msg="oauth settings are not configured")
                    for obj in oauth_settings:
                        if obj['status'] == 'active':
                            base_url = obj['baseURL']
                            break
                if not base_url:
                    raise InvestigateDestinationException(error_code=400, error_msg="oauth settings are not configured")
                headers = None
                investigate_index = None
                for obj in investigate_settings_data:
                    if obj['status'] == 'active':
                        investigate_index = obj['index']
                        break
                if not investigate_index:
                    raise InvestigateDestinationException(error_code=400, error_msg="Investigate index is not configured")
                destination_req = str(payload_res[field])
                if destination_req.endswith("."):
                    destination_req = destination_req[:-1]

                destination_req_api = ''
                if field_type == 'url':
                    m = re.search('https?://([A-Za-z_0-9.-]+).*', destination_req)
                    if m:
                        destination_req_api = m.group(1)
                else:
                    destination_req_api = destination_req
                path = f'/investigate/v2/domains/risk-score/{str(destination_req_api)}?count_total=false'
                risk_response_body = api_client.send_request(path=path, method='get', headers=headers)
                risk_response_body = f'"{risk_response_body.json()[u"risk_score"]}"'
                
                if 'category' in list(payload_res.keys()):
                    category_req = payload_res['category']
                else:
                    if field_type in ['domain','url']:
                        path = f'/investigate/v2/domains/categorization/{str(destination_req_api)}?showLabels'
                        category_response_body = api_client.send_request(path=path, method='get', headers=headers)
                        response_obj = category_response_body.json()[destination_req_api] #response in the form of dictionary is expected for this API
                        category_req = getCategory(response_obj)
                    else:
                        path = f'/investigate/v2/pdns/ip/{str(destination_req_api)}?'
                        category_response_body = api_client.send_request(path=path, method='get', headers=headers)
                        response_list = category_response_body.json()["records"] #response in the form of list is expected for this API
                        category_req = getCategory(response_list)

                category_req = category_req if category_req!='' else "NULL"
                category_req = '"{0}"'.format(str(category_req))
                destination_req = '"{0}"'.format(str(destination_req))
                org_id_req = '"{0}"'.format(str(org_id))
                host_req = payload_res['splunk_server']
                splunkservice = client.connect(host="localhost", token=session_token)
                indexes = splunkservice.indexes
                for ele in indexes:
                    if str(ele.name)==str(investigate_index):
                        ele.submit('{0},{1},{2},{3}'.format(str(destination_req), str(risk_response_body), str(category_req), str(org_id_req)), sourcetype="cisco:cloud_security:investigated", source="cloud_security_investigate", host=host_req)
                        break

        Logger().info("AL: investigate_destinations: execution completed")
    except ReportingAPIClientException as e:
            Logger().error("AL: investigate_destinations, Exception : {0}".format(str(e.error_msg)))
            return {'payload': {"message": str(e.error_msg)}, "status": e.error_code}
    except Exception as e:
        Logger().error("AL: investigate_destinations: Exception: {0}".format(str(e)))


if __name__ == '__main__':
    main()
