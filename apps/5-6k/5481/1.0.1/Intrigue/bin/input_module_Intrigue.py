
# encoding = utf-8

import os
import sys
import time
import json
import datetime
import base64

def parseEntities(helper, items):
    parsed_items = []

    for item in items:

        # skip item if hidden
        if item["hidden"] == True:
            continue
        
        # we only want a subset of fields for the items
        clean_item = {}
        state = helper.get_check_point(item["id"])
        if state is None:
            # add default fields
            clean_item["uid"] = item["uid"]
            clean_item["id"] = item["id"].replace("Intrigue::Entity::", "")
            clean_item["type"] = item["type"].replace("Intrigue::Entity::", "")
            clean_item["name"] = item["name"]
            clean_item["collection"] = item["collection"]

            # add fields if present
            if "first_seen" in item:
                clean_item["first_seen"] = item["first_seen"]
            if "last_seen" in item:
                clean_item["last_seen"] = item["last_seen"]
            if "scoped" in item:
                clean_item["scoped"] = item["scoped"]
            if "scoped_reason" in item:
                clean_item["scoped_reason"] = item["scoped_reason"]
            if "issue_count" in item:
                clean_item["issue_count"] = int(float(item["issue_count"]))
            if "vuln_count" in item:
                clean_item["vuln_count"] = int(float(item["vuln_count"]))

            # add to parsed array and store as processed.
            parsed_items.append(clean_item)
            helper.save_check_point(item["id"], "Indexed")
    return parsed_items

def parseItems(helper, items):
    parsed_items = []

    for item in items:
        state = helper.get_check_point(item["id"])
        if state is None:
            parsed_items.append(item)
            helper.save_check_point(item["id"], "Indexed")
    
    return parsed_items


def getItems(helper, accessKey, secretKey, collectionName, itemType, startDate):

    baseUrl = "https://api.intrigue.io/api/collections/{}/export/{}/from_date/{}/".format(
        collectionName, 
        itemType,
        startDate
        )
    
    headers = {
    'INTRIGUE_ACCESS_KEY': accessKey,
    'INTRIGUE_SECRET_KEY': secretKey
    }

    items = []
    finished = False

    url = baseUrl # start url is base url

    while finished != True:
        response = helper.send_http_request(url,
                                        'GET',
                                        parameters=None,
                                        payload=None,
                                        headers=headers,
                                        cookies=None,
                                        verify=True,
                                        cert=None,
                                        timeout=None,
                                        use_proxy=False)
        responseJson = response.json()
        for item in responseJson['result']['items']:
            items.append(item)

        if responseJson['result']['more_results'] == True:
            urlAdd = base64.b64encode(json.dumps(responseJson['result']['last_evaluated_key']).encode('ascii'))
            url = baseUrl + urlAdd.decode('ascii')
        else:
            finished = True
            return items

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
    # This example accesses the modular input variable
    # collection_name = definition.parameters.get('collection_name', None)
    # item_type = definition.parameters.get('item_type', None)
    # date = definition.parameters.get('date', None)
    pass


def collect_events(helper, ew):
    loglevel = helper.get_log_level()
    # (log_level can be "debug", "info", "warning", "error" or "critical", case insensitive)
    helper.set_log_level(loglevel)
    opt_collection_name = helper.get_arg('collection_name')
    opt_item_type = helper.get_arg('item_type')
    opt_access_key = helper.get_arg("access_key")
    opt_secret_key = helper.get_arg("secret_key")
    opt_index = helper.get_arg("index")
    helper.log_debug("collected data from fields")

    # start date to use for collecting data
    startDate = "2020-01-01"

    helper.log_debug("Getting data from API...")
    items = getItems(helper, opt_access_key, opt_secret_key, opt_collection_name, opt_item_type, startDate)    
    
    helper.log_debug("Parsing items...")
    if opt_item_type == "entities":
        parsedItems = parseEntities(helper, items)
    else:
        parsedItems = parseItems(helper, items)
    

    
    helper.log_debug("Sending to splunk...")
    # To create a splunk event
    if len(parsedItems) > 0:
        event = helper.new_event(json.dumps(parsedItems), time=None, host=None,
                             index=opt_index, source=None, sourcetype=None, done=True, unbroken=True)
        ew.write_event(event)
        helper.log_debug("finished writing event")
    
    helper.log_debug("finished run")
