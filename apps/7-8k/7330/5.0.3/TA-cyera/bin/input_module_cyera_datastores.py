# encoding = utf-8



#import os

#import sys

#Remove lines for debugging if not needed.

#sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))

#import splunk_debug as dbg

#dbg.enable_debugging(timeout=25)



from cyera_utils import collect_events_common, validate_input as common_validate_input



'''

    IMPORTANT

    Edit only the validate_input and collect_events functions.

    Do not edit any other part in this file.

    This file is generated only once when creating the modular input.

'''

'''

# For advanced users, if you want to create single instance mod input, uncomment this method.

def use_single_instance_mode():

    return True

'''


def validate_input(helper, definition):
    """
    Validate input configuration for datastores.
    Ensures that when retrieve_all_data is enabled, interval is at least 86400 seconds (1 day).
    """
    # Call common validation first
    common_validate_input(helper, definition)
    
    # Get the parameters
    retrieve_all_data = definition.parameters.get('retrieve_all_data_every_time')
    interval = definition.parameters.get('interval')
    
    # Check if retrieve_all_data is enabled and interval is set
    # Note: Splunk checkbox returns "0" (string) when unchecked, which is truthy in Python
    if str(retrieve_all_data).strip() == '1' and interval:
        try:
            interval_seconds = int(interval)
            if interval_seconds < 86400:
                raise ValueError(
                    "When 'Retrieve All Data Every Time' is enabled, interval must be at least 86400 seconds (1 day). "
                    f"Current interval: {interval_seconds} seconds."
                )
        except ValueError as e:
            if "invalid literal" in str(e):
                raise ValueError(f"Invalid interval value: {interval}")
            raise


def collect_events(helper, ew):

    """

    Collect datastore events.

    """

    collect_events_common(helper, ew, "datastores", "cyera:datastores")



def main(helper, ew):

    """

    Main entry point for the module.

    """

    collect_events(helper, ew)
