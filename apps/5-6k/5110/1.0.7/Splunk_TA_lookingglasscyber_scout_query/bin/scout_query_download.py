from requests import codes, post
from os import path, environ, makedirs
from json import dumps
from time import sleep
from logging import getLogger, handlers, Formatter
from sys import stdin, stderr, version_info
import splunk.entity as entity
from ast import literal_eval
from datetime import datetime, timedelta

if version_info < (3, 0):
    from ConfigParser import RawConfigParser
else:
    from configparser import RawConfigParser

try:
    from splunk.clilib import cli_common as cli
    from splunk import setupSplunkLogger
except:
    pass

SCRIPT_DIR = path.dirname(path.realpath(__file__))
APP_DIR = path.dirname(SCRIPT_DIR)


def setup_logging():
    logger = getLogger('splunk.scout_query_logger')

    SPLUNK_HOME = environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')

    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "scoutquery.log"
    maxBytes = 10000000
    backupCount = 4

    BASE_LOG_PATH = path.join(APP_DIR, 'logs')

    if not path.exists(BASE_LOG_PATH):
        makedirs(BASE_LOG_PATH)

    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = handlers.RotatingFileHandler(path.join(SPLUNK_HOME, BASE_LOG_PATH,
                                                                           LOGGING_FILE_NAME), mode='a',
                                                              maxBytes=int(maxBytes), backupCount=int(backupCount))
    splunk_log_handler.setFormatter(Formatter(LOGGING_FORMAT))

    logger.addHandler(splunk_log_handler)
    setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)

    return logger

try:
    logger = setup_logging()
except:
    logger = None


def process_api_response(api_token, api_url, scout_query_str, time_interval, time_delay):
    headers = {
        "Authorization": "Bearer {}".format(api_token),
        "Content-type": "application/json",
        "User-Agent": "Splunk ScoutPrime Query",
    }

    now_to_convert = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:00.000Z')
    now_current = datetime.strptime(now_to_convert, '%Y-%m-%dT%H:%M:00.000Z')

    now_shifted = now_current - timedelta(minutes=time_delay)
    time_delta = now_shifted - timedelta(minutes=time_interval)

    epoch = datetime.utcfromtimestamp(0)

    now_milliseconds = int((now_shifted - epoch).total_seconds()) * 1000
    delta_milliseconds = int((time_delta - epoch).total_seconds()) * 1000

    data_to_add = '["between", "lastActivityAt", {}, {}]'.format(delta_milliseconds,
                                                                 now_milliseconds)
    scout_query = literal_eval(scout_query_str)
    scout_query['query'].append(literal_eval(data_to_add))

    result_to_add_to_splunk = []
    success = False
    tries = 0

    while not success and tries < 480:
        try:
            api_results = None
            result_to_add_to_splunk = []

            if 'use_proxy' in cf:
                if cf['use_proxy']:
                    if int(cf['use_proxy']) == 1:
                        proxies = {
                            'https': 'http://{}'.format(cf['use_proxy_server'])
                        }

                        if logger:
                            logger.info("Requesting data from {} for the following query: {}".format(api_url, scout_query))

                        if 'verify_ssl' in cf:
                            if cf['verify_ssl']:
                                if int(cf['verify_ssl']) == 0:
                                    api_results = post(api_url, headers=headers, data=dumps(scout_query),
                                                       proxies=proxies, verify=False)
                                else:
                                    api_results = post(api_url, headers=headers, data=dumps(scout_query), proxies=proxies)
                            else:
                                api_results = post(api_url, headers=headers, data=dumps(scout_query), proxies=proxies)
                        else:
                            api_results = post(api_url, headers=headers, data=dumps(scout_query), proxies=proxies)

                    else:
                        if logger:
                            logger.info("Requesting data from {} for the following query: {}".format(api_url, scout_query))

                        api_results = post(api_url, headers=headers, data=dumps(scout_query))
            else:
                if logger:
                    logger.info(
                        "Requesting data from {} for the following query: {}".format(api_url, scout_query))

                api_results = post(api_url, headers=headers, data=dumps(scout_query))

            if api_results.status_code == codes.ok:
                response = api_results.json()

                for line in response['results']:
                    if 'ref' in line:
                        if 'type' in line['ref']:
                            if line['ref']['type'] == 'ipv4':
                                if 'name' in line:
                                    line['src_ip'] = line.pop('name')

                            if line['ref']['type'] == 'fqdn':
                                if 'name' in line:
                                    line['src_name'] = line.pop('name')

                            if line['ref']['type'] == 'cidrv4':
                                if 'name' in line:
                                    line['src_ip'] = line.pop('name')

                    if 'ticScore' in line:
                        line['criticality'] = line.pop('ticScore')

                    if 'left' in line:
                        if 'ref' in line['left']:
                            if 'type' in line['left']['ref']:
                                if line['left']['ref']['type'] == 'ipv4':
                                    if 'name' in line['left']:
                                        line['src_ip'] = line['left'].pop('name')

                                if line['left']['ref']['type'] == 'fqdn':
                                    if 'name' in line['left']:
                                        line['src_name'] = line['left'].pop('name')

                                if line['left']['ref']['type'] == 'cidrv4':
                                    if 'name' in line['left']:
                                        line['src_ip'] = line['left'].pop('name')

                                # Remove the name from a file reference since it is an internal uuid and not a file name associated with the hash
                                if line['left']['ref']['type'] == 'file':
                                    if 'name' in line['left']:
                                        del line['left']['name']

                        if 'ticScore' in line['left']:
                            line['criticality'] = line['left'].pop('ticScore')

                            del line['left']['ref']

                        line.update(line['left'])
                        del line['left']

                    if 'right' in line:
                        if 'ref' in line['right']:
                            del line['right']['ref']
                            line.update(line['right'])

                        del line['right']

                    if 'ref' in line:
                        del line['ref']

                    line['product'] = 'ScoutPrime'
                    line['vendor'] = 'LookingGlass Cyber'

                    result_to_add_to_splunk.append(line)

                success = True
            else:
                api_results.raise_for_status()
        except:
            tries += 1

            if logger:
                logger.error('Error Processing API Response from {} with query: {}.  Trying again'.format(api_url, dumps(scout_query)), exc_info=True)

            sleep(30)

    if not success:
        if logger:
            logger.info("Failed to download and/or process the {} file after 480 tries(4 hours) - Exiting".format(api_url))

        raise Exception("Failed to download and/or process the {} file after 480 tries(4 hours) - Exiting".format(api_url))
    else:
        return result_to_add_to_splunk


if __name__ == '__main__':
    svc_config = RawConfigParser()
    svc_config.optionxform = str

    if path.isfile(path.join(APP_DIR, "local", "splunk_scout_query.conf")):
        svc_config.read(path.join(APP_DIR, "local", "splunk_scout_query.conf"))
    else:
        svc_config.read(path.join(APP_DIR, "default", "splunk_scout_query.conf"))

    cf = {}
    default_cf = {}

    for section in svc_config.sections():
        cf = dict(svc_config.items(section))

    try:
        scout_api_token = cf['scout_api_token']
        scout_api_query = cf['scout_query']

        if scout_api_token:
            query_endpoint_url = 'https://{}/api/graph/query'.format(cf['scouthost'])

            try:
                if int(cf["enable_scout"]) == 1:
                    time_interval = int(cf['time_interval'])
                    time_delay = int(cf['time_delay'])

                    if logger:
                        logger.info("Processing API Response from {}".format(query_endpoint_url))

                    json_data_to_add = process_api_response(scout_api_token, query_endpoint_url, scout_api_query, time_interval, time_delay)

                    if json_data_to_add:
                        for json_data in json_data_to_add:
                            print(dumps(json_data))

                else:
                    exit(0)
            except:
                try:
                    svc_config_default = RawConfigParser()
                    svc_config_default.optionxform = str
                    svc_config_default.read(path.join(APP_DIR, "default", "splunk_scout_query.conf"))

                    for section in svc_config_default.sections():
                        default_cf = dict(svc_config_default.items(section))

                    time_interval = int(default_cf['time_interval'])
                    time_delay = int(default_cf['time_delay'])

                    if int(default_cf["enable_scout"]) == 1:
                        if logger:
                            logger.info("Processing API Response from {}".format(query_endpoint_url))

                        if 'time_interval' in cf:
                            time_interval = int(cf['time_interval'])

                        if 'time_delay' in cf:
                            time_delay = int(cf['time_delay'])

                        json_data_to_add = process_api_response(scout_api_token, query_endpoint_url, scout_api_query, time_interval, time_delay)

                        if json_data_to_add:
                            for json_data in json_data_to_add:
                                try:
                                    print(dumps(json_data))
                                except:
                                    # Ignore cases with malformed JSON
                                    logger.info('Encountered malformed JSON with {} - Ignoring'.format(json_data))

                    else:
                        exit(0)
                except:
                    if logger:
                        logger.error('Error querying the Scout Graph API', exc_info=True)

                    exit(1)
        else:
            if logger:
                logger.error('Error authenticating the Scout Graph API.  Please validate your API Token and try '
                             'again', exc_info=True)

                exit(1)
    except:
        if logger:
            logger.error('Error querying the Scout Graph API', exc_info=True)

        exit(1)
