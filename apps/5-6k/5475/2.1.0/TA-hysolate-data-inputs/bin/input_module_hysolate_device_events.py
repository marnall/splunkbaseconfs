from ta_hysolate_data_inputs_common_logic import hysolate_collect_events

API_PATH = 'device-events'

def validate_input(helper, definition): # pylint: disable=unused-argument
    pass

def collect_events(helper, event_writer):
    hysolate_collect_events(helper, event_writer, API_PATH)
