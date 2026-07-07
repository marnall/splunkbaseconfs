
# encoding = utf-8

from pihole_helper import *
import pihole_constants as const


def validate_input(helper, definition):
   # We have nothing left to verify
    pass


def collect_events(helper, ew):
    # Get Credentials
    account = helper.get_arg('pihole_account')
    pihole_host = account['pihole_host']

    # Get Log Level
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)
    helper.log_info(f'log_level="{log_level}"')

    # Start ..
    params = {
        'summary': '',
        'type': '',
        'version': ''
    }
    event_name = 'system_summary'
    response = sendit(pihole_host, event_name, helper, params)

    if not response:
        return False

    # Build Event
    event = {}
    event['status'] = response['status']
    event['type'] = response['type']
    event['version'] = response['version']
    event['privacy_level'] = response['privacy_level']
    event['domains_on_blocklist'] = response['domains_being_blocked']
    event['unique_domains'] = response['unique_domains']
    event['gravity_updated'] = response['gravity_last_updated']['absolute']

    # Create Splunk Event
    splunk_event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(
    ), sourcetype=helper.get_sourcetype(), data=json.dumps(event), host=pihole_host)
    ew.write_event(splunk_event)

    # Checkpointer
    checkpointer(pihole_host, event_name, helper, set_checkpoint=True)
