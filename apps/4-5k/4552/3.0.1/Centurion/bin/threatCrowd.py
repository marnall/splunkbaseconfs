import json
import time
import sys
import os
from variables import index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class ThreatCrowdCommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        category = ""
        country = "NA"
        ip_score = 0
        proxy_username = 'NA'
        proxy_pass = 'NA'
        # validate ip address
        ip_address = ipv4_check(self.ip)
        try:
            # get proxy authentication info
            storage_passwords = self.service.storage_passwords
            for credentials in storage_passwords:
                usercreds = {'username': credentials.content.get('username'),
                             'password': credentials.content.get('clear_password')}

                proxy_username = usercreds['username']
                proxy_pass = usercreds['password']

            url = "http://www.threatcrowd.org/searchApi/v2/ip/report/"
            params = {"ip": ip_address}
            header = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Threat Crowd", params, url, header)
            str_response = res.text

            logger = setup_logger()
            if res.status_code == 429:
                ip_details_dict = "OOPS! Your Free Trial is Over for ThreatCrowd"
                logger.error("OOPS! Your Free Trial is Over for ThreatCrowd")

            elif res.status_code != 429 and res.status_code != 200:
                ip_details_dict = str(res.status_code) + " : " + str(str_response)
                logger.error(str(res.status_code) + " : " + str(str_response))

            elif res.status_code == 200:
                json_response = json.loads(str_response)

                if "votes" in json_response:
                    if json_response["votes"] == -1:
                        ip_score = 8
                        category = ''

                    elif json_response["votes"] == 0:
                        ip_score = 5
                        category = ''
                    else:
                        ip_score = 0
                        category = ''

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "ThreatCrowd" + " | " + "Reputation:" + str(ip_score) + " | " + "Reason:" + str(category) + " | " + "Country:" + str(country) + "|"

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "ThreatCrowd",
                       "Reason": category, "Reputation": str(ip_score), "Country": country}

                sys.exit()

            else:
                ip_details_dict = "Threat Crowd response status: " + str(res.status) + " and error msg is: " + str(res.text)
                logger.error("Threat Crowd response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Threat Crowd Api General Exception for IP Address: %s" % (str(e)))


dispatch(ThreatCrowdCommand, sys.argv, sys.stdin, sys.stdout, __name__)