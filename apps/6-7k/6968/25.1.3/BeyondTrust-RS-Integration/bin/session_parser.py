import xml.etree.ElementTree as ET
import re
import traceback
from datetime import datetime, timezone
from dateutil.tz import tzlocal

DATA_DELIMITER = "|"

EVENT_ID_MAP = {
    'Callback Button Deployed': '10',
    'Callback Button Removed': '20',
    'Chat Message': '30',
    'Command Shell Session Started': '40',
    'Conference Member Added': '50',
    'Conference Member Departed': '60',
    'Conference Member State Changed': '70',
    'Conference Owner Changed': '80',
    'Credential Injection Attempt Failed': '90',
    'Credential Injection Attempt': '100',
    'Customer Exit Survey': '110',
    'Directory Created': '120',
    'External Key': '130',
    'File Deleted': '140',
    'File Download Failed': '150',
    'File Download': '160',
    'File Moved': '170',
    'File Upload Failed': '180',
    'File Upload': '190',
    'Files Shared': '200',
    'Jump Item Authorization Request Utilized': '210',
    'Jump Item Authorization Request': '220',
    'Legal Agreement Response': '230',
    'Pinned Session Moved Away from Queue': '240',
    'Pinned Session Moved to Queue': '250',
    'Pinned Session Password Modified': '260',
    'Registry Exported': '270',
    'Registry Imported': '280',
    'Registry Key Added': '290',
    'Registry Key Deleted': '300',
    'Registry Key Renamed': '310',
    'Registry Value Added': '320',
    'Registry Value Deleted': '330',
    'Registry Value Modified': '340',
    'Registry Value Renamed': '350',
    'Representative Exit Survey': '360',
    'Representative Monitoring Started': '370',
    'Representative Monitoring Stopped': '380',
    'Screen Recording': '390',
    'Screenshot Captured': '400',
    'Service Access Allowed': '410',
    'Session Assigned': '420',
    'Session Assignment Response': '430',
    'Session End': '440',
    'Session Foreground Window Changed': '450',
    'Session Note Added': '460',
    'Session Pinned to Queue': '470',
    'Session Start': '480',
    'Session Transferred Away from Queue': '490',
    'Session Transferred to Queue': '500',
    'Session Unpinned from Queue': '510',
    'Show My Screen Recording': '520',
    'System Information Retrieved': '530'
}

EVENT_DATA_FIELD_MAP = {
    'deviceHost': 'deviceHost',
    'sessionId': 'sessionId',
    'externalKeyLabel': 'externalKeyLabel',
    'externalKey': 'externalKey',
    'sourceUser': 'srcUser',
    'sourceUserId': 'srcUid',
    'sourceHost': 'srcHost',
    'sourceAddress': 'srcAddr',
    'sourcePort': 'srcPort',
    'sourcePrivateAddress': 'srcPrivAddr',
    'sourceUserType': 'srcPriv',
    'destinationUser': 'dstUser',
    'destinationUserId': 'dstUid',
    'destinationHost': 'dstHost',
    'destinationAddress': 'dstAddr',
    'destinationPort': 'dstPort',
    'destinationPrivateAddress': 'dstPrivAddr',
    'destinationUserType': 'dstPriv',
    'message': 'msg',
    'path': 'filePath',
    'filename': 'filePath',
    'filesize': 'fsize',
    'old_path': 'oldFilePath',
    'new_path': 'filePath',
    'priority': 'sessionPriority',
    'owner': 'sessionOwner',
    'attempt_id': 'credentialAttempt',
    'credential_id': 'credentialId',
    'credential_name': 'credentialName',
    'failure_reason': 'failureReason',
    'key_path': 'keyPath',
    'parent_path': 'parentPath',
    'root_path': 'rootPath',
    'key_name': 'keyName',
    'key_name_old': 'keyNameOld',
    'key_name_new': 'keyNameNew',
    'value_name': 'valueName',
    'value_name_old': 'valueNameOld',
    'value_name_new': 'valueNameNew',
    'value_type': 'valueType',
    'value_data': 'valueData',
    'value_data_old': 'valueDataOld',
    'value_data_new': 'valueDataNew',
    'Command Shell Session Started': {
        'instance': 'cmdShellInst',
        'download_url': 'cmdShellDlUrl',
        'view_url': 'cmdShellViewUrl'
    },
    'Conference Member Added': {
        'private_name': 'confMemPrivName',
        'public_name': 'confMemPubName',
        'username': None,
        'private_ip': None,
        'public_ip': None,
        'hostname': None,
        'os': 'confMemOs',
        'support_teams': 'confMemTeams',
        'user_id': None
    },
    'Conference Member State Changed': {
        'state': 'msg'
    },
    'Service Access Allowed': {
        'granted_to': 'accessGrantedTo',
        'level': 'accessLevel',
        'service': 'accessService'
    },
    'Session Foreground Window Changed': {
        'exeName': 'exeName',
        'windowName': 'windowName'
    }
}

########## convert the xml session report into discrete events
def get_events(helper, session: str, rs_hostname: str, xmlns: str):
    
    # array of string events per session
    return __get_events_from_session(helper, session, rs_hostname, xmlns)

########## -----------------------------------------------

def __get_events_from_session(helper, support_session: ET.Element, rs_hostname: str, xmlns):
    # returned events are dictionaries with 2 keys: 'end_time', and 'event_data'
    lsid = support_session.attrib['lsid']
    externalKey = __get_xml_text(support_session.find('.//xmlns:external_key', xmlns))
    helper.log_info(f"Getting events for session lsid: '{lsid}'")

    session_data = {}
    session_data['lsid'] = lsid
    session_data['external_key'] = externalKey
    session_data['device_host'] = rs_hostname
    session_data['user_data'] = __get_user_data(helper, support_session.find('xmlns:rep_list', xmlns), xmlns)
    session_data['endpoint_data'] = __get_endpoint_data(helper, support_session.find('.//xmlns:customer', xmlns), xmlns)
    session_data['jumpoint_data'] = __get_jumpoint_data(helper, support_session, xmlns)

    events = {}
    events['end_time'] = support_session.find('.//xmlns:end_time', xmlns).attrib['timestamp']
    events['events'] = __parse_events_from_session(helper, session_data, support_session.find('xmlns:session_details', xmlns), xmlns)

    return events

def __get_user_data(helper, rep_list: ET.Element, xmlns):
    helper.log_debug('Getting users in session')
    users = {}

    for rep in rep_list:
        try:
            gsnumber = str(rep.attrib['gsnumber'])
            users[gsnumber] = {}

            # parse out the address if it exists
            address = None
            port = None
            address_split = rep.find('xmlns:public_ip', xmlns)
            if address_split != None:
                address_split = address_split.text.split(':')
                address = address_split[0]
                port = address_split[1]

            users[gsnumber]['address'] = address
            users[gsnumber]['port'] = port
            
            users[gsnumber]['id'] = rep.attrib['id']
            users[gsnumber]['username'] = __get_xml_text(rep.find('xmlns:username', xmlns))
            users[gsnumber]['private_address'] = __get_xml_text(rep.find('xmlns:private_ip', xmlns))
            users[gsnumber]['hostname'] = __get_xml_text(rep.find('xmlns:hostname', xmlns))

        except Exception as e:
            helper.log_error(f"Error getting user: {str(e)}")
            traceback.print_exc()

    return users

def __get_endpoint_data(helper, endpoint: ET.Element, xmlns):
    helper.log_debug('Getting session endpoint')

    endpoint_data = {}

    endpoint_data['hostname'] = __get_xml_text(endpoint.find('xmlns:hostname', xmlns))
    endpoint_data['private_address'] = __get_xml_text(endpoint.find('xmlns:private_ip', xmlns))

    public_address = None
    public_address_xml = endpoint.find('xmlns:public_ip', xmlns)
    if public_address_xml != None:
        public_address = public_address_xml.text

    # if there is an ip provided, split out the port if present and return only the ip portion
    if public_address != None:
        public_address = public_address.split(':')[0]

    endpoint_data['public_address'] = public_address

    return endpoint_data

