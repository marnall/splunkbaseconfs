# encoding = utf-8

#Remove lines for debugging if not needed.
# import os
# import sys
# sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
# import splunk_debug as dbg
# dbg.enable_debugging(timeout=25)
#End of debugging code

from cyera_utils import collect_events_common, validate_input

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

def collect_events(helper, ew):
    """
    Collect events from the Cyera API.
    """
    collect_events_common(helper, ew, "events", "cyera:events")

def main(helper, ew):
    """
    Main entry point for the module.
    """
    collect_events(helper, ew)
