# encoding = utf-8

import os
import sys
import time
import datetime
import ta_google_search_for_splunk_declare
import json
import csv

from google_search import search
from lookup_reader import get_dorks

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # lookup_file = definition.parameters.get('lookup_file', None)
    # google_tld = definition.parameters.get('google_tld', None)
    # google_language = definition.parameters.get('google_language', None)
    # maximum_results = definition.parameters.get('maximum_results', None)
    pass


def collect_events(helper, ew):
    # The following examples get the arguments of this input.
    # Note, for single instance mod input, args will be returned as a dict.
    # For multi instance mod input, args will be returned as a single value.
    google_query = helper.get_arg("google_query", None)
    google_tld = helper.get_arg("google_tld", None)
    google_language = helper.get_arg("google_language", None)
    maximum_results = helper.get_arg("maximum_results", None)

    #Set up logging
    loglevel = helper.get_log_level()
    helper.set_log_level(loglevel)

    iter = search(helper,google_query, tld=google_tld, lang=google_language, stop=int(maximum_results))
    if iter == None:
        helper.log_error(f"Failed to get events for input {helper.get_input_stanza_names()}.")
        pass
    
    for link in iter:
        event = helper.new_event(
            json.dumps({
                "url": link,
                "rule_name":helper.get_input_stanza_names()
            }),
            index=helper.get_output_index(),
            source=helper.get_input_type(),
            sourcetype=helper.get_sourcetype(),
        )
        ew.write_event(event)