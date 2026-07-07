import ta_flashpoint_intelligence_declare  # noqa: F401
import requests
import calendar
import copy
import json
import traceback
import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from solnlib.utils import is_true
import splunk.version as v
from solnlib import conf_manager

from formatters import get_event_time

TA_NAME = ta_flashpoint_intelligence_declare.ta_name
STATUS_FORCELIST = list(range(500, 600)) + [429]
REQ_TIMEOUT = 60    # In seconds


def requests_retry_session(
    retries=3, backoff_factor=30, status_forcelist=STATUS_FORCELIST, session=None
):
    """Create and return a session object.

    :param retries: Maximum number of retries to attempt
    :param backoff_factor: Backoff factor used to calculate time between retries.
    :param status_forcelist: A tuple containing the response status codes that should trigger a retry.
    :param session: Session object
    :return: Session Object
    """
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


SESSION_OBJECT = requests_retry_session()


def generate_query_params(helper):
    """Generate query parameters for compromised credentials."""
    is_fresh = is_true(helper.get_arg('is_fresh'))
    password_complexity_has_lowercase = is_true(helper.get_arg('password_complexity_has_lowercase'))
    password_complexity_has_number = is_true(helper.get_arg('password_complexity_has_number'))
    password_complexity_has_symbol = is_true(helper.get_arg('password_complexity_has_symbol'))
    password_complexity_has_uppercase = is_true(helper.get_arg('password_complexity_has_uppercase'))
    password_complexity_length = helper.get_arg('password_complexity_length')

    query_params = ""

    if is_fresh:
        query_params += "+is_fresh:(true)"

    if password_complexity_has_lowercase:
        query_params += "+password_complexity.has_lowercase:(true)"

    if password_complexity_has_number:
        query_params += "+password_complexity.has_number:(true)"

    if password_complexity_has_symbol:
        query_params += "+password_complexity.has_symbol:(true)"

    if password_complexity_has_uppercase:
        query_params += "+password_complexity.has_uppercase:(true)"

    if password_complexity_length:
        query_params += f"+password_complexity.length:>{password_complexity_length}"

    return query_params


def get_json_from_url(url, proxy_uri, helper, headers=None, params={}, json={}, method='GET'):
    """Creates json response from url.

    :param url: str, url to call
    :param proxy_uri: str,  proxy uri
    :param helper: Splunk helper object
    :param headers: dict, Optional custom headers
    :param params: dict, url parameters

    :return: object, json data from api mapped to equivalent python objects
    """
    headers = headers or {}
    params = copy.deepcopy(params) or {}
    proxy = {"http": proxy_uri, "https": proxy_uri}
    collect_plain_text_password = is_true(helper.get_arg('collect_plain_text_password'))

    if 'query' in params:
        updated_since = params.pop('updated_since')
        updated_until = params.pop('updated_until')
        if "basetypes:(vulnerability)" in params['query']:
            date_range = "[" + updated_since + " TO " + updated_until + "]" + \
                "|mitre.created_at.date-time:[" + \
                updated_since + " TO " + updated_until + "])"
        elif ("+_exists_:enrichments.cves" in params['query']) or \
                ("+basetypes:(credential-sighting)" in params['query']) or \
                ("+basetypes:(ransomware)" in params['query']):
            updated_since = str(int(calendar.timegm(
                (datetime.datetime.strptime(updated_since, '%Y-%m-%dT%H:%M:%S')).timetuple())))
            updated_until = str(int(calendar.timegm(
                (datetime.datetime.strptime(updated_until, '%Y-%m-%dT%H:%M:%S')).timetuple())))
            date_range = "[" + updated_since + " TO " + updated_until + "])"
        else:
            date_range = "[" + updated_since + " TO " + updated_until + "])"
        params['query'] += date_range
        params['query'] += generate_query_params(helper)
        if not collect_plain_text_password:
            params['_source_excludes'] = "body,password"

    try:
        if method == "POST":
            req = SESSION_OBJECT.post(url, headers=headers, proxies=proxy, verify=True,
                                      params=params, json=json, timeout=REQ_TIMEOUT)
        else:
            req = SESSION_OBJECT.get(url, headers=headers, proxies=proxy,
                                     verify=True, params=params, timeout=REQ_TIMEOUT)
        req.raise_for_status()
        rv = req.json()
        return rv
    except ValueError as e:
        # Response is not json serializable
        # Do actions here
        raise e
    except requests.exceptions.HTTPError as e:
        helper.log_error(
            "Error in connecting to Flashpoint API.\n{}".format(str(e)))
        raise
    except Exception as e:
        helper.log_error(
            "Unknown Error occured: {}\nTraceback: {}".format(str(e), traceback.format_exc()))
        raise


def connect_to_fpi(url, token, proxy_uri, helper, params={}, json={}, method=None):
    """Connect to ss api and returns json data.

    :param url: str
    :param token: str
    :param proxy_uri: str, proxy uri
    :param helper: Splunk helper object
    :param params: dict, url parameters

    :return: json
    """
    # construct headers
    headers = {'authorization': 'Bearer {}'.format(token),
               'X-FP-IntegrationPlatform': 'Splunk',
               'X-FP-IntegrationPlatformVersion': v.__version__,
               'X-FP-IntegrationVersion': get_app_version(helper.context_meta["session_key"]),
               }

    rv = get_json_from_url(url, proxy_uri, helper, headers, params, json, method=method)

    return rv


def get_app_version(session_key=None):
    """Return the version of TA specified in app.conf."""
    app_conf = read_conf_file(session_key, "app", stanza="launcher")
    return app_conf.get("version")


def get_checkpoint(helper, checkpoint_name):
    """Function to get checkpoint.

    :param helper: object, splunk helper object
    :param checkpoint_name: str, name of checkpoint

    :return checkpoint: str, return checkpoint if stored else start_date
    """
    checkpoint = helper.get_check_point(checkpoint_name)
    if checkpoint:
        return str(checkpoint)
    else:
        start_date = helper.get_arg('start_date')
        return start_date


def format_proxy_uri(proxy_dict):
    """Function to get proxy uri in below format.

    <protocol>://<user_name>:<password>@<proxy_server_ip>:<proxy_port>

    :param proxy_dict: dict, Dictionary containing proxy information

    :return: proxy_uri: str, proxy uri in standard format
    """
    uname = requests.compat.quote_plus(proxy_dict.get('proxy_username', ''))
    passwd = requests.compat.quote_plus(proxy_dict.get('proxy_password', ''))
    protocol = proxy_dict.get('proxy_type')
    proxy_url = proxy_dict.get('proxy_url')
    proxy_port = proxy_dict.get('proxy_port')
    proxy_uri = "%s://%s:%s@%s:%s" % (protocol,
                                      uname, passwd, proxy_url, proxy_port)

    return proxy_uri


def write_events(helper, ew, formatted_events, event_type):
    """Write formatted events to splunk.

    :param helper: object, splunk helper object
    :param ew: object, Splunk event writer
    :param formatted_events: list, List of formatted events
    :param event_type: str, Type of events (reports/indicators/cves/mentions)

    :return: None
    """
    source_type = "flashpoint_intelligence"
    if event_type != "indicators":
        source_type = "flashpoint_intelligence:" + event_type

    for item in formatted_events:
        if source_type == "flashpoint_intelligence:ransomware":
            # Check if collect_enrichments is enabled for this input
            collect_enrichments = helper.get_arg('collect_enrichments')
            if not collect_enrichments or collect_enrichments == "0":
                item.pop('enrichments', None)
        event_time = None
        try:
            event_time = get_event_time(item, event_type)
        except Exception as ex:
            helper.log_error('Error occured while extracting event timestamp: type={} error={}'.format(
                event_type, ex
            ))

        item["vendor_product"] = "Flashpoint"
        item["product_version"] = "4.5.23"
        if item.get("sightings"):
            dvc = []
            signature = []
            for sighting in item["sightings"]:
                if sighting.get("source"):
                    dvc.append(sighting["source"])
                if sighting.get("tags"):
                    for tag in sighting["tags"]:
                        tag_detail = tag.split(":")
                        tag_name = tag_detail[0]
                        if tag_name == "malware" and len(tag_detail) > 1:
                            signature.append(tag_detail[1])

            item["signature"] = signature
            item["dvc"] = dvc

        try:
            event = helper.new_event(
                source=helper.get_input_type(),
                index=helper.get_output_index(),
                sourcetype=source_type,
                time=event_time,
                data=json.dumps(item, ensure_ascii=False),
            )
            ew.write_event(event)
        except Exception as e:
            raise Exception("Error while writing event for type = {}.\n Error: {}".format(
                event_type, str(e)))


def read_conf_file(session_key, conf_file, stanza=None):
    """
    Get conf file content with conf_manager.

    :param session_key: Splunk session key
    :param conf_file: conf file name
    :param stanza: If stanza name is present then return only that stanza,
                    otherwise return all stanza
    """
    conf_file = conf_manager.ConfManager(
        session_key,
        TA_NAME,
        realm="__REST_CREDENTIAL__#{}#configs/conf-{}".format(TA_NAME, conf_file),
    ).get_conf(conf_file)

    if stanza:
        return conf_file.get(stanza)
    return conf_file.get_all()
