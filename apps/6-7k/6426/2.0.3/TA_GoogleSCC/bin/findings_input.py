import import_declare_test
import sys
import json
import time
from datetime import datetime
import traceback
import TA_GoogleSCC_apiclient as gsa
from TA_GoogleSCC_consts import constants
from TA_GoogleSCC_utils import get_credentials, get_project_id

from splunklib import modularinput as smi
from TA_GoogleSCC_logger_manager import setup_logging

class FINDINGS_INPUT(smi.Script):

    def __init__(self):
        super(FINDINGS_INPUT, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('findings_input')
        scheme.description = 'Findings Input'
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
        
        scheme.add_argument(
            smi.Argument(
                'findings_subscription_id',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'maximum_fetching',
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
        logger = setup_logging("ta_googlescc_findings", input_name=input_name)

        account_name = input_items[1]['google_scc_account']
        meta_configs = self._input_definition.metadata
        session_key = meta_configs['session_key']
        account_info = get_credentials(session_key, account_name, logger)

        interval = input_items[1]['interval']
        maximum_fetching = input_items[1]['maximum_fetching']
        findings_subscription_name = input_items[1]['findings_subscription_id']
        findings_subscription_split = findings_subscription_name.split("/")
        project_id = findings_subscription_split[1]
        findings_subscription_id = findings_subscription_split[3]

       # Validating account
        if not account_info:
            logger.error("message=account_error |" 
                         " Google SCC Account not found. Please configure the account first")
            return

        # Validating Interval
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

        # Validating Maximum Fetching
        try:
            maximum_fetching = int(maximum_fetching)
        except:
            msg = "Maximum Fetchings must be an integer."
            logger.error("message=input_field_error |"
                         " Error occured while validating Maximum Fetchings : {}".format(msg))
            return
        if int(maximum_fetching) < 500 or int(maximum_fetching) > 5000:
            msg = "Maximum Fetchings must be positive Integer between 500 to 5000."
            logger.error("message=input_field_error |"
                         " Error occured while validating Maximum Fetchings : {}".format(msg))
            return
        
        service_account = account_info['service_account_json']
        project_ID = get_project_id(logger, project_id, service_account)
        org = account_info.get('organization_id')
        # Validating project id and assets subscription id
        scc_findings_sub_client = gsa.init_google_pubsub_client(
                project_id=project_ID,
                subscription_id=findings_subscription_id,
                service_account_json=account_info['service_account_json'],
                credential_configuration_file=account_info['credential_configuration_file'],
                logger=logger,
                organization_id=account_info['organization_id'],
                timeout=constants.CONFIG_TIMEOUT,
                session_key=session_key,
        )
        try:
            subscription = "projects/{0}/subscriptions/{1}".format(
                    project_ID, findings_subscription_id
            )
            body = {"max_messages": 1, "return_immediately": True}
            validate = scc_findings_sub_client.service.projects().subscriptions().pull(
                    subscription=subscription,
                    body=body
            )
            data = validate.execute()
        except Exception:
            msg = "Please enter valid Project ID or Assets Subscription ID."
            logger.error("message=account_error | {}\n{}".format(msg, traceback.format_exc()))
            sys.exit()

        now = datetime.now()
        start_date_time = now.strftime("%d/%m/%Y %H:%M:%S")
        logger.info("message=data_collection_started |"
                    " Data collection started at {}".format(start_date_time))
        
        start_time = time.time()
        try:
            logger.info("message=initialized_client | Intialized PubSub client")
            event_count = gsa.get_findings_data(logger, maximum_fetching, index_name, ew, org, scc_findings_sub_client)

            end_time = time.time()
            data_collection_time = end_time - start_time
            now = datetime.now()
            end_date_time = now.strftime("%d/%m/%Y %H:%M:%S")
            logger.info("message=data_collection_completed |"
                        " Data collection completed at {}".format(end_date_time))
            logger.info("message=data_collection_completed |"
                        " Time elapsed in Data ingestion : {}".format(data_collection_time))
            logger.info("message=data_collection_completed |"
                        " Total events ingested: {}".format(event_count))
        except Exception:
            logger.error("message=data_fetching_error |"
                         " Error occured while getting response for PUBSUB client.\n{}".format(traceback.format_exc()))


if __name__ == '__main__':
    exit_code = FINDINGS_INPUT().run(sys.argv)
    sys.exit(exit_code)