# encoding = utf-8
from __future__ import print_function

import json
import sys
from os.path import dirname, abspath
import re
import splunklib.client as client
from logger import Logger
from service.app_kvstore_service import KVStoreService
from enums import Collections, InvestigateAPIS
from exceptions import DestinationReportException
from investigate_apis import InvestigateReports
from validator import cummulative_validator

sys.path.append(dirname(abspath(__file__)))
oauth_settings = None

def validator(arg, name):
    if not cummulative_validator(arg):
        raise Exception('KV store data [{0}] validation failed'.format(name))
    return arg

def dataset_validator(datasets, field_type):
    '''Removes the datasets which are not specfic to the configured field type of Report.
    '''
    if field_type == 'domain':
        return [dataset for dataset in datasets if dataset in InvestigateAPIS.DOMAIN_URIS.value.keys()]
    if field_type == 'ip':
        return [dataset for dataset in datasets if dataset in InvestigateAPIS.IP_URIS.value.keys()]
    if field_type == 'url':
        return [dataset for dataset in datasets if dataset in InvestigateAPIS.URL_URIS.value.keys()]
    if field_type == 'hash':
        return [dataset for dataset in datasets if dataset in InvestigateAPIS.HASH_URIS.value.keys()]


def save_to_kv_store(collection, event, token, report_name, destination, org_id: str):
    try:
        service = client.connect(host='localhost', token=token)
        service.namespace['owner'] = 'Nobody'
        kv_collection = KVStoreService(collection, token)
        prev_data = json.loads(kv_collection.query_items(collection, token, query_conditions={'Report_name':report_name, 'Dest':destination, 'orgId':org_id}))
        if collection not in service.kvstore:
            collection = service.kvstore.create(collection)
        else:
            collection = service.kvstore[collection]
        if len(prev_data) == 0:
            collection.data.insert(event)
        else:
            key = prev_data[-1]["_key"]
            collection.data.update(key, event)
    
    except Exception as e:
        Logger().error("AL: Save to KV store: Exception: {0}".format(str(e)))


def main():
    try:
        Logger().info("AL: investigate_reports: execution started")
        if len(sys.argv) > 1 and sys.argv[1] == "--execute":
            main_res = json.loads(sys.stdin.read())
            configur = main_res['configuration']
            org_id = validator(configur['org_id'], 'org_id')
            report_name = validator(configur['report_name'], 'report_name')
            field = validator(configur['field_name'], 'field_name')
            field_type = validator(configur['field_type'], 'field_type')
            datasets = [value for key, value in configur.items() if key.startswith('datasets')]
            if not datasets:
                raise DestinationReportException(error_code=400, error_msg="Datasets are not selected")
            if field_type not in ['domain', 'url', 'ip', 'hash']:
                raise DestinationReportException(error_code=400, error_msg="field_type is not allowed")
            datasets = dataset_validator(datasets, field_type)
            if not datasets:
                raise DestinationReportException(error_code=400, error_msg=f'The selected datasets are not related to {field_type} field_type, edit or configure a Report')
            payload_res = main_res['result']
            session_token = main_res['session_key']
            alert_inputs = KVStoreService('alert_inputs', session_token)
            alert_inputs_data = json.loads(alert_inputs.query_items('alert_inputs', session_token, query_conditions={'report_name':report_name, 'orgId':org_id}))
            if len(alert_inputs_data) != 0:
                prev_input = alert_inputs_data[-1]
                key = prev_input["_key"]
                alert_inputs.update_item_by_key('alert_inputs', key, session_token,
                                                {'report_name' : report_name,
                                                 'field_type' : field_type,
                                                 'datasets' : datasets,
                                                'orgId' : org_id
                                                })
            else:
                alert_inputs.insert_record('alert_inputs', session_token,
                                           {'report_name' : report_name,
                                            'field_type' : field_type,
                                            'datasets' : datasets,
                                            'orgId' : org_id
                                           })

            if field in list(payload_res.keys()) and 'splunk_server' in list(payload_res.keys()):
                global oauth_settings
                if not oauth_settings:
                    oauth_settings = KVStoreService('oauth_settings', session_token)
                    oauth_settings = json.loads(oauth_settings.query_items('oauth_settings', session_token,{
                        'orgId': org_id,
                        'status': 'active'
                    }))
                    if len(oauth_settings) == 0:
                        Logger().error("Message: oauth settings are not configured")
                        raise DestinationReportException(error_code=400, error_msg="oauth settings are not configured.")
                    for obj in oauth_settings:
                        if obj['status'] == 'active':
                            base_url = obj['baseURL']
                            break
                if not base_url:
                    raise DestinationReportException(error_code=400, error_msg="oauth settings are not configured.")
                collection = Collections.COLLECTION.value
                collection = collection[field_type]
                destination = str(payload_res[field])
                if destination.endswith("."):
                    destination = destination[:-1]
                if field_type == 'url':
                    m = re.search('https?://([A-Za-z_0-9.-]+).*', destination)
                    if m:
                        destination = m.group(1)
                report = InvestigateReports(session_token, org_id)
                response_dict = dict()
                try:
                    for dataset in datasets:
                        dataset_response = getattr(report, report.process_uris[dataset])(destination, field_type)
                        if dataset_response:
                            response_dict = report.merge_response(response_dict, dataset_response)
                    if response_dict:
                        response_dict['Dest'] = destination
                        response_dict['Field_type'] = field_type
                        response_dict['Report_name'] = report_name
                        response_dict['orgId'] = org_id
                        response_dict = json.dumps(response_dict)
                        save_to_kv_store(collection, response_dict, session_token, report_name, destination, org_id)
                    else:
                        Logger().error(f"AL: Failed to Enrich the destination. \
                            Investigate API might be down check health status for more information.")

                except Exception as e:
                    Logger().error(f"AL: investigate_reports: Exception while investigating destination {destination} : {str(e)} ")
                
        Logger().info("AL: investigate_reports: execution completed")
    except Exception as e:
        Logger().error("AL: investigate_reports: Exception: {0}".format(str(e)))


if __name__ == '__main__':
    main()
