# encoding = utf-8

import os
import sys
import time
import datetime
import requests
import time
import json

def validate_input(helper, definition):
    # This example accesses the modular input variable
    category = definition.parameters.get('category', None)
    sources = definition.parameters.get('sources', None)
    status = definition.parameters.get('status', None)
    days = definition.parameters.get('days', None)
    limit = definition.parameters.get('limit', None)

def collect_events(helper, ew):
    # Go through each input for this modular input
    opt_category = str(helper.get_arg('category'))
    opt_sources = helper.get_arg('sources')
    opt_status = str(helper.get_arg('status'))
    opt_days = str(helper.get_arg('days'))
    opt_limit = str(helper.get_arg('limit'))
    
    selSources = []
    
    if 'all' in opt_sources: 
        selSources = ""
    else:
        for s in range (len(opt_sources)):
            selSources.append(str(opt_sources[s]))
        
        selSources = str(selSources).strip("[]").replace("'", "").replace(" ", "")
    
    url = 'https://eonet.sci.gsfc.nasa.gov/api/v2.1/categories/'+ opt_category +'?source=' + selSources +'&status='+ opt_status +'&days='+ opt_days +'&limit='+ opt_limit
    
    dataJson = requests.get(url).text
    json_parsed = json.loads(dataJson)

    events = json_parsed['events']

    for evt in events:
        for src in evt['sources']:
            sources = src['url']
            
            for geo in evt['geometries']:
                dt = str(geo['date'])
                typ = str(geo['type'])
                coord = str(geo['coordinates']).strip('[]')
                title = evt['title']
                desc = evt['description']
                evtId = evt['id']
                
                for cat in evt['categories']:
                    category = cat['title']
                    
                    data =  dt + "|" + typ + "|" + coord + "|" + title + "|" + desc + "|" + evtId + "|" + category + "|" + sources
                        
                    event = helper.new_event(data, host=None, source='eonet_api', sourcetype='eonetdata', done=True, unbroken=True)
    
                    try:
                        ew.write_event(event)
                    except Exception as e:
                        raise e