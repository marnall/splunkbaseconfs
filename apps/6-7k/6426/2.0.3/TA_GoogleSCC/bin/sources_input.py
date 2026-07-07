import import_declare_test
import sys
import json
import time
from datetime import datetime
import traceback
import TA_GoogleSCC_apiclient as gsa
from TA_GoogleSCC_consts import constants
from TA_GoogleSCC_utils import get_credentials

from splunklib import modularinput as smi
from TA_GoogleSCC_logger_manager import setup_logging

class SOURCES_INPUT(smi.Script):

    def __init__(self):
        super(SOURCES_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('sources_input')
        scheme.description = 'Source Input'
        scheme.use_external_validation = True
        scheme.streaming_mode_xml = True
        scheme.use_single_instance = False

        scheme.add_argument(
            smi.Argument(
                'name',
                title='Name',
                description='Name',
                required_on_create=True
            )
        )
        
        scheme.add_argument(	
            smi.Argument(	
                'google_scc_account',	
                required_on_create=True,	
            )	
        )
        
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        input_items = [{'count': len(inputs.inputs)}]
        for input_name, input_item in inputs.inputs.items():
            input_item['name'] = input_name
            input_items.append(input_item)
        
        input_name = input_items[1]['name']
        index_name = input_items[1]['index']
        logger = setup_logging("ta_googlescc_sources", input_name=input_name)

        account_name = input_items[1]['google_scc_account']
        meta_configs = self._input_definition.metadata
        session_key = meta_configs['session_key']
        account_info = get_credentials(session_key, account_name, logger)
        org = account_info.get('organization_id')
        # Validating account
        if not account_info:
            logger.error("message=account_error |" 
                         " Google SCC Account not found. Please configure the account first")
            return

        # Validating Interval
        interval = input_items[1]['interval']
        try:
            interval = int(interval)
        except:
            msg = "Interval must be an integer."
            logger.error("message=input_field_error |"
                         " Error occured while validating interval : {}".format(msg))
            return
        if int(interval) < 300 or int(interval) > 900:
            msg = "Interval must be positive Integer between 300 to 900."
            logger.error("message=input_field_error |"
                         " Error occured while validating interval : {}".format(msg))
            return

        now = datetime.now()
        start_date_time = now.strftime("%d/%m/%Y %H:%M:%S")
        logger.info("message=data_collection_started |"
                    " Data collection started at {}".format(start_date_time))
        start_time = time.time()
        try:

            client = gsa.init_google_scc_client(
                service_account_json=account_info['service_account_json'],
                credential_configuration_file=account_info['credential_configuration_file'],
                organization_id=account_info['organization_id'],
                logger=logger,
                timeout=constants.TIMEOUT_TIME,
                session_key=session_key,
            )
            responses = client.get_sources_data(
                logger=logger,
                parent="organizations/{0}".format(account_info['organization_id']),
                page_size=constants.DEFAULT_MAX_SOURCE_VALUE,
            )
        except Exception:
            logger.error("message=client_response_error |"
                         " Error occured while getting response for SCC client.\n{}".format(traceback.format_exc()))

        try:
            event_count = 0
            for response in responses:
                if response.get('sources'):
                    for res_obj in response.get('sources'):
                        try:
                            res_obj['orgID'] = org
                            event = smi.Event(
                                data=json.dumps(res_obj),
                                sourcetype='google:scc:sources',
                                index=index_name,
                                source="google_scc_sources_input"
                            )
                            ew.write_event(event)
                            event_count += 1
                        except Exception:
                            logger.error("message=data_ingestion_error |"
                                         " Error occured while writing event into splunk.\n{}".format(traceback.format_exc()))

            end_time = time.time()
            data_collection_time = end_time - start_time
            now = datetime.now()
            end_date_time = now.strftime("%d/%m/%Y %H:%M:%S")
            logger.info("message=data_collection_completed |"
                        " Data collection completed at {}".format(end_date_time))
            logger.info("message=data_collection_completed |"
                        " Time elapsed in Data ingestion : {}".format(data_collection_time))
            logger.info("message=data_collection_completed |"
                        " Number of events ingested : {}".format(event_count))
                        
        except Exception:
            logger.error("message=data_ingestion_error |"
                         " Error occured while data ingestion.\n{}".format(traceback.format_exc()))


if __name__ == '__main__':
    exit_code = SOURCES_INPUT().run(sys.argv)
    sys.exit(exit_code)