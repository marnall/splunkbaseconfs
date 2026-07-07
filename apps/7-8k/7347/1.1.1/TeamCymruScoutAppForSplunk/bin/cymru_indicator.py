import import_declare_test

import sys
import time
from cymru_helpers.logger_manager import setup_logging
from cymru_helpers.rest_helper import RestHelper
from cymru_helpers.conf_helper import get_credentials, get_conf_file
from cymru_helpers.event_ingestor import EventIngestor

from splunklib import modularinput as smi

class CYMRU_INDICATOR(smi.Script):

    def __init__(self):
        super(CYMRU_INDICATOR, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('cymru_indicator')
        scheme.description = 'Team Cymru Scout Indicator'
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
                'global_account',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'api_type',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'indicator_type',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'indicators',
                required_on_create=True,
            )
        )
        
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        start_time = time.time()
        input_items = [{'count': len(inputs.inputs)}]
        meta_configs = self._input_definition.metadata
        session_key = meta_configs['session_key']
        for input_name, input_item in inputs.inputs.items():
            input_item['stanza_name'] = input_name
            input_item['name'] = input_name.split('://')[1]
            input_item['session_key'] = session_key
            input_items.append(input_item)

        input_name = input_items[1]['name']
        logger = setup_logging("ta_team_cymru_scout_indicator", input_name=input_name)
        splunk_rest_host_info = get_conf_file(
            file="teamcymruscoutappforsplunk_settings",
            session_key=session_key,
            stanza="splunk_rest_host"
        )
        collection_type = splunk_rest_host_info.get("collection_type")

        if collection_type == "index" and not input_items[1].get("index"):
            logger.error("Please add Index for this input as collection type is set to index.")
            return
        
        
        logger.info("Data collection stared.")

        account_info = get_credentials(
            session_key=session_key,
            account_name=input_items[1]['global_account']
        )
        input_items[1].update(account_info)
        cymru_rest_helper = RestHelper(input_items[1], logger)
        indicator_datas = cymru_rest_helper.get_data()
        
        event_ingestor = EventIngestor(input_items[1], ew, logger)
        event_count = event_ingestor.ingest(indicator_datas)

        total_time_taken = time.time() - start_time
        logger.info("Total events ingested in Splunk are {}".format(event_count))
        logger.info("Data collection completed and total time taken: {}".format(total_time_taken))


if __name__ == '__main__':
    exit_code = CYMRU_INDICATOR().run(sys.argv)
    sys.exit(exit_code)