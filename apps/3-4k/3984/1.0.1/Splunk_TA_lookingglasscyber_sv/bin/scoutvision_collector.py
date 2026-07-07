from scoutvision import Scout, Project, Tag, Tagging, Export, IPAddress, DNS, Search
from json import dumps, loads
import argparse
from multiprocessing import Process, Queue
import os
import sys
import ConfigParser
import csv
from datetime import datetime
import logging, logging.handlers
from requests import get, post
from splunk import getLocalServerInfo
import splunk.entity as entity
from re import compile, split

try:
    from splunk.clilib import cli_common as cli
    import splunk
except:
    pass

VERBOSE = True

SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))
APP_DIR = os.path.dirname(SCRIPT_DIR)


def setup_logging():
    logger = logging.getLogger('splunk.sv_logger')

    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')

    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "scoutvision_collector.log"
    maxBytes = 10000000
    backupCount = 4

    BASE_LOG_PATH = os.path.join(APP_DIR, 'logs')

    if not os.path.exists(BASE_LOG_PATH):
        os.makedirs(BASE_LOG_PATH)

    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH,
                                                                           LOGGING_FILE_NAME), mode='a',
                                                              maxBytes=int(maxBytes), backupCount=int(backupCount))
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

    apikeyconf = {}

    localconfpath = os.path.join(appdir, "local", "splunk_sv.conf")

    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    else:
        apikeyconfpath = os.path.join(appdir, "default", "splunk_sv.conf")
        apikeyconf = cli.readConfFile(apikeyconfpath)

    return apikeyconf[stanza]


def valid_ip(ip_addr):
    valid_ipv4_address = True

    ip_period_pattern = r'\.'
    ip_period_char = compile(ip_period_pattern)

    ipv4_address_pattern = ''

    octet_count = 1

    for octet in split(ip_period_char, ip_addr):
        if len(octet) == 3:
            ipv4_address_pattern = r'^(1[0-9][0-9]|2[0-4][0-9]|2[5][0-5])'
        elif len(octet) == 2:
            ipv4_address_pattern = r'^[1-9][0-9]'
        elif len(octet) == 1 and octet_count == 1:
            ipv4_address_pattern = r'^[1-9]'
        elif len(octet) == 1:
            ipv4_address_pattern = r'^[0-9]'
        else:
            valid_ipv4_address = False

        octet_count += 1
        ipv4_address = compile(ipv4_address_pattern)

        if not ipv4_address.match(octet):
            valid_ipv4_address = False
            break

    return valid_ipv4_address


def getfile(hConfigFile):
    if not os.path.exists(hConfigFile):
        raise IOError('Config file not found - %s' % hConfigFile)
    config = ConfigParser.RawConfigParser()
    config.read(hConfigFile)

    return config.get('ScoutParams', 'filepath')


def merge_two_dicts(x, y):
    z = x.copy()   # start with x's keys and values
    z.update(y)    # modifies z with y's keys and values & returns None
    return z


def IP_ResultWorker( queue, finished ):
    out_dict = {}

    item = queue.get()
    while not item is None:
        try:
            out_dict[item[0]].append((item[1], item[2], item[3]))
        except:
            out_dict[item[0]] = [(item[1], item[2], item[3])]
        item = queue.get()

    finished.put(out_dict)


def IP_Worker(id_num, config, project, data_queue, data_queue2, out_queue):
    s2 = Scout('https://' + config["svhost"] + "/api", api_token=config['api_key'])
    sv_ip = IPAddress(s2)
    sv_dns = DNS(s2)
    sv_search = Search(s2)
    sv_tagging = Tagging(s2)
    s2.verbose = VERBOSE

    # Get an IP from the queue of IPs
    ip = data_queue.get()

    # As long as we are not at the end of the queue, get data about element
    while ip is not None:
        hold = {}
        ip_info = sv_ip.overview(ip[0], fulldata=True)
        tag = ip[1]

        try:
            for threat in ip_info['threat_indicators']:
                if threat['id'] == ip[1]:
                    hold[tag] = {}
                    hold[tag]["attribute_list"] = {}
                    for attr in threat["attribute_list"]:
                        hold[tag]["attribute_list"][attr[0]] = attr[1]
                    hold[tag]["classification_list"] = []
                    for classification in threat["classification_list"]:
                        hold[tag]["classification_list"].append(classification["classification"])
                    hold[tag]["criticality"] = threat["criticality"]
                    hold[tag]['timestamp'] = ip[2]
        except KeyError, ValueError:
            if logger:
                logger.info("Could not get metadata for %s." % ip[0])
            hold[tag] = {"attribute_list": {}, "classification_list": [], "criticality": 50, "timestamp": ip[2]}

        out_queue.put((ip[0], hold, ip[3], ip[4]))
        # Get next IP in queue
        ip = data_queue.get()

    # Get an IP from the queue of IPs
    dom = data_queue2.get()

    # As long as we are not at the end of the queue, get data about element
    while dom is not None:
        try:
            hold = {}

            dns_info = sv_dns.get_dns(dom[0], fulldata=True)

            tag = dom[1]

            for threat in dns_info['threat_indicators']:
                if threat['id'] == tag:
                    hold[tag] = {}
                    hold[tag]["attribute_list"] = {}
                    for attr in threat["attribute_list"]:
                        hold[tag]["attribute_list"][attr[0]] = attr[1]
                    hold[tag]["classification_list"] = []
                    for classification in threat["classification_list"]:
                        hold[tag]["classification_list"].append(classification["classification"])
                    hold[tag]["criticality"] = threat["criticality"]
                    hold[tag]['timestamp'] = dom[2]

            out_queue.put((dom[0], hold, "", ""))

        except:
            if logger:
                logger.info("Could not get data for %s." % dom[0])

            hold = {}
            domain_tags = []
            domain_tags = sv_tagging.list( "dns/%s" % dom[0], allinclusive=True )
            for domain_tag in domain_tags:
                if domain_tag['tag']['type'] == 'system':
                    qid = sv_search.create_query( "indicator_s:'%s'" % domain_tag['tag']['name'] )
                    results = sv_search.get_query_page( qid, page=1, per_page=1, fulldata=True )
                    score = None
                    for item in results['search_results']:
                        if 'threat_indicators' in item.keys():
                            for ti in item['threat_indicators']:
                                if ti['id'] == domain_tag['tag']['name']:
                                    tag = dom[1]
                                    hold[tag] = {}
                                    hold[tag]["attribute_list"] = {}
                                    hold[tag]["classification_list"] = []
                                    for classification in ti["classification_list"]:
                                        hold[tag]["classification_list"].append(classification["classification"])
                                    hold[tag]["criticality"] = ti['criticality']
                                    hold[tag]['timestamp'] = dom[2]

            out_queue.put((dom[0], hold, "", ""))

        # Get next IP in queue
        dom = data_queue2.get()

    s2.logout()


def get_project_sets(config, project, project_tag_list, system_tag_list):
    if logger:
        logger.info("Getting SV project data...")

    def TagWorker(id, queue, results):
        s = Scout('https://' + config["svhost"] + "/api", api_token=config['api_key'])
        s.verbose = VERBOSE
        sv_tag = Tag(s)
        sv_project = Project(s)

        ip_list = set()

        if sv_project.find_and_set_current(project):
            item = queue.get()
            while not item is None:
                project_tag = item[0]
                sys_tag = item[1]

                try:
                    inherited_ips = sv_tag.view_sub_tag_items(sys_tag,
                                                              "tag/%s" % project_tag)["items"].get("ip_address", [])

                    for inherited_ip in inherited_ips:
                        ip_list.add(inherited_ip["ip_address"]["address"])

                    if ip_list:
                        results.put((ip_list, project_tag))
                except:
                    pass

                item = queue.get()

        try:
            s.logout()
        except:
            pass

        if logger:
            logger.info("TagWorker-%s finished." % id)

    def ResultWorker(queue, finished):
        ip_set = dict()

        item = queue.get()
        while not item is None:
            try:
                ip_set[item[1]] |= item[0]
            except:
                ip_set[item[1]] = item[0]
            item = queue.get()

        finished.put(ip_set)

    num_tag_threads = 10

    tag_queue = Queue()
    result_queue = Queue()
    finished_queue = Queue()

    if logger:
        logger.info("Starting ResultWorker...")

    result_worker = Process(target=ResultWorker, args=(result_queue, finished_queue))
    result_worker.daemon = True
    result_worker.start()

    if logger:
        logger.info("Starting TagWorkers...")

    tag_threads = []
    for i in range(num_tag_threads):
        tag_threads.append(Process(target=TagWorker, args=(i+1, tag_queue, result_queue)))
        tag_threads[i].start()

    for ptag in project_tag_list:
        for stag in system_tag_list:
            tag_queue.put((ptag, stag))

    for t in tag_threads:
        tag_queue.put(None)

    for t in tag_threads:
        t.join()

    if logger:
        logger.info("TagWorkers finished...")

    result_queue.put(None)
#    result_worker.join()

    ip_set = finished_queue.get()

    return ip_set


class ScoutvisionCollector(object):
    def __init__(self, config):
        if logger:
            logger.info("ScoutvisionCollector started...")

        self.config = config
        self.project = config["svproject"].replace(" ,", ",").replace(", ", ",").split(",")

        current_script_dir = os.path.dirname(os.path.realpath(__file__))
        appdir = os.path.dirname(current_script_dir)

        self.csv_file_path = os.path.join(appdir, "csv_reports")
        self.data_file_path = os.path.join(appdir, "json_data")
        self.data_filename = os.path.join(self.data_file_path, "sv_data.json")

        self.delimiter = "|||||"

        if not os.path.exists(self.csv_file_path):
            os.makedirs(self.csv_file_path)

        if not os.path.exists(self.data_file_path):
            os.makedirs(self.data_file_path)

#    instantiate the connection to SV and download the latest SV system tag file
    def _get_system_tag_file(self):
        if logger:
            logger.info("Downloading csv report.")

#        instantiate the SV objects
        sv = Scout('https://' + self.config["svhost"] + "/api", api_token=self.config['api_key'])
        sv.verbose = VERBOSE
        sv_export = Export(sv)

        result = sv_export.latest_ip_csv_report(self.csv_file_path)

        try:
            os.rename(result, os.path.join(self.csv_file_path, 'ip_csv_report.csv'))
        except OSError:
            if logger:
                logger.info("IP CSV Report not updated...")

        result = sv_export.latest_domain_csv_report(self.csv_file_path)

        try:
            os.rename(result, os.path.join(self.csv_file_path, 'domain_csv_report.csv'))
        except OSError:
            if logger:
                logger.info("Domain CSV Report not updated...")

        sv.logout()

    @property
    def gather_events(self):
        self._get_system_tag_file()

        if logger:
            logger.info("Gathering events...")

        s = Scout('https://' + self.config["svhost"] + "/api", api_token=self.config['api_key'])
        s.verbose = VERBOSE
        sv_project = Project(s)
        sv_tag = Tag(s)
        sv_tagging = Tagging(s)
        sv_export = Export(s)

        ip_file = os.path.join(self.csv_file_path, 'ip_csv_report.csv')
        domain_file = os.path.join(self.csv_file_path, 'domain_csv_report.csv')

        events = []

        exclude_list = [
            "[LG] Anonymous Proxy",
            "[LG] Corporate Proxy",
            "[LG] Probing Darknet",
            "[DShield] Daily Sources",
            "[DSHIELD] Daily Sources"
        ]

        system_tags = {}
        domain_system_tags = {}
        set_domains = []
        ip_set = dict()
        dns_set = dict()
        dns_projects = dict()

        domains = []
        for project in self.project:
            if sv_project.find_and_set_current(project):
                project_tags = [i["tag"]["tag"] for i in sv_tagging.summary() if not "Shodan" in i ["tag"]["tag"] or "shodan" in i ["tag"]["tag"]]
                
                for t in project_tags:
                    for domain in sv_tag.view_tag_items(t, entity_type="dns"):
                        domains.append(domain['tag']['entity']['dns']['fqdn'])
                        set_domains.append(domain['tag']['entity']['dns']['fqdn'])

                    dns_set[t] = set(set_domains)
                    set_domains = []
                
                dns_projects[project] = dns_set
                
        with open(ip_file, "r") as file:
            reader = csv.reader(file)

            for row in reader:
                try:
                    timestamp, action, ip, system_tag, _, _ = row
                    if not system_tag in exclude_list:
                        if action == "add":
                            if system_tag not in system_tags.keys() and not "Shodan" in system_tag and not "shodan" in system_tag:
                                system_tags[system_tag] = {"ips": [ip], "timestamp": timestamp}
                            else:
                                system_tags[system_tag]["ips"].append(ip)
                except ValueError:
                    if logger:
                        logger.info("Error parsing ip_csv_report line.")

        with open(domain_file, "r") as file:
            reader = csv.reader(file)

            for row in reader:
                try:
                    timestamp, action, dom, system_tag, _, _ = row
                    if action == "add":
                        if dom in domains: 
                            if system_tag in domain_system_tags.keys() and not system_tag in exclude_list:
                                try:
                                    domain_system_tags[system_tag]["domains"].append(dom)
                                except KeyError:
                                    domain_system_tags[system_tag]["domains"] = []
                                    domain_system_tags[system_tag]["domains"].append(dom)
                            else:
                                domain_system_tags[system_tag] = {"domains": [dom], "timestamp": timestamp}
                except ValueError:
                    if logger:
                        logger.info("Error parsing domain_csv_report line.")

        for project in self.project:
            if sv_project.find_and_set_current(project):
                project_tags = [i["tag"]["tag"] for i in sv_tagging.summary() if not "Shodan" in i ["tag"]["tag"] or "shodan" in i ["tag"]["tag"]]
                ip_set[project] = get_project_sets(self.config, project, project_tags, system_tags)

        ip_queue = Queue()
        domain_queue = Queue()
        out_queue = Queue()
        finished = Queue()

        NUM_THREADS = 10
        threads = []

        # Create threads for Domain and IP metadata gathering
        if logger:
            logger.info("Starting IP_Workers...")

        for i in range(NUM_THREADS):
            threads.append(Process(target=IP_Worker, args=(i+1, self.config, self.project, ip_queue, domain_queue, out_queue)))
            threads[i].start()

        if logger:
            logger.info("Starting IP_ResultWorker...")

        result_worker = Process(target=IP_ResultWorker, args=(out_queue, finished))
        result_worker.daemon = True
        result_worker.start()

        # Add IP and Domain Data to each queue, end each queue with None to kill each thread
        for sTag in system_tags.keys():
            for ip in system_tags[sTag]["ips"]:
                for proj in ip_set.keys():
                    for projTag in ip_set[proj].keys():
                        if ip in ip_set[proj][projTag]:
                            ip_queue.put((ip, sTag, system_tags[sTag]['timestamp'], projTag, proj))

        for sTag in domain_system_tags.keys():
            for domain in domain_system_tags[sTag]["domains"]:
                logger.info('Domain - %s' % domain)
                domain_queue.put((domain, sTag, domain_system_tags[sTag]["timestamp"]))

        for i in range(NUM_THREADS):
            ip_queue.put(None)
            domain_queue.put(None)

        # Wait for all threads to finish then join them together
        for t in threads:
            t.join()

        if logger:
            logger.info("IP_Workers finished.")

        out_queue.put(None)

        if logger:
            logger.info("Parsing events...")
        event = []
        events = []
        ip_dict = finished.get()
        for ip in ip_dict:
            for indicator_set in ip_dict[ip]:
                indicator_item = indicator_set[0]
                projectTag = indicator_set[1]
                project = indicator_set[2]
                for stag in indicator_item:
                    timestamp = indicator_item[stag]["timestamp"]
                    timestamp = datetime.strptime(timestamp, "%Y%m%d %H:%M:%S %Z").strftime("%Y-%m-%d %H:%M:%S")

                    feed_source_tag = stag.split('] ')

                    feed_source_tag_name = r'N/A'

                    if feed_source_tag[0].startswith('['):
                        feed_source_tag_name = feed_source_tag[0] + r']'

                    event_metadata = {}
                    event_metadata = {k: v for k, v in indicator_item[stag]["attribute_list"].iteritems()}

                    if valid_ip(ip):
                        event_data = {
                            "src_ip": ip,
                            "date": timestamp,
                            "category": ",".join(indicator_item[stag]["classification_list"]),
                            "sv_tag": stag,
                            "sv_tag_source": feed_source_tag_name,
                            "sv_project": project,
                            "sv_project_tag": projectTag,
                            "criticality": indicator_item[stag]["criticality"],
                            "vendor": 'LookingGlass Cyber',
                            "product": "ScoutVision"
                        }

                        events.append(merge_two_dicts(event_data, event_metadata))
                    else:
                        for dns_project in dns_projects.keys():
                            for dns_project_tags in dns_projects[dns_project]:
                                if ip in dns_projects[dns_project][dns_project_tags]:
                                    event_data = {
                                        "src_name": ip,
                                        "date": timestamp,
                                        "category": ",".join(indicator_item[stag]["classification_list"]),
                                        "sv_tag": stag,
                                        "sv_tag_source": feed_source_tag_name,
                                        "sv_project": dns_project,
                                        "sv_project_tag": dns_project_tags,
                                        "criticality": indicator_item[stag]["criticality"],
                                        "vendor": 'LookingGlass Cyber',
                                        "product": "ScoutVision"
                                    }

                                    events.append(merge_two_dicts(event_data, event_metadata))
        if logger:
            logger.info("Finished.  Parsed %s events." % len(events))

        s.logout()
        return events


def getCredentials(splunk_session_key, api_user, app_name):
    if len(splunk_session_key) == 0:
        sys.stderr.write("Did not receive a session key from splunkd. " +
                         "Please enable passAuth in inputs.conf for this " +
                         "script\n")
        exit(2)
    try:
        # list all credentials
        entities = entity.getEntities(['admin', 'passwords'], namespace=app_name,
                                      owner='nobody', sessionKey=splunk_session_key)
    except Exception, e:
        raise Exception("Could not get %s credentials from splunk. Error: %s" % (app_name, str(e)))

    # return first set of credentials
    for i, c in entities.items():
        if c['username'] == api_user:
            return c['clear_password']


if __name__ == '__main__':
    import ConfigParser

    svc_config = ConfigParser.RawConfigParser()
    svc_config.optionxform = str

    if os.path.isfile(os.path.join(APP_DIR, "local", "splunk_sv.conf")):
        svc_config.read(os.path.join(APP_DIR, "local", "splunk_sv.conf"))
    else:
        svc_config.read(os.path.join(APP_DIR, "default", "splunk_sv.conf"))

    cf = {}
    default_cf = {}

    for section in svc_config.sections():
        cf = dict(svc_config.items(section))

    VERBOSE = True

    try:
        if int(cf["enable_sv"]) == 1:
            api_key_user = 'sv_api'
            app_name = 'Splunk_TA_lookingglasscyber_sv'

            # read session key sent from splunkd
            sessionKey = sys.stdin.readline().strip()

            if len(sessionKey) == 0:
                sys.stderr.write("Did not receive a session key from splunkd. " +
                                 "Please enable passAuth in inputs.conf for this " +
                                 "script\n")
                exit(2)

            # now get the stored credentials from Splunk
            api_key = getCredentials(sessionKey, api_key_user, app_name)

            cf['api_key'] = api_key

            svc = ScoutvisionCollector(cf)
            results = svc.gather_events

            for result in results:
                print(dumps(result))
        else:
            exit(0)
    except:
        svc_config_default = ConfigParser.RawConfigParser()
        svc_config_default.optionxform = str
        svc_config_default.read(os.path.join(APP_DIR, "default", "splunk_sv.conf"))

        for section in svc_config_default.sections():
            default_cf = dict(svc_config_default.items(section))

            if int(default_cf["enable_sv"]) == 1:
                api_key_user = 'sv_api'
                app_name = 'Splunk_TA_lookingglasscyber_sv'

                # read session key sent from splunkd
                sessionKey = sys.stdin.readline().strip()

                if len(sessionKey) == 0:
                    sys.stderr.write("Did not receive a session key from splunkd. " +
                                     "Please enable passAuth in inputs.conf for this " +
                                     "script\n")
                    exit(2)

                # now get the stored credentials from Splunk
                api_key = getCredentials(sessionKey, api_key_user, app_name)

                cf['api_key'] = api_key

                svc = ScoutvisionCollector(cf)
                results = svc.gather_events

                for result in results:
                    print(dumps(result))
            else:
                exit(0)
