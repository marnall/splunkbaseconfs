#!/usr/bin/env python
import datetime

from splunklib.modularinput import *

def get_splunk_attack_path_event(event_data, stanza, domain):
    id = event_data["id"]
    path_title = event_data["path_title"]
    path_type = event_data["path_type"]
    exposure = event_data["exposure"]
    finding_count = event_data["finding_count"]
    principal_count = event_data["principal_count"]
    created_at = event_data["created_at"]
    updated_at = event_data["updated_at"]
    deleted_at = event_data["deleted_at"]
    severity = event_data["severity"]

    timestamp = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Write event
    event = Event(time = '%.3f' % timestamp.timestamp())
    event.stanza = stanza
    event.data = ("domain_id={domain_id}"
                " domain_impact_value={domain_impact_value}"
                " domain_name={domain_name}"      # If you rename this, update EXTRACT-domain_name in default/props.conf
                " domain_type={domain_type}"
                " id={id}"
                " path_title={path_title}"        # If you rename this, update EXTRACT-path_title in default/props.conf
                " path_type={path_type}"          # If you rename this, update EXTRACT-path_type in default/props.conf
                " exposure={exposure}"
                " finding_count={finding_count}"
                " principal_count={principal_count}"
                " created_at={created_at}"
                " updated_at={updated_at}"
                " deleted_at={deleted_at}"
                " severity={severity}"
                " data_type={data_type}"
                ).format(
                    domain_id = domain['id'],
                    domain_impact_value = domain['impactValue'],
                    domain_name = domain['name'],
                    domain_type = domain['type'],
                    id = id,
                    path_title = path_title,
                    path_type = path_type,
                    exposure = exposure,
                    finding_count = finding_count,
                    principal_count = principal_count,
                    created_at = created_at,
                    updated_at = updated_at,
                    deleted_at = deleted_at,
                    severity = severity,
                    data_type = "paths"
                )
    return event

def get_splunk_posture_event(event_data, stanza, domains):
    domain_id = event_data["domain_sid"]
    exposure = str(int(float(event_data["exposure_index"]) * 100))
    tier_zero_count = event_data["tier_zero_count"]
    critical_risk_count = event_data["critical_risk_count"]
    id = event_data["id"]
    created_at = event_data["created_at"]
    deleted_at_time = event_data["deleted_at"]["Time"]
    deleted_at_valid = event_data["deleted_at"]["Valid"]

    timestamp = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')

    # Lookup domain name and type
    try:
        domain = next(x for x in domains if x['id'] == domain_id)
    except:
        #insert null domain lookup info if domain no longer exists
        domain = {'type': 'null', 'name': 'null', 'impactValue': 'null'}
    
    # Write event
    event = Event(time = '%.3f' % timestamp.timestamp())
    event.stanza = stanza
    event.data = ("domain_id={domain_id}"
                    " exposure={exposure}"
                    " tier_zero_count={tier_zero_count}"
                    " critical_risk_count={critical_risk_count}"
                    " id={id}"
                    " created_at={created_at}"
                    " deleted_at_time={deleted_at_time}"
                    " deleted_at_valid={deleted_at_valid}"
                    " domain_impact_value={domain_impact_value}"
                    " domain_name={domain_name}"            # If you rename this, update EXTRACT-domain_name in default/props.conf
                    " domain_type={domain_type}"
                    " data_type={data_type}"
                ).format(
                    domain_id = domain_id,
                    exposure = exposure,
                    tier_zero_count = tier_zero_count,
                    critical_risk_count = critical_risk_count,
                    id = id,
                    created_at = created_at,
                    deleted_at_time = deleted_at_time,
                    deleted_at_valid = deleted_at_valid,
                    domain_impact_value = domain['impactValue'],
                    domain_name = domain['name'],
                    domain_type = domain['type'],
                    data_type = "posture"
                )
    return event

def get_splunk_audit_event(event_data, stanza):
    id = event_data["id"]
    created_at = event_data["created_at"]
    actor_name = event_data["actor_name"]
    actor_email = event_data["actor_email"]
    action = event_data["action"]
    message = event_data["fields"]
    source_ip = event_data["source_ip_address"]
    status = event_data["status"]
    timestamp = datetime.datetime.strptime(created_at, '%Y-%m-%dT%H:%M:%S.%fZ')

    #Write Event

    event = Event(time = '%.3f' % timestamp.timestamp())
    event.stanza = stanza
    event.data = ("id={id}"
                  " created_at={created_at}"
                  " actor_email={actor_email}"
                  " action={action}"
                  " message={message}"
                  " source_ip={source_ip}"
                  " status={status}"
                  " data_type={data_type}"
                ).format(
                    id = id,
                    created_at = created_at,
                    actor_name = actor_name,
                    actor_email = actor_email,
                    action = action,
                    message = message,
                    source_ip = source_ip,
                    status = status,
                    data_type = "audit"
                )
    return event
