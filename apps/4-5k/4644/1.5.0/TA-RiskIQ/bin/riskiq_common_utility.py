# python imports
import os
import sys
import datetime
import json
from collections import Mapping, Set, Sequence
from os.path import dirname, abspath, join, isfile
from requests.compat import quote_plus

import splunk.rest as rest
from solnlib.credentials import CredentialManager, CredentialNotExistException
from solnlib.utils import is_true
import splunk.entity as entity

# local imports
import riskiq_logger_manager as log


_LOGGER = log.setup_logging("ta_riskiq_util")
APP_NAME = __file__.split(os.sep)[-3]


def get_proxy_clear_password(session_key):
    """
    Get clear password from splunk passwords.conf.

    :return: str/None: proxy password if available else None.
    """
    _LOGGER.debug("Reading proxy password in clear text.")
    try:
        manager = CredentialManager(
            session_key,
            app=APP_NAME,
            realm="__REST_CREDENTIAL__#{0}#{1}".format(
                APP_NAME, "configs/conf-ta_riskiq_settings"
            ),
        )
    except CredentialNotExistException:
        return None
    else:
        _LOGGER.debug("Proxy password found. Returning.")
        return json.loads(manager.get_password("proxy")).get("proxy_password")


def get_proxy_configuration(session_key):
    """
    Get proxy configuration settings.

    :return: proxy configuration dict.
    """
    rest_endpoint = "/servicesNS/nobody/{}/TA_riskiq_settings/proxy".format(
        APP_NAME)
    _LOGGER.debug(
        "Reading proxy details from REST Endpoint: {}".format(rest_endpoint))

    _, content = rest.simpleRequest(
        rest_endpoint,
        sessionKey=session_key,
        method="GET",
        getargs={"output_mode": "json"},
        raiseAllErrors=True,
    )

    _LOGGER.debug("Returning proxy details.")
    return json.loads(content)["entry"][0]["content"]


def get_proxy_uri(session_key, proxy_settings=None):
    """
    Generate proxy uri from provided configurations.

    :param session_key: Splunk Session Key
    :param proxy_settings: Proxy configuration dict. Defaults to None.
    :return: if proxy configuration available returns uri string else None.
    """
    _LOGGER.debug("Reading proxy configurations.")

    if not proxy_settings:
        proxy_settings = get_proxy_configuration(session_key)

    if proxy_settings.get("proxy_username"):
        proxy_settings["proxy_password"] = get_proxy_clear_password(
            session_key)

    if all(
        [
            proxy_settings,
            is_true(proxy_settings.get("proxy_enabled")),
            proxy_settings.get("proxy_url"),
            proxy_settings.get("proxy_type"),
        ]
    ):
        _LOGGER.debug("Proxy is enabled. Using proxy server.")
        http_uri = proxy_settings["proxy_url"]

        if proxy_settings.get("proxy_port"):
            http_uri = "{}:{}".format(
                http_uri, proxy_settings.get("proxy_port"))

        if proxy_settings.get("proxy_username") and proxy_settings.get(
            "proxy_password"
        ):
            http_uri = "{}:{}@{}".format(
                quote_plus(proxy_settings["proxy_username"], safe=""),
                quote_plus(proxy_settings["proxy_password"], safe=""),
                http_uri,
            )

        http_uri = "{}://{}".format(proxy_settings['proxy_type'], http_uri)

        proxy_data = {"http": http_uri, "https": http_uri}

        _LOGGER.debug("Returning proxy configurations.")

        return proxy_data
    else:
        _LOGGER.debug("Proxy is disabled or not configured. Skipping proxy.")
        return None


def get_only_changed_assets_fields(helper):
    """
    Method to get new_and_changed_assets_only flag.

    :param helper: Splunk's helper class.
    :return: new_and_changed_assets flag and last_updated_time.
    """
    only_changed_assets = helper.get_arg('new_and_changed_assets_only')
    last_updated_time = helper.get_arg('last_updated_time')
    if last_updated_time is None:
        last_updated_time = ""
    return(int(only_changed_assets), last_updated_time)


def get_data_filters(helper):
    """
    Method to get filters for GI assets.

    :param helper: Splunk's helper class.
    :return: tags, brands and org filters.
    """
    tags_filter = helper.get_arg('tags')
    brands_filter = helper.get_arg('brands')
    orgs_filter = helper.get_arg('organizations')
    return(tags_filter, brands_filter, orgs_filter)


def get_account_clear_password(session_key, account_name):
    """
    Get clear password of the configured account from the passwords.conf.

    :param session_key: splunk session key
    :param account_name: name of the configured account.
    :return api_secret
    """
    api_secret = ''
    entities = entity.getEntities('storage/passwords',
                                  search=APP_NAME,
                                  namespace=APP_NAME,
                                  owner='nobody',
                                  sessionKey=session_key)
    # return first set of credentials
    for _, value in entities.items():
        if value['username'].partition('`')[0] == str(account_name) and not value.get('clear_password', '`').startswith(
            '`'
        ):
            cred = json.loads(value.get('clear_password', '{}'))
            api_secret = cred.get('api_secret')
            break
    return api_secret


def create_riskiq_input(account_name, selected_endpoints, session_key):
    """
    Create RiskIQ Input for the selected endpoints.

    :param account_name : name of the configured account.
    :param selected_endpoints : list of the selected endpoints.
    :param session_key : Splunk session key.
    """
    _LOGGER.debug("Creating modular input stanzas.")

    for endpoint in selected_endpoints:
        if endpoint == "events":
            input_type = "riskiq_events"
        elif endpoint == "gi_assets":
            input_type = "risk_iq_global_inventory_assets"

        # Using Splunk Internal API to get all information related to endpoint
        _, content = rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-inputs/{}".format(APP_NAME, input_type),
            sessionKey=session_key,
            method='GET',
            getargs={"output_mode": "json"},
            raiseAllErrors=True
        )
        data = json.loads(content)['entry'][0]['content']

        input_name = "{}://{}_{}".format(input_type, account_name, endpoint)

        # Creating dict for input details
        final_input = {
            "name": input_name,
            "index": [data.get('index')],
            "sourcetype": [data.get('sourcetype')],
            "global_account": account_name,
            "interval": [data.get('interval')],
            "page_size": [data.get('page_size')],
            "disabled": "1"
        }
        _LOGGER.debug("Creating modular input stanza: {}".format(input_name))

        # Using Splunk internal API to create input
        rest.simpleRequest(
            "/servicesNS/nobody/{}/configs/conf-inputs".format(APP_NAME),
            session_key,
            postargs=final_input,
            method='POST',
            raiseAllErrors=True
        )
        _LOGGER.info("Created modular input stanza: {}.".format(input_name))


def splunk_field_name(key):
    """
    Method to clean keys(string).

    # Allowed range: [a-z, A-Z, 0-9, _ -].
    :param key: key.
    :return: clean unicode/string key in the mentioned range.
    """
    key = ''.join([c for c in key if ord(c) in range(97, 123)
                   or ord(c) in range(65, 91) or ord(c) in range(48, 57) or ord(c) in (45, 95)])
    # strip leading underbars
    key = key.lstrip('_')
    return(key)


# Should be all Unicode strings in d
# Potential time stamp: _time
# Cleans keys according Splunk fieldname syntax

def dict_2_splunk(d):
    """
    Method to create a string in key=value format from the given dictionary.

    :param d: dictionary of data to be ingested into Splunk.
    :return: string of k=v pairs.
    """
    # Single out special keys: _time
    try:
        str_format = '{0:s} '.format(d['_time'])
        customer_key = list(d.keys())[-1]
        str_format += ',{0}={1}'.format(customer_key, d[customer_key])
        d.pop('_time', None)
        d.pop(customer_key, None)
    except KeyError:
        # sys.stderr.write('No _time field: {!r}\n'.format(d))
        str_format = ''
    for k, v in d.items():
        # remaining fields
        # We rely on Splunk's default KV_MODE detection, based on key=value,
        # so need to take pre-caution for values containing = and/or ,
        v = v.replace('"', '\\\"')
        if ',' in v or '=' in v and v[0] != '\"':
            # Surround value by " if required, and remove any newlines
            # - questionable practice....
            v = '\"{}\"'.format(v)
        # Delete newlines from values - questionable practice really
        # - we should not tamper with any content....
        v = v.replace('\n', '')
        str_format += ',{0}={1}'.format(splunk_field_name(k), v)
    str_format += ',ok'
    return(str_format)

# Open file containing the last event timestamps per command
# HOSTS,CONFIRMED,20180410


def get_last_event_timestamp(data):
    """
    Extract the latest timestamp from the given checkpoint data.

    :param data: raw data from checkpoint.
    :return: list representation of the checkpoint value.
    """
    d_last_events = {}
    for str_line in data:
        if str_line.strip() == "":
            continue
        line = str_line.rstrip().split(',')
        if len(line) == 2:
            if line[0] == "EVENTS" or "CHANGED_" in line[0]:
                d_last_events[('riskiq', line[0])] = line[1]
            else:
                d_last_events[('riskiq', line[0])] = datetime.datetime.strptime(
                    line[1], '%Y%m%d').date()
        else:
            if line[1] == "EVENTS" or "CHANGED_" in line[1]:
                d_last_events[(line[0], line[1])] = line[2]
            else:
                d_last_events[(line[0], line[1])] = datetime.datetime.strptime(
                    line[2], '%Y%m%d').date()
    return d_last_events


# d_commands: {'HOSTS':dateobject}
def set_checkpoint(helper, key, d_commands):
    """
    Method to set checkpoint in the kvstore.

    :param helper: Splunk's helper class.
    :param key: input name to which the checkpoint is associated.
    :param d_commands: Control commands related to events or assets data.
    :return: None.
    """
    checkpoint_list = []
    try:
        # HOSTS,10180410
        for k, v in d_commands.items():
            if k[1] == 'EVENTS' or "CHANGED_" in k[1]:
                checkpoint_list.append('{0},{1},{2}\n'.format(k[0], k[1], v))
            else:
                checkpoint_list.append('{0},{1},{2}\n'.format(
                    k[0], k[1], v.strftime('%Y%m%d')))
        helper.save_check_point(key, checkpoint_list)
        _LOGGER.debug("New checkpoint saved : {}".format(
            helper.get_check_point(key)))
    except Exception as e:
        sys.stderr.write(str(e) + '\n')
        sys.stderr.write(
            'Error while saving last_eventid: ' + str(e) + '\n')
        _LOGGER.error('Error while saving last_eventid: ' + str(e) + '\n')
        sys.exit(2)


# Fetch the last event timestamp stored in kvstore or open the file containing last event timestamp
def get_checkpoint(helper, file_name, input_name):
    """
    Method to fetch checkpoint from checkpoint file and/or kvstore.

    # If a checkpoint file exists, it will be deleted.
    # New checkpoints will be stored in the kvstore.
    :param helper: Splunk's helper class.
    :param file_name: Name of checkpoint file.
    :param input_name: Name of the input to associate with the checkpoint.
    :return: dictionary of checkpoint.
    """
    d_last_events = {}

    old_checkpoint_file = old_checkpoint_file = join(dirname(
        dirname(abspath(__file__))), 'local', file_name)

    checkpoint = helper.get_check_point(input_name)
    if checkpoint:
        d_last_events = get_last_event_timestamp(checkpoint)
    elif isfile(old_checkpoint_file):
        try:
            fp = open(old_checkpoint_file, 'r')
            data = fp.read().strip().splitlines()
            d_last_events = get_last_event_timestamp(data)
            fp.close()
            os.remove(old_checkpoint_file)
            _LOGGER.debug(
                "Removed last_events file and saved the checkpoint using kvstore mechanism")
            set_checkpoint(helper, input_name, d_last_events)
        except Exception as e:
            sys.stderr.write(str(e) + '\n')
            sys.stderr.write(
                'Error: failed to read or understand last_eventid file, ' + old_checkpoint_file + '\n')
            _LOGGER.error(
                'Error: failed to read or understand last_eventid file, ' + old_checkpoint_file + '\n')
            sys.exit(2)
    return(d_last_events)


# dual python 2/3 compatability, inspired by the "six" library
if sys.version_info[0] >= 3:
    unicode = str
string_types = (str, unicode) if str is bytes else (str, bytes)

# Use list as a container to allow duplicate keys


def lflatten(obj, path=()):
    """
    Method to flatten objects of types: Mapping, Sequence, string.

    :param obj: Any object.
    :param path: Path.
    :return: flattened object.
    """
    flattened_obj = []
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            flattened_obj = flattened_obj + lflatten(v, path + (k,))
        return(flattened_obj)
    elif isinstance(obj, (Sequence, Set)) and not isinstance(obj, string_types):
        for x in obj:
            flattened_obj = flattened_obj + lflatten(x, path)
        return(flattened_obj)
    else:
        if str is bytes:
            if isinstance(obj, unicode):
                flattened_obj.append(('_'.join(map(unicode, path)), obj))
            elif isinstance(obj, str):
                flattened_obj.append(
                    ('_'.join(map(unicode, path)), obj.decode('utf-8')))
            else:
                flattened_obj.append(
                    ('_'.join(map(unicode, path)), unicode(obj)))
            return(flattened_obj)
        else:
            flattened_obj.append(('_'.join(map(str, path)), str(obj)))
            return(flattened_obj)


def l_flat(obj, delim=';'):
    """
    Creates a dictionary from a flattened object.

    :param obj: flattened object.
    :param delim: delimiter.
    :return: flattened dictionary.
    """
    flattened_obj = lflatten(obj)
    d_flat = {}
    for item in flattened_obj:
        if item[0] in d_flat:
            d_flat[item[0]] = d_flat[item[0]] + delim + item[1]
        else:
            d_flat[item[0]] = item[1]
    return(d_flat)
