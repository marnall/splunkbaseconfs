# encoding = utf-8
from re import compile as re_complie
from json import dumps
from copy import deepcopy
from datetime import datetime


from sixgill.sixgill_feed_client import SixgillFeedClient
from sixgill.sixgill_constants import FeedStream
from sixgill.sixgill_utils import is_indicator
from splunk_utils import SplunkUtils
from collections import OrderedDict


CHANNEL_ID = "7d274d05e666cfa5a95aac2182a142b7"

stix_regex_parser = re_complie(r"([\w-]+?):(\w.+?) (?:[!><]?=|IN|MATCHES|LIKE) '(.*?)' *[OR|AND|FOLLOWEDBY]?")
HASH_MAPPING = {"hashes.md5": "md5", "hashes.\'sha-1\'": "sha1", "hashes.\'sha-256\'": "sha256"}

SPLUNK_COLLECTION_NAME = "splunk_collection_name"
DATE_TIME_FORMAT = '%Y-%m-%dT%H:%M:%S.%fZ'
KEY_DELETE = "delete"
KEY_ADD = "add"


def clean_url(value):
    return value.replace("[.]", ".")


splunk_mapping = {
    'darkfeed_001': {'collection_name': "http_intel", 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_002': {'collection_name': "file_intel", 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_003': {'collection_name': "http_intel", 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_004': {'collection_name': "ip_intel", 'field_name': "ip", 'pipeline': []},
    'darkfeed_005': {'collection_name': "ip_intel", 'field_name': "ip", 'pipeline': []},
    'darkfeed_006': {'collection_name': "ip_intel", 'field_name': "ip", 'pipeline': []},
    'darkfeed_007': {'collection_name': "ip_intel", 'field_name': "ip", 'pipeline': []},
    'darkfeed_008': {'collection_name': "ip_intel", 'field_name': "ip", 'pipeline': []},
    'darkfeed_009': {'collection_name': "ip_intel", 'field_name': "ip", 'pipeline': []},
    'darkfeed_010': {'collection_name': "http_intel", 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_012': {'collection_name': "file_intel", 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_013': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_014': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_015': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_018': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_019': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_020': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_021': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_022': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_023': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_024': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_025': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_026': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_027': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_028': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_029': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_030': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_031': {'collection_name': "http_intel", 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_032': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_033': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_034': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_035': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_036': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_037': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_038': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_039': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_040': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_041': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_042': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_043': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_044': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_045': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_046': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_047': {'collection_name': "http_intel", 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_048': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_049': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_050': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_051': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_052': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_053': {'collection_name': 'file_intel', 'field_name': "file_hash", 'pipeline': []},
    'darkfeed_054': {'collection_name': 'http_intel', 'field_name': "url", 'pipeline': [clean_url]},
    'darkfeed_055': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []},
    'darkfeed_056': {'collection_name': 'ip_intel', 'field_name': "ip", 'pipeline': []}
}

splunk_collections = {
    'ip_intel': {KEY_ADD: [], KEY_DELETE: []},
    'file_intel': {KEY_ADD: [], KEY_DELETE: []},
    'user_intel': {KEY_ADD: [], KEY_DELETE: []},
    'http_intel': {KEY_ADD: [], KEY_DELETE: []},
    'email_intel': {KEY_ADD: [], KEY_DELETE: []},
    'service_intel': {KEY_ADD: [], KEY_DELETE: []},
    'process_intel': {KEY_ADD: [], KEY_DELETE: []},
    'registry_intel': {KEY_ADD: [], KEY_DELETE: []},
    'certificate_intel': {KEY_ADD: [], KEY_DELETE: []},
}

DESCRIPTION_FIELD_ORDER = OrderedDict([('Description', 'sixgill_description'),
                                       ('Created On', 'created'),
                                       ('Post Title', 'sixgill_posttitle'),
                                       ('Threat Actor Name', 'sixgill_actor'),
                                       ('Source', 'sixgill_source'),
                                       ('Sixgill Feed ID', 'sixgill_feedid'),
                                       ('Sixgill Feed Name', 'sixgill_feedname'),
                                       ('Sixgill Post ID', 'sixgill_postid'),
                                       ('Language', 'lang'),
                                       ('Indicator ID', 'id'),
                                       ('External references (e.g. MITRE ATT&CK)', 'external_reference')])

indicators_to_delete = []

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    client_id = definition.parameters.get('client_id')
    client_secret = definition.parameters.get('client_secret')

    if not client_id:
        raise ValueError("Client ID is a required parameter.")
    if not client_secret:
        raise ValueError("Client Secret is a required parameter.")


def run_pipeline(value, pipeline, log):
    for func in pipeline:
        log.debug("run {} function on value: {}".format(func.__name__, value))
        value = func(value)
        log.debug("post {} run value: {}".format(func.__name__, value))

    log.debug("returned value: {}".format(value))
    return value


def get_description(stix_obj):
    description_string = ""
    for name, sixgill_name in DESCRIPTION_FIELD_ORDER.items():
        description_string += "{}: {}\n".format(name, stix_obj.get(sixgill_name))

    return description_string


def get_splunk_indicators(stix2obj, helper):
    hashes = {"md5": None, "sha1": None, "sha256": None}
    parsed_pattern = []
    indicators = []

    pattern = stix2obj.get("pattern", "")
    sixgill_feedid = stix2obj.get("sixgill_feedid", "")

    splunk_collection_name = splunk_mapping.get(sixgill_feedid,{}).get("collection_name",'')
    splunk_field_name = splunk_mapping.get(sixgill_feedid,{}).get("field_name", 'value')

    stix2obj[SPLUNK_COLLECTION_NAME] = splunk_collection_name
    stix2obj["_key"] = stix2obj.get("id")
    stix2obj["threat_key"] = stix2obj.get("id")
    stix2obj["sixgill_description"] = stix2obj.get("description")
    stix2obj["weight"] = stix2obj.get("sixgill_severity")
    utc_time = datetime.strptime(stix2obj.get("created"), DATE_TIME_FORMAT)
    stix2obj["time"] = (utc_time - datetime(1970, 1, 1)).total_seconds()
    stix2obj["threat_group"] = "APT"
    stix2obj["threat_category"] = stix2obj.get("sixgill_feedname")


    for match in stix_regex_parser.findall(pattern):
        try:
            stix_type, stix_property, value = match
            splunk_indicator_map = splunk_mapping.get(sixgill_feedid,{})
            parsed_value = run_pipeline(value, splunk_indicator_map.get('pipeline', []), helper.logger)
            splunk_indicator = deepcopy(stix2obj)

            if splunk_indicator.get(splunk_collection_name) == "file_intel" and \
                    HASH_MAPPING.get(stix_property.lower()) in hashes.keys():
                hashes[HASH_MAPPING[stix_property.lower()]] = parsed_value

            splunk_indicator[splunk_field_name] = parsed_value
            indicators.append(splunk_indicator)

            stix_property = stix_property.replace('\'', '')
            if stix_property == 'value':
                stix_property = stix_type + '.' + stix_property

            parsed_pattern.append({
                "type": stix_type,
                "property": stix_property,
                "value":  value,
                "parsed_value": parsed_value,
            })

        except Exception as e:
            helper.logger.error("failed converting STIX object to indicator: {}, STIX object: {}".format(e, stix2obj))
            continue

    full_description = get_description(stix2obj)

    for indicator in indicators:
        indicator["parsed_pattern"] = parsed_pattern
        indicator["hashes"] = hashes
        indicator["description"] = full_description

    return indicators


def add_to_splunk_collection(indicator):
    revoked = indicator.get("revoked", False)
    action = KEY_DELETE if revoked else KEY_ADD

    if action == KEY_DELETE:
        splunk_collections[indicator.get(SPLUNK_COLLECTION_NAME)][action].append({"_key": indicator.get("_key")})

    else:
        splunk_collections[indicator.get(SPLUNK_COLLECTION_NAME)][action].append(indicator)


def get_proxy_session(helper):
    helper.rest_helper._init_request_session(helper._get_proxy_uri())
    proxy_config = helper.rest_helper.requests_proxy if helper.rest_helper.requests_proxy else {}
    return proxy_config


def init_splunk_utils(helper):
    host = helper.get_arg('splunk_host')
    port = helper.get_arg('splunk_port')
    global_account = helper.get_arg('global_account')
    splunk_user = global_account['username']
    splunk_password= global_account['password']

    helper.logger.info("host: {}, port: {}, splunk_user: {}, verify_ssl: {}".format(host, port, splunk_user, True))
    
    
    if not host or not port or not splunk_user or not splunk_password:
        return None

    return SplunkUtils(host=host, port=port, username=splunk_user, password=splunk_password, verify=True)


def indicators_to_enterprise_security(helper):
    splunk_utils = init_splunk_utils(helper)

    if splunk_utils:
        helper.logger.info("pushing indicator to Splunk Enterprise Security KV")

        for collection_name, action_dict in splunk_collections.items():
            try:
                if len(action_dict.get(KEY_ADD)) > 0:
                    helper.logger.info("push indicators to {} number of indicators {}".format(collection_name, len(action_dict.get(KEY_ADD))))
                    ret = splunk_utils.add_threat_intel_item(collection_name, action_dict.get(KEY_ADD))
                    helper.logger.info("push status {}".format(ret))
            except Exception as e:
                helper.logger.error("error {}".format(e))

            try:
                if len(action_dict.get(KEY_DELETE)) > 0:
                    helper.logger.info("delete revoked indicators from {} number of indicators {}".format(collection_name, len(action_dict.get(KEY_DELETE))))
                    ret = splunk_utils.delete_threat_intel_item(collection_name, action_dict.get(KEY_DELETE))
                    helper.logger.info("delete status {}".format(ret))
            except Exception as e:
                helper.logger.error("error {}".format(e))
    else:
        helper.logger.info("failed to create splunk_utils object")


def collect_events(helper, ew):
    client_id = helper.get_arg('client_id')
    client_secret = helper.get_arg('client_secret')
    confidence = helper.get_arg('confidence')
    confidence = 'all' if confidence is None else confidence
    confidence = int(confidence) if isinstance(confidence, str) and confidence.isdigit() else confidence
    filter_func = lambda x: (isinstance(confidence, str) and confidence in ['all', '']) or (x.get("sixgill_confidence") and int(x.get("sixgill_confidence")) >= confidence)
    
    helper.rest_helper.http_session.proxies = get_proxy_session(helper)
    sixgill_darkfeed_client = SixgillFeedClient(client_id, client_secret, CHANNEL_ID, FeedStream.DARKFEED,
                                                logger=helper.logger, session=helper.rest_helper.http_session,
                                                verify=True)
    
    bundle = sixgill_darkfeed_client.get_bundle()
    indicators_to_create = []

    for stix_indicator in filter(filter_func, bundle.get("objects", [])):
        if is_indicator(stix_indicator):
            indicators = get_splunk_indicators(stix_indicator, helper)
            indicators_to_create.extend(indicators)

    sixgill_darkfeed_client.commit_indicators()

    helper.logger.info("bundle {}".format(bundle.get('id')))

    for indicator in indicators_to_create:
        add_to_splunk_collection(indicator)
        event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(),
                                 sourcetype=helper.get_sourcetype(), data=dumps(indicator))
        ew.write_event(event)

    indicators_to_enterprise_security(helper)
