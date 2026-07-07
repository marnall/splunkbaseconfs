
# encoding = utf-8

import os
import sys
import time
import datetime
import importlib

def get_park_config(helper):
    park_input = helper.get_arg('theme_park')
    selector = {
        "magic_kingdom": "disney.MagicKingdom",
        "epcot" : "disney.Epcot",
        "hollywood_studios" : "disney.HollywoodStudios",
        "animal_kingdom" : "disney.AnimalKingdom",
        "disneyland" : "disney.DisneyLand",
        "universal_studios_florida" : "universal.UniversalStudiosFlorida",
        "islands_of_adventure" : "universal.IslandsOfAdventure"
    }
    return selector.get(park_input, "unknown_park")

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    theme_park = definition.parameters.get('theme_park', None)

def collect_events(helper, ew):
    helper.log_info("Starting data collection for park=%s" % helper.get_arg('theme_park'))
    park_module = get_park_config(helper)
    helper.log_info("Using module=%s" % park_module)

    park_mod_import = importlib.import_module('amusement.parks.%s' % park_module)

    park = getattr(park_mod_import, park_module.split('.')[1])
    park_handle = park()
    park_handle.splunk_config(helper, ew)
    park_handle.rides()

    helper.log_info("Completed data collection")
