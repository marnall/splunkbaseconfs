from json import dumps, loads
import datetime
import sys
import logging, logging.handlers
import os
import splunk.entity as entity
import requests
from re import compile, sub

try:
    import splunk
    from splunk.clilib import cli_common as cli
except:
    pass

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)


def setup_logging():
    logger = logging.getLogger('splunk.ctc_logger')

    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')

    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "ctc_collector.log"

    BASE_LOG_PATH = os.path.join(APP_DIR, 'logs')

    if not os.path.exists(BASE_LOG_PATH):
        os.makedirs(BASE_LOG_PATH)

    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))

    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)

    return logger


try:
    logger = setup_logging()
except:
    logger = None


def get_app_config(stanza):
    current_script_dir = os.path.dirname(os.path.realpath(__file__))
    appdir = os.path.dirname(current_script_dir)

    apikeyconfpath = os.path.join(appdir, "default", "splunk_ctc.conf")
    apikeyconf = cli.readConfFile(apikeyconfpath)

    localconfpath = os.path.join(appdir, "local", "splunk_ctc.conf")

    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)

        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content

    return apikeyconf[stanza]


def remove_html(data_string):
    html_regex = compile('<.*?>')
    html_removed_from_data = sub(html_regex, '', data_string)

    return html_removed_from_data


class CTCCollector(object):
    def __init__(self, config, url='https://ctc-api.lookingglasscyber.com/v1/incidents/search', endpoint='Key Incident',
                 sourcetype=None):
        self.config = config

        current_script_dir = os.path.dirname(os.path.realpath(__file__))
        appdir = os.path.dirname(current_script_dir)

        # URL of API
        self.url = url

        # Splunk sourcetype to use
        self.sourcetype = sourcetype

        # API Endpoint
        self.endpoint = endpoint

        # Required Headers for API call
        self.headers = {'Content-Type': 'application/json', 'Authorization': 'Bearer {}'.format(self.config["api_key"])}

        self.response_size = 100
        self.offset = 0

        # Data for filtering the results (can be modified based on customer requests)
        self.data = {
            "fields": [
                "analysis",
                "author",
                "collector",
                "content",
                "createdOn",
                "date",
                "deliveredBy",
                "deliveredOn",
                "deliveryTags",
                "discoveredOn",
                "domain",
                "headline",
                "highlightedContent",
                "host",
                "incidentDisplayImage",
                "incidentEmailImage",
                "incidentId",
                "incidentImage",
                "incidentOwner",
                "incidentSourceImage",
                "incidentType",
                "industryTargets",
                "ipAddresses",
                "keywords",
                "language",
                "locations",
                "locationTargetTypes",
                "matchingContent",
                "miscellaneousTags",
                "postedOn",
                "processName",
                "rawContent",
                "reports",
                "riskLevel",
                "rocId",
                "rogueAppTags",
                "savedBy",
                "savedOn",
                "solution",
                "source",
                "status",
                "tags",
                "targetTerms",
                "targets",
                "targetTypes",
                "threatTerms",
                "threatTypes",
                "title",
                "tld",
                "URL",
                "viewedBy",
                "viewedOn",
                "violation",
                "WatchDeskWorkflow",
                "workHistory"
            ],
            "sortBy": [
                {
                    "field": "deliveredOn",
                    "order": "asc"
                }
            ],
            "size": self.response_size,
            "offset": self.offset,
            "filter": {
                "type": "simple",
                "queryString": "tags:{}".format(self.endpoint),
            },
            "dateRange": {
                "from": one_hour_ago,
                "to": now,
            },
            "clients": [self.config["clientid"]],
        }

        if self.endpoint == r'"Key Incident"':
            self.data["dateRange"].update({"dateField": "deliveredOn"})

            if self.sourcetype == 'lookingglasscyber_ctc_gi':
                self.data["clients"] = ['Ux5cNOT5yx3csLrORLogBMeFaARPUphOlIDb6jvSDwpWcOUmhXQcWFfp4375oujnhHulcA==']

    def get_ctc_data(self):
        total_results = 0

        if logger:
            logger.info("Getting CTC data...")
        # Make the API call and store the JSON response
        try:
            if logger:
                logger.info("Request URL: {}, Request Data: {}".format(self.url, dumps(self.data)))

            if int(cf["use_proxy"]) == 1:
                proxy_server = 'http://{}'.format(cf['use_proxy_server'])

                proxy = {
                    'https': proxy_server
                }

                while self.offset <= total_results:
                    response = requests.post(self.url, headers=self.headers, json=self.data, proxies=proxy)
                    response.raise_for_status()
                    json_response = response.json()

                    if 'totalIncidents' in json_response:
                        total_results = json_response['totalIncidents']
                        metadata = {'sourcetype': self.sourcetype}

                        for incident in json_response['incidents']:
                            if 'analysis' in incident:
                                incident['analysis'] = remove_html(incident['analysis'])
                                incident.update(metadata)
                                print(dumps(incident))
                            else:
                                incident['sourcetype'] = self.sourcetype
                                print(dumps(incident))

                        self.offset += self.response_size
                        self.data['offset'] = self.offset
                    else:
                        break

            else:
                while self.offset <= total_results:
                    response = requests.post(self.url, headers=self.headers, data=dumps(self.data))
                    response.raise_for_status()
                    json_response = response.json()

                    if 'totalIncidents' in json_response:
                        total_results = json_response['totalIncidents']

                        for incident in json_response['incidents']:
                            if 'analysis' in incident:
                                incident['analysis'] = remove_html(incident['analysis'])
                                incident['sourcetype'] = self.sourcetype
                                print(dumps(incident))
                            else:
                                incident['sourcetype'] = self.sourcetype
                                print(dumps(incident))

                        self.offset += self.response_size
                        self.data['offset'] = self.offset
                    else:
                        break

            return total_results

        except:
            if logger:
                logger.info("Error getting CTC data. %s - %s" % (sys.exc_info()[0], sys.exc_info()[1]))
            response = None


if __name__ == '__main__':
    VERBOSE = True

    cf = get_app_config('setupentity')

    one_hour_ago = (datetime.datetime.utcnow() - datetime.timedelta(hours=int(cf['ctc_hours']))).strftime(
        '%Y-%m-%dT%H:%M:%S.000Z')
    now = datetime.datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')
    today_date = datetime.date.today().strftime('%Y-%m-%d')

    if int(cf["enable_ctc"]) == 1:
        if int(cf["ctc_TM"]) == 1:
            ctc = CTCCollector(cf, endpoint=r'"Target Mention"', sourcetype='lookingglasscyber_ctc_tm')
            ctc_results = ctc.get_ctc_data()

            if logger:
                logger.info(ctc_results)
            else:
                print(ctc_results, "events")

        if int(cf["ctc_VD"]) == 1:
            ctc = CTCCollector(cf, endpoint=r'"Vetted"', sourcetype='lookingglasscyber_ctc_vd')
            ctc_results = ctc.get_ctc_data()

            if logger:
                logger.info(ctc_results)
            else:
                print(ctc_results, "events")

        if int(cf["ctc_KI"]) == 1:
            ctc = CTCCollector(cf, endpoint=r'"Key Incident"', sourcetype='lookingglasscyber_ctc_ki')
            ctc_results = ctc.get_ctc_data()

            if logger:
                logger.info(ctc_results)
            else:
                print(ctc_results, "events")

        if int(cf["ctc_GI"]) == 1:
            ctc = CTCCollector(cf,
                               endpoint=r'"Key Incident"',
                               sourcetype='lookingglasscyber_ctc_gi')

            ctc_results = ctc.get_ctc_data()

            if logger:
                logger.info(ctc_results)
            else:
                print(ctc_results, "events")

    else:
        if logger:
            msg = 'Splunk CTC Integration Disabled within the Application Setup'
            logger.info({}).format(msg)

        exit(0)
