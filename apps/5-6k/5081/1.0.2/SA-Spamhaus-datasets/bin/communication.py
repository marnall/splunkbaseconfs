import requests, sys, json, os
import logging, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from splunk.clilib import cli_common as cli

class LogHelper:
    def __init__(self, enable):
        self.enabled = enable
        if self.enabled:
            self.logger = logging.getLogger('Debug_Log')
            self.logger.setLevel(logging.DEBUG)
            fh = logging.FileHandler('/tmp/mm_sa_splunk.log')
            fh.setLevel(logging.DEBUG)
            self.logger.addHandler(fh)
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            fh.setFormatter(formatter)
            self.logger.addHandler(fh)
    def debug(self, mline):
        if self.enabled:
            self.logger.debug(mline)

# debug logger
logger = LogHelper(False)

#Spamhaus Custom Search Command for Splunk
isMemoryCacheEnabled = True

#Run only on Search Heads
@Configuration(local=True)

class SpamhausCommand(StreamingCommand):
    #known datasets: SBL, CSS, CBL, DROP, PBL, AuthBL, DBL, ZRD
    #dataset = Option(require=True, validate=None)
    dataset = Option(require=True, validate=validators.Match("validate","authbl|AuthBL|AUTHBL|sbl|SBL|XBL|xbl|PBL|pbl|zen|ZEN|DBL|dbl|ZRD|zrd"))

    def prepare(self):
        self._max_records_seconds = 60 * 2 # 2 minutes

        if isMemoryCacheEnabled:
            self._memcache = {}

    def stream(self, records):

        #read config from filesystem via REST
        var_config = cli.getConfStanza('spamhaus_setup','app_config')

        #proxy functionality
        if 'proxy_enabled' in var_config:
            proxy_enabled = var_config['proxy_enabled']
        else:
            proxy_enabled = '0'

        if 'proxy_address' in var_config:
            proxy_address = var_config['proxy_address']
        else:
            proxy_address = ''

        if 'proxy_port' in var_config:
            proxy_port = var_config['proxy_port']
        else:
            proxy_port = ''

        if 'proxy_https' in var_config:
            proxy_https = var_config['proxy_https']
        else:
            proxy_https = '0'

        if 'proxy_user' in var_config:
            proxy_user = var_config['proxy_user']
        else:
            proxy_user = ''

        if 'proxy_passw' in var_config:
            proxy_passw = var_config['proxy_passw']
        else:
            proxy_passw =''

        if proxy_enabled == '1':
            if proxy_https == '0':
                proxy_protocol = 'http'
            else:
                proxy_protocol = 'https'

            if proxy_user != '':
                proxies = {
                    "http": proxy_protocol + "://" + proxy_address + ":" + proxy_port,
                    "https": proxy_protocol + "://" + proxy_address + ":" + proxy_port,
                }
            else:
                proxies = {
                    "http": proxy_protocol + "://" + proxy_user + ":" + proxy_passw +"@" + proxy_address + ":" + proxy_port,
                    "https": proxy_protocol + "://" + proxy_user + ":" + proxy_passw +"@" + proxy_address + ":" + proxy_port,
                }

        else:
            proxies = {}

        for record in records:

            #needed if there is no response in the first Splunk result
            resp = "resp"
            respstatus = "status"
            record[resp] = ""
            record[respstatus] = ""

            fieldname = self.fieldnames[0]

            if fieldname in record:
                value = record[fieldname]
            else:
                value =''

            # skip on next record if examined value is empty
            if len(value) == 0:
                yield record
                continue

            # use cached response if available
            cache_key = value + " " + self.dataset
            cacheFound = False

            # try memcache first
            if isMemoryCacheEnabled and cache_key in self._memcache and int(time.time())-self._memcache[cache_key]["ts"] < self._max_records_seconds:
                logger.debug("Checked (MEMCACHED): " + cache_key + " (TS:" + str(int(time.time())-self._memcache[cache_key]["ts"]) + ")")
                if self._memcache[cache_key]["status"] == str(requests.codes.ok):
                    record[resp] = json.loads(self._memcache[cache_key]["value"])
                record[respstatus] = self._memcache[cache_key]["status"]
                cacheFound = True

            # cache not found, perform request and cache results (if enabled)
            if cacheFound == False:

                # REST Authorization Headers
                headers={"Accept": "application/json" }
                if len(var_config['token']) > 0:
                    headers["Authorization"] = var_config['token']

                site = "https://apibl.spamhaus.net/lookup/v1/" + self.dataset + "/" + value

                # REST Call
                try:
                    response = requests.get(site, headers=headers, timeout=10, proxies=proxies)
                    response.raise_for_status()
                except requests.exceptions.HTTPError as errh:
                    if errh.response.status_code != requests.codes.not_found: # not found in WQS
                        logger.debug("[REQUEST_ERROR] Http - " + site + ": " + str(errh))
                except requests.exceptions.ConnectionError as errc:
                    logger.debug("[REQUEST_ERROR] Connecting - " + site + ": " + str(errc))
                except requests.exceptions.Timeout as errt:
                    logger.debug("[REQUEST_ERROR] Timeout - " + site + ": " + str(errt))
                except requests.exceptions.RequestException as err:
                    logger.debug("[REQUEST_ERROR] Other - " + site + ": " + str(err))

                record[respstatus] = str(response.status_code)

                logger.debug("Checked: " + cache_key)

                cacheobj = {"_key": cache_key, "status": record[respstatus], "ts": int(time.time())}

                if response.status_code == requests.codes.ok:
                    try:
                        input_dict = json.loads(response.text)
                        if resp in input_dict:
                            record[resp] = input_dict[resp]
                            cacheobj["value"] = json.dumps(record[resp])
                    except:
                        pass # log errors?

                if isMemoryCacheEnabled:
                    self._memcache[cache_key] = cacheobj

            spamhaus_dataset_value= self.dataset
            spamhaus_dataset = "spamhaus_dataset"
            record[spamhaus_dataset] = spamhaus_dataset_value

            yield record


dispatch(SpamhausCommand, sys.argv, sys.stdin, sys.stdout, __name__)
