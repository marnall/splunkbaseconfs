import import_declare_test

import json
import sys
import time

from splunklib import modularinput as smi

from infoblox_helpers.logger_manager import setup_logging
from infoblox_helpers.rest_helper import RestHelper
from infoblox_helpers.conf_helper import get_credentials, get_conf_file
from infoblox_helpers.event_ingestor import EventIngestor


class InfoBloxInsights(smi.Script):
    def __init__(self):
        super(InfoBloxInsights, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('infoblox_insights')
        scheme.description = 'SOC Insights'
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
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
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
        logger = setup_logging("ta_infoblox_soc_insights", input_name=input_name)

        logger.info("message=data_collection_start_execution | Data collection stared.")

        account_info = get_credentials(
            session_key=session_key,
            account_name=input_items[1]['global_account']
        )
        input_items[1].update(account_info)
        
        # Initialize rest helper and event ingestor
        infoblox_rest_helper = RestHelper(input_items[1], logger)
        event_ingestor = EventIngestor(input_items[1], ew, logger)

        # Get insights data and ingest in Splunk
        insights_data = infoblox_rest_helper.get_insights()
        insights_event_count = event_ingestor.ingest_insights(insights_data)
        logger.info(
            "message=events_collected | Total events for Insights"
            " ingested in Splunk are {}".format(insights_event_count)
        )

        total_time_taken = time.time() - start_time
        logger.info(
            "message=events_collected | Total events ingested in Splunk"
            " are {}".format(insights_event_count)
        )
        logger.info(
            "message=data_collection_end_execution | Data collection completed"
            " and total time taken: {}".format(total_time_taken)
        )



if __name__ == '__main__':
    exit_code = InfoBloxInsights().run(sys.argv)
    sys.exit(exit_code)