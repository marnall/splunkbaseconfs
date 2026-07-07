import sys
import json
import base64
import datetime
import requests


# local imports
import riskiq_common_utility as util
import riskiq_constants as constants
from riskiq_assets_utils import create_splunk_events, MainThread
try:
    from urllib import quote  # Python 2.X
except ImportError:
    from urllib.parse import quote  # Python 3+


def create_filter(command, status, start_time='', end_time=''):
    """
    Method to create filters for API request.

    :param command: Filter command related to GI assets.
    :param status: Filter for state.
    :param start_time: Filter for start time. Defaults to ''.
    :param end_time: Filter for end time. Defaults to ''.
    :return: filter dictionary.
    """
    filters = {'filters': {
        'condition': 'AND',
        'value': [{'operator': 'EQ', 'name': 'type', 'value': command},
                  {'operator': 'EQ', 'name': 'state', 'value': status}
                  ]}}
    if start_time != '':
        filters['filters']['value'].append(
            {'operator': 'GTE', 'name': 'updatedAt', 'value': start_time})
    if end_time != '':
        filters['filters']['value'].append(
            {'operator': 'LTE', 'name': 'updatedAt', 'value': end_time})
    return(filters)


COMMANDS = (('IP_BLOCKS', create_filter('IP_BLOCK', 'CONFIRMED')),
            ('HOSTS', create_filter('HOST', 'CONFIRMED')),
            ('CERTS', create_filter('SSL_CERT', 'CONFIRMED')),
            ('ASNS', create_filter('AS', 'CONFIRMED')),
            ('DOMAINS', create_filter('DOMAIN', 'CONFIRMED')),
            ('MAIL', create_filter('MAIL_SERVER', 'CONFIRMED')),
            ('NS', create_filter('NAME_SERVER', 'CONFIRMED')),
            ('CONTACTS', create_filter('CONTACT', 'CONFIRMED')),
            ('IP_ADDRESS', create_filter('IP_ADDRESS', 'CONFIRMED')),
            ('PAGES', create_filter('PAGE', 'CONFIRMED')))

CHANGED_ASSESTS_COMMANDS = (('CHANGED_IP_BLOCKS', 'IP_BLOCK'),
                            ('CHANGED_HOSTS', 'HOST'),
                            ('CHANGED_CERTS', 'SSL_CERT'),
                            ('CHANGED_ASNS', 'AS'),
                            ('CHANGED_DOMAINS', 'DOMAIN'),
                            ('CHANGED_MAIL', 'MAIL_SERVER'),
                            ('CHANGED_NS', 'NAME_SERVER'),
                            ('CHANGED_CONTACTS', 'CONTACT'),
                            ('CHANGED_IP_ADDRESS', 'IP_ADDRESS'),
                            ('CHANGED_PAGES', 'PAGE'))


def format_event(helper, event):
    """Remove unwanted fields and some formatting.

    1. remove data points without current=true
    2. For asset type "PAGE" 'responseBodyMinhashSignatures', 'fullDomMinhashSignatures'
       fields value list trimmed to first 2 value
    3. Remove fields for asset type
        "PAGE": responseBodies
        "IP_ADDRESS": banners
    4. Skip asset type "SSL_CERT" as it does not contain any data point
    5. Combine webComponent name and version
    Parameters
    ----------
    event : dict
        Event to be formated
    """
    try:
        asset_type = event['type']
        if asset_type == 'SSL_CERT':
            return

        for key, value in event['asset'].items():
            if isinstance(value, list):
                for item in value[:]:
                    if item.get('current', False) is False and \
                        ('firstSeen' in item
                         or key in ["webComponents", "assetSecurityPolicies"]):
                        value.remove(item)

        keys = ['responseBodyMinhashSignatures', 'fullDomMinhashSignatures']

        if asset_type == "PAGE":
            for key in keys:
                if event.get('asset'):
                    for item in event.get('asset').get(key):
                        item['values'] = item['values'][:2]
            event['asset']['responseBodies'] = []

        elif asset_type == "IP_ADDRESS":
            for item in event['asset'].get('services', []):
                banners = [banner for banner in item.get('banners', []) if banner.get(
                    'scanType', '') not in ['http', 'tls', 'udp']]
                item['banners'] = banners

        # Combine webComponent name and version
        for item in event.get('asset').get('webComponents', []):
            item['webComponentNameVersion'] = " ".join(
                [item.get('webComponentName'),
                    item.get('webComponentVersion')]) if item.get('webComponentVersion') \
                else item.get('webComponentName')

    except Exception as e:
        helper.log_info("Error in event formation: " + str(e))


def retrieve_assets(helper, ew, **kwargs):
    """
    Method to fetch assets from RiskIQ API endpoint and ingest them into Splunk.

    :param helper: Splunk helper class.
    :param ew: Splunk event writer class.
    :kwargs: url, js, category, filters.
    :return: result count.
    """
    global_account = helper.get_arg('global_account')
    token = global_account['api_key'].strip()
    key = global_account['api_secret'].strip()
    customer = global_account['customer_name'].strip()
    page_size = helper.get_arg('page_size').strip()
    session_key = helper.context_meta['session_key']
    url = kwargs['url']
    js = kwargs['js']
    category = kwargs['category']
    tags_filter = kwargs.get('tags_filter', None)
    org_filter = kwargs.get('org_filter', None)
    brands_filter = kwargs.get('brands_filter', None)
    if customer.strip() == "":
        helper.log_error("Customer name cannot be empty")
        return -1
    proxies = util.get_proxy_uri(session_key)
    client_token = (token + ":" + key).encode()
    base64_client_token = base64.b64encode(client_token)
    b_more = True
    mark = "*"
    event_count = 0
    n_report = 0
    attempt = 0
    if tags_filter:
        tags_filter = tags_filter.split(",")
        js['filters']['value'].append(
            {'operator': 'IN', 'name': 'tag', 'value': tags_filter})
    if brands_filter:
        brands_filter = brands_filter.split(",")
        js['filters']['value'].append(
            {'operator': 'IN', 'name': 'brand', 'value': brands_filter})
    if org_filter:
        org_filter = org_filter.split(",")
        js['filters']['value'].append(
            {'operator': 'IN', 'name': 'organization', 'value': org_filter})
    while b_more:
        start_time = datetime.datetime.now()
        retry = False
        theurl = '{}?global=false&mark={}&size={}'.format(
            url, quote(mark), page_size)
        try:
            headers = {"Authorization": "Basic " + base64_client_token.decode(),
                       "Content-Type": "application/json"}
            helper.log_debug(
                "Final URL RiskIQ API call: {}".format(str(theurl)))
            helper.log_debug(
                "Final filters for RiskIQ API call: {}".format(str(js)))
            api_call_start_time = datetime.datetime.now()
            response = requests.post(url=theurl,
                                     headers=headers,
                                     data=json.dumps(js),
                                     verify=constants.SSL_VERIFY,
                                     proxies=proxies)
            api_call_end_time = datetime.datetime.now()
            helper.log_debug("RiskIQ API call time duration is {} seconds".format(
                str((api_call_end_time - api_call_start_time).seconds)))
        except Exception as e:
            helper.log_warning('API request failed: {0}'.format(str(e)))
            retry = True

        if response:
            try:
                response.raise_for_status()
            except Exception as e:
                helper.log_warning(
                    'Unexpected response code {0}'.format(str(e)))
                helper.log_warning('Response:{0}'.format(repr(response)))
                retry = True

            # Result is dict with keys: content page last
            helper.log_debug('Decode JSON response')
            try:
                result = response.json()
            except Exception:
                helper.log_warning(
                    'Could not interpret json response from {0}'.format(theurl))
                helper.log_warning('Response:{0}'.format(repr(response)))
                retry = True

        if retry:
            attempt += 1
            if attempt > 5:
                helper.log_error(
                    "API request failed 5 times. These assets will be collected in next collection.")
                return(-1)
            helper.log_info("Retry number: " + str(attempt))
            continue
        content = result['content']
        event_count += len(content)

        for event in content:
            try:
                event['assetName'] = event.pop('name')
            except Exception:
                event['assetName'] = ""
            format_event(helper, event)
            n_report = create_splunk_events(
                helper,
                event,
                ew,
                customer,
                constants.GLOBAL_INVENTORY_ASSETS_SOURCE,
                n_report,
                delim=";;")
        end_time = datetime.datetime.now()
        helper.log_info("Number of assets indexed for {} are {}".format(
            category, str(event_count)))
        helper.log_debug("Total time duration is {} seconds".format(
            str((end_time - start_time).seconds)))
        if not result['last']:
            try:
                mark = result['mark']
            except KeyError:
                helper.log_error(
                    "No mark found for Pagination. These assets will be collected in next collection.")
                return(-1)
        else:
            b_more = False
        attempt = 0
    return(event_count)


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def collect_events(helper, ew):
    """Splunk default collect event method for core logic of data collection and ingestion."""
    only_changed_assets, conf_time = util.get_only_changed_assets_fields(
        helper)
    tags_filter, brands_filter, org_filter = util.get_data_filters(helper)

    if only_changed_assets:
        checkpoint_file = 'last_changed_gi_assets'
        filters = CHANGED_ASSESTS_COMMANDS
    else:
        checkpoint_file = 'last_gi_assets'
        filters = COMMANDS

    arg_dict = {
        "url": constants.GLOBAL_INVENTORY_ASSETS_URL,
        "retrieve_assets": retrieve_assets,
        "create_filter": create_filter,
        "only_changed_assets": only_changed_assets,
        "checkpoint_file": checkpoint_file,
        "commands": filters,
        "tags_filter": tags_filter,
        "brands_filter": brands_filter,
        "org_filter": org_filter,
        "conf_time": conf_time,
        "helper": helper,
        "ew": ew
    }
    MainThread(arg_dict)
    helper.log_info('Script exiting....')
    sys.exit()