def __get_jumpoint_data(helper, session: ET.Element, xmlns):
    helper.log_debug('Getting session jumpoint data')
    jumpoint_data = {}

    jumpoint_id = None
    jumpoint_name = None
    jumpoint = session.find('xmlns:jumpoint', xmlns)
    if jumpoint != None:
        jumpoint_id = jumpoint.attrib['id']
        jumpoint_name = jumpoint.text

    jumpoint_data['jumpoint_id'] = jumpoint_id
    jumpoint_data['jumpoint_name'] = jumpoint_name

    jump_group_id = None
    jump_group_name = None
    jump_group_type = None
    jump_group = session.find('xmlns:jump_group', xmlns)
    if jump_group != None:
        jump_group_id = jump_group.attrib['id']
        jump_group_name = jump_group.text
        jump_group_type = jump_group.attrib['type']

    jumpoint_data['jump_group_id'] = jump_group_id
    jumpoint_data['jump_group_name'] = jump_group_name
    jumpoint_data['jump_group_type'] = jump_group_type

    # clear the id values if they are -1
    if jumpoint_data['jumpoint_id'] == '-1':
        jumpoint_data['jumpoint_id'] = ''
    if jumpoint_data['jump_group_id'] == '-1':
        jumpoint_data['jump_group_id'] = ''

    return jumpoint_data

def __parse_events_from_session(helper, session_data, event_list: ET.Element, xmlns):
    helper.log_debug(f"Collecting events in session")
    events: list[str] = []

    for xml_event in event_list:
        event_name = xml_event.attrib['event_type']
        if not event_name != None:
            helper.log_error(f"Unable to determine event type in session: '{session_data['lsid']}'")
            continue
        try:
            siem_event = {}

            if not __should_process_event(event_name):
                helper.log_debug(f"Skipping event '{event_name}'")
                continue

            siem_event['timestamp'] = xml_event.attrib['timestamp']
            siem_event['event_id'] = __get_event_id(event_name)
            siem_event['event_name'] = event_name
            siem_event['device_host'] = session_data['device_host']
            siem_event['extension_data'] = __create_extension_data(helper, session_data, xml_event, event_name, xmlns)

            events.append(__siem_event_to_str(helper, siem_event))
        except Exception as e:
            helper.log_error(f"Error retrieving event data for: '{event_name}' in session: '{session_data['lsid']}'.")
            helper.log_error(str(e))
            traceback.print_exc()

    helper.log_info(f"Created {len(events)} events")

    return events

def __siem_event_to_str(helper, siem_event):
    event = ''

    unix_timestamp = datetime.fromtimestamp(int(siem_event['timestamp']), tz=timezone.utc)
    local_timestamp = unix_timestamp.astimezone(tzlocal())
    event += local_timestamp.strftime('%b %d %H:%M:%S')
    event += '|BeyondTrust|Remote Support Appliance|15.x+|'
    event += f"{siem_event['event_id']}|{siem_event['event_name']}|{siem_event['extension_data']}"

    helper.log_debug(f"Created siem event:\n{event}")

    return event

def __create_extension_data(helper, session_data, xml_event: ET.Element, event_name: str, xmlns):
    helper.log_debug('Adding extension data')

    extension_data = ''
    try:
        extension_data += __add_extension_data(__get_event_field(event_name, 'deviceHost'), session_data['device_host'])
        extension_data += __add_extension_data(__get_event_field(event_name, 'sessionId'), session_data['lsid'])
        extension_data += __add_extension_data(__get_event_field(event_name, 'externalKeyLabel'), 'External Key')
        extension_data += __add_extension_data(__get_event_field(event_name, "externalKey"), session_data['external_key'])
        
        extension_data += __add_extension_data(__get_event_field(event_name, 'jumpointId'), session_data['jumpoint_data']['jumpoint_id'])
        extension_data += __add_extension_data(__get_event_field(event_name, 'jumpointName'), session_data['jumpoint_data']['jumpoint_name'])
        extension_data += __add_extension_data(__get_event_field(event_name, 'jumpGroupId'), session_data['jumpoint_data']['jump_group_id'])
        extension_data += __add_extension_data(__get_event_field(event_name, 'jumpGroupName'), session_data['jumpoint_data']['jump_group_name'])
        extension_data += __add_extension_data(__get_event_field(event_name, 'jumpGroupType'), session_data['jumpoint_data']['jump_group_type'])

        performed_by = xml_event.find('xmlns:performed_by', xmlns)
        if performed_by != None:
            extension_data += __user_extension_data(helper, session_data, performed_by, True, event_name)

        destination = xml_event.find('xmlns:destination', xmlns)
        if destination != None:
            extension_data += __user_extension_data(helper, session_data, destination, False, event_name)
        else: # if there is no destination node, add these 2 fields
            extension_data += __add_extension_data(__get_event_field(event_name, 'destinationUser'), session_data['endpoint_data']['hostname'])
            extension_data += __add_extension_data(__get_event_field(event_name, 'destinationUserId'), session_data['endpoint_data']['private_address'])
        
        body = xml_event.find('xmlns:body', xmlns)
        if body != None:
            extension_data += __add_extension_data(__get_event_field(event_name, 'message'), body.text)

        event_data = xml_event.find('xmlns:data', xmlns)
        if event_data != None:
            extension_data += __event_values_extension_data(helper, event_data, event_name)

    except Exception as e:
        helper.log_error(f'Error creating extension data: {str(e)}')
        traceback.print_exc()

    return extension_data

def __user_extension_data(helper, session_data, event_actor_action: ET.Element, is_source: bool, event_name: str):
    extension_data = ''

    # source and destination extension data are identical with the only difference being the keys used
    prepend_key = ''
    if is_source:
        prepend_key = 'source'
    else:
        prepend_key = 'destination'

    helper.log_debug(f"Adding '{prepend_key}' extension data")

    gs_number = event_actor_action.attrib['gsnumber']
    user_type = event_actor_action.attrib['type']
    user_data = session_data['user_data']
    endpoint_data = session_data['endpoint_data']

    if user_type == 'representative' and user_data[gs_number]:
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}User'), user_data[gs_number]['username'])
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}UserId'), user_data[gs_number]['id'])
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}Host'), user_data[gs_number]['hostname'])
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}Address'), user_data[gs_number]['address'])
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}Port'), user_data[gs_number]['port'])
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}PrivateAddress'), user_data[gs_number]['private_address'])
    else: # 'customer' type means the endpoint
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}User'), event_actor_action.text)
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}UserId'), gs_number)
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}Host'), endpoint_data['hostname'])
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}Address'), endpoint_data['public_address'])
        extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}PrivateAddress'), endpoint_data['private_address'])

    extension_data += __add_extension_data(__get_event_field(event_name, f'{prepend_key}UserType'), user_type)

    return extension_data

def __event_values_extension_data(helper, event_data: ET.Element, event_name: str):
    helper.log_debug('Adding event values extension data')
    extension_data = ''

    for value in event_data:
        try:
            field = __get_event_field(event_name, value.attrib['name'])
            if field != None:
                # if this is a custom field of some kind
                field_split = field.split('|')
                if len(field_split) == 3:
                    extension_data += __add_extension_data(field_split[0], __to_safe_string(field_split[1]))
                    extension_data += __add_extension_data(field_split[2], value.attrib['value'])
                else:
                    extension_data += __add_extension_data(field, value.attrib['value'])
        except Exception as e:
            helper.log_error(f"Error adding value: '{value}'. {str(e)}")
            traceback.print_exc()

    return extension_data

def __should_process_event(event_name):
    # this is intended to allow the ability for an end user to filter out event types they dont care about
    # not implemented yet
    return True

def __add_extension_data(item_key: str, item_value: str):
    extensionData = ''
    if item_key and item_value:
        extensionData = item_key + '=' + item_value + DATA_DELIMITER

    return extensionData

def __get_event_id(event_name: str):
    eventid = None
    if event_name in EVENT_ID_MAP:
        eventid = EVENT_ID_MAP[event_name]

    return eventid if eventid else '999'

def __get_event_field(event_name: str, bomgar_field: str):
    event_field = None

    # Return the mapped field or the original BeyondTrust field name if no mapped entry exists
    if event_name and event_name in EVENT_DATA_FIELD_MAP and bomgar_field in EVENT_DATA_FIELD_MAP[event_name]:
        event_field = EVENT_DATA_FIELD_MAP[event_name][bomgar_field]
    elif bomgar_field in EVENT_DATA_FIELD_MAP:
        event_field = EVENT_DATA_FIELD_MAP[bomgar_field]

    return event_field if event_field else bomgar_field

def __to_safe_string(input):
    result = re.sub("\\\\", "\\\\", input)
    result = re.sub("\\|", "\\|", result)
    result = re.sub("=", "\\=", result)
    result = re.sub("\r", "\\r", result)
    result = re.sub("\n", "\\n", result)

    return result

def __get_xml_text(xml: ET.Element):
    text = None
    if xml != None:
        text = xml.text

    return text