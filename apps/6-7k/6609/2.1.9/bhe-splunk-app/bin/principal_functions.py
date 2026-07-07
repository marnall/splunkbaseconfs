#!/usr/bin/env python
import datetime
import json
from splunklib.modularinput import *

def create_finding_record(path_details, finding, timestamp, stanza):

    e_timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')
    first_seen_ts = datetime.datetime.strptime(finding['First Seen'], '%Y-%m-%dT%H:%M:%S.%fZ')
    # Create generic record
    path_record = {
            "timestamp": str(e_timestamp),
            "data_type": "finding_export",
            "domain_id": path_details.domain_id,
            "domain_name": path_details.domain_name,
            "path_id": path_details.id,
            "path_title": path_details.title,
            "first_seen": str(first_seen_ts)
        }

    # Populate generic record and insert
    if (path_record['path_id'].startswith('LargeDefault')):
        path_record['group'] = finding['Group']
        path_record['principal'] = finding['Principal']
        
    elif 'Tier Zero Principal' in finding:
        path_record['non_tier_zero_principal'] = finding['Non Tier Zero Principal']
        path_record['tier_zero_principal'] = finding['Tier Zero Principal']
        
    else:
        path_record['user'] = finding['User']

    # Convert Path Record to JSON
    json_event = json.dumps(path_record)

    # Create Event Record
    event = Event(time = '%.3f' % e_timestamp.timestamp())
    event.stanza = stanza
    event.data = json_event
    return event
     

def create_tier0_record(t0object, domains, timestamp, stanza):

    e_timestamp = datetime.datetime.strptime(timestamp, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Create generic record
    temp_t0_rec = {
            "timestamp": str(e_timestamp),
            "data_type": "t0_export",
            "name": t0object['label'],
            "object_Id": t0object['objectId'],
            "type": t0object['kind'],
            "domain_name": None,
            "domain_id": None
        }
    rec_type = temp_t0_rec['type']
    # If to avoid processing Meta or Base object types
    if not(rec_type == 'Meta' or rec_type == 'Base' or rec_type == 'ADLocalGroup' or rec_type == 'ADLocalUser'):

        if rec_type.startswith('AZ'):
            temp_t0_rec['domain_id'] = t0object['properties']['tenantid']
            domain_id = t0object['properties']['tenantid']
            try:
                domain = next(x for x in domains if x['id'] == domain_id)
                temp_t0_rec['domain_name'] = '%s' % domain['name']
            except:
                pass
        elif rec_type == 'Domain':
            temp_t0_rec['domain_name'] = '%s' %temp_t0_rec['name']
            temp_t0_rec['domain_id'] = temp_t0_rec['object_Id']

        else:
            try:
                temp_t0_rec['domain_name'] = '%s' % t0object['properties']['domain']
            except:
                pass

            try:
                temp_t0_rec['domain_id'] = t0object['properties']['domainsid']
            except:
                pass
            
        #Convert T0 Record to JSON
        json_event = json.dumps(temp_t0_rec)

        #Create Splunk Event Type
        event = Event(time = '%.3f' % e_timestamp.timestamp())
        event.stanza = stanza
        event.data = json_event

        return event
