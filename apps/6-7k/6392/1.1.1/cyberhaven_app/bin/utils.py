import json

def format_event(event):
    source_edge = event['edge']['source']
    destination_edge = event['edge']['destination']
    data = event['data']

    eventid = event['id']
    search_name = "Dataset: {}, Category: {}".format(event['category']['name'], event['dataset']['name'])
    file_name = 'none'
    if 'path_basename' in source_edge.keys():
        file_name = source_edge['path_basename']
    source_location = source_edge['location_outline']
    source_type = source_edge['location']
    destination_location = destination_edge.get('location_outline')
    destination_type = destination_edge.get('location')
    date = destination_edge.get('local_time')
    user = destination_edge.get('local_user_name')
    event_type = destination_edge.get('event_type')

    hostname = 'none'
    if 'hostname' in destination_edge.keys():
        hostname = destination_edge.get('hostname')

    userReactionMessages =  {
        'acknowledged': "Acknowledged",
        'none': "None",
        'not_applicable': "N/A",
        'provided_explanation': "Provided an explanation",
        'requested_review': "Requested review",
        'requested_unblock': "Self-unblocked",
        'warned': "Viewed the warning",
    }

    incident_response_to_message = {
        'access_restricted': "Blocked",
        'access_restricted_expired': "Blocking expired",
        'access_restricted_removed': "Blocking removed",
        'access_restricted_rate_limited': "Blocked, Response skipped: throttled",
        'not_applicable': "N/A",
        'skipped_rate_limited': "Response skipped: throttled",
        'skipped_timeout': "Response skipped: timeout",
        'pending': "Response pending",
        'warning_received': "Warning received by endpoint",
        'warned': "Warning shown",
    }


    user_reaction = ''

    if event['incident_reactions']:
        labels = map(lambda label: userReactionMessages[label], event['incident_reactions'])
        user_reaction =", ".join(list(labels))

    resolved_by = ''

    if event.get('admin_history'):
        for history in event['admin_history']:
            if history.get('new_status') == 'resolved':
                resolved_by = history.get('user')

    local_groups = ",".join(list(map(lambda group: group['sid'] + ':' + group['name'], destination_edge.get('local_groups') or [])))
    content = ",".join(data.get('personal_info') or [])

    return {
        'id': format_value(eventid),
        'search_name': format_value(search_name), 
        'file_name': format_value(file_name),
        'source_location': format_value(source_location),
        'source_type': format_value(source_type),
        'destination_location': format_value(destination_location),
        'destination_type': format_value(destination_type),
        'date': format_value(date),
        'event_type': event_type,

        'assignee': format_value(event.get('assignee')),
        'resolution_status': event.get('resolution_status'),
        'severity': event.get('severity'),
        'dataset_name': format_value(event['dataset'].get('name')),
        'category_name': format_value(event['category'].get('name')),
        'user': format_value(event.get('user')),
        'file': format_value(event.get('file')),
        'content_tags': format_value(",".join(event['content_tags'] or [])),
        'response': format_value(incident_response_to_message.get(event.get('incident_response'))),
        'user_reaction': format_value(user_reaction),
        'resolved_by': resolved_by,
        'timestamp UTC': event.get('event_time'),
        'resolution_time UTC': event.get('resolution_time'),
        'app_name': destination_edge.get('app_name'),
        'app_main_window_title': data.get('app_main_window_title'),
        'app_package_name': data.get('app_package_name'),
        'app_description': format_value(data.get('app_description')),
        'app_command_line': format_value(data.get('app_command_line')),
        'blocked': data.get('blocked') or False,
        'browser_page_url': format_value(destination_edge.get('browser_page_url')),
        'browser_page_domain': format_value(destination_edge.get('browser_page_domain')),
        'browser_page_title': format_value(destination_edge.get('browser_page_title')),
        'content_uri': destination_edge.get('content_uri'),
        'cloud_provider': destination_edge.get('cloud_provider'),
        'cloud_app': format_value(destination_edge.get('cloud_app')),
        'data_size': destination_edge.get('data_size'),
        'domain': format_value(destination_edge.get('domain')),
        'domain_category': format_value(data.get('destination') and data['destination'][0]),
        'event_type': destination_edge.get('event_type'),
        'endpoint_id': destination_edge.get('endpoint_id'),
        'email_account': destination_edge.get('email_account'),
        'file_path': format_value(data.get('path')),
        'file_extension': format_value(data.get('extension')),
        'file_size': destination_edge.get('file_size'),
        'group_name': format_value(",".join(destination_edge.get('group_name') or [])),
        'hostname': format_value(hostname),
        'location': format_value(destination_edge.get('location')),
        'local_time UTC': format_value(destination_edge.get('local_time')),
        'local_user_name': format_value(destination_edge.get('local_user_name')),
        'local_user_sid': format_value(destination_edge.get('local_user_sid')),
        'local_groups': format_value(local_groups),
        'local_machine_name': format_value(destination_edge.get('local_machine_name')),
        'media_category': format_value(data.get('media_category')),
        'md5_hash': format_value(destination_edge.get('md5_hash')),
        'salesforce_account_name': format_value(data.get('salesforce_account_name')),
        'salesforce_account_domains': format_value(",".join(data.get('salesforce_account_domains') or [])),
        'printer_name': format_value(data.get('printer_name')),
        'removable_device_name': format_value(data.get('removable_device_name')),
        'removable_device_vendor_id': format_value(data.get('removable_device_vendor_id')),
        'removable_device_product_id': format_value(data.get('removable_device_product_id')),
        'url': format_value(data.get('url')),
        'content': format_value(content),


        # dest_bunit dest_priority severity_id, src_priority

        # CIM fields https://docs.splunk.com/Documentation/CIM/4.2.0/User/Alerts
        'app': format_value(destination_edge.get('app_name')),
        'body': format_value(content),
        'dest': format_value(destination_location),
        'dest_category': format_value(event.get('category').get('id')),
        'src': format_value(source_edge.get('hostname')),
        'src_bunit': format_value(source_edge.get('location')),
        'src_category': format_value(source_edge.get('event_type')),
        'src_priority': format_value(source_edge.get('event_type')),
        'subject': format_value(event.get('category').get('name')),
        'tag': format_value(",".join(event['content_tags'] or [])),
        'type': format_value(destination_edge.get('event_type')),
    }
    

def format_value(value):
    if not value:
        return value
    return value.replace('\r', '').replace('\n', '')