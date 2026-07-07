import import_declare_test # noqa

import sys

from splunklib import modularinput as smi
from cymru_helpers.rest_helper import RestHelper
from cymru_helpers.logger_manager import setup_logging
from cymru_helpers.conf_helper import get_credentials
import time
import traceback


class cymru_feed_api(smi.Script):
    """Class for API data input."""

    def __init__(self):
        """Init method for class."""
        super(cymru_feed_api, self).__init__()

    def get_scheme(self):
        """Method to get scheme."""
        scheme = smi.Scheme('cymru_feed_api')
        scheme.description = 'Team Cymru Feed Indicator'
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
                'account',
                required_on_create=True,
            )
        )
        scheme.add_argument(
            smi.Argument(
                'api_type',
                required_on_create=True,
            )
        )
        return scheme

    def validate_input(self, definition: smi.ValidationDefinition):  # noqa
        return

    def stream_events(self, inputs: smi.InputDefinition, ew: smi.EventWriter):
        """Method to stream events."""
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
        logger = setup_logging("ta_team_cymru_feed_api", input_name=input_name)
        logger.info("Data collection started.")
        account_info = get_credentials(
            session_key=session_key,
            account_name=input_items[1]['account']
        )
        input_items[1].update(account_info)

        try:
            cymru_rest_helper = RestHelper(input_items[1], logger)
            event_counter = cymru_rest_helper.get_and_write_data_api(ew)

            total_time_taken = time.time() - start_time
            logger.info("Total events Downloaded in Splunk are {}".format(event_counter))
            logger.info("Data collection completed and total time taken: {}".format(total_time_taken))

        except Exception as e:
            logger.error(
                "Error occured while collecting data. Error={}, Traceback={}".format(e, traceback.format_exc())
            )


if __name__ == '__main__':
    exit_code = cymru_feed_api().run(sys.argv)
    sys.exit(exit_code)
