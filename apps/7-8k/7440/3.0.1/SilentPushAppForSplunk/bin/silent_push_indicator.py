import import_declare_test

import sys
import time
import traceback
from silent_push_helpers.logger_manager import setup_logging
from silent_push_helpers.rest_helper import RestHelper
from silent_push_helpers.conf_helper import get_credentials, get_conf_file
from silent_push_helpers.event_ingestor import EventIngestor

from splunklib import modularinput as smi

class SilentPushIndicator(smi.Script):

    def __init__(self):
        super(SilentPushIndicator, self).__init__()

    def get_scheme(self):
        scheme = smi.Scheme('silent_push_indicator')
        scheme.description = 'Silent Push Indicator'
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
                'threat_intelligence_type',
                required_on_create=True,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'silent_push_feed_uuid',
                required_on_create=False,
            )
        )
        
        scheme.add_argument(
            smi.Argument(
                'silent_push_filter_profile',
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                'data_export_url',
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                'feed_scanner_url',
                required_on_create=False,
            )
        )

        scheme.add_argument(
            smi.Argument(
                'iofa_exports_url',
                required_on_create=False,
            )
        )
        
        return scheme

    def validate_input(self, definition):
        return

    def stream_events(self, inputs, ew):
        try:
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
            logger = setup_logging("ta_silent_push_indicator", input_name=input_name)
            splunk_rest_host_info = get_conf_file(
                file="silentpushappforsplunk_settings",
                session_key=session_key,
                stanza="splunk_rest_host"
            )
            collection_type = splunk_rest_host_info.get("collection_type")

            if collection_type == "index" and not input_items[1].get("index"):
                logger.error("message=validate_fields_error | Please add Index for this"
                            " input as collection type is set to index.")
                return

            logger.info("message=data_collection_start_execution | Data collection started.")

            account_info = get_credentials(
                session_key=session_key,
                account_name=input_items[1]['global_account']
            )
            input_items[1].update(account_info)

            # Check and exit for the deprecated modular input of type upload_file 
            data_collection_method = input_items[1].get("data_collection_method", "")
            if data_collection_method == "upload_file":
                logger.error(
                    "message=deprecated_collection_method | Support of Enrichment collection method"
                    " is deprecated in the input. You can delete this input."
                )
                exit(0)

            # Initialize rest helper and event ingestor
            silent_push_rest_helper = RestHelper(input_items[1], logger)
            event_ingestor = EventIngestor(input_items[1], ew, logger)

            # Get Threat Ranking data and ingest in Splunk
            threat_ranking_datas = silent_push_rest_helper.get_target_ranking_data()
            event_threat_ranking_count = event_ingestor.ingest_threat_ranking(threat_ranking_datas)
            logger.info(
                "message=events_collected | Total events for Threat Ranking"
                " ingested in Splunk are {}".format(event_threat_ranking_count)
            )

            total_time_taken = time.time() - start_time
            logger.info(
                "message=data_collection_end_execution | Data collection completed"
                " and total time taken: {}".format(total_time_taken)
            )
        except Exception:
            logger.error(traceback.format_exc())


if __name__ == '__main__':
    exit_code = SilentPushIndicator().run(sys.argv)
    sys.exit(exit_code)