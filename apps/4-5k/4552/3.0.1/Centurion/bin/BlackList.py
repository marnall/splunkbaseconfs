import json
import time
import sys
import os
from variables import blacklistapikey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class BlackListAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        category_list = []
        category_str = 'Not blacklisted'
        threat_score = 0
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

            # Setting up connection with the website
            url = 'https://tony11-blacklist-ip-v1.p.rapidapi.com/ipv4/' + ip_address
            headers = {
                "X-RapidAPI-Key": blacklistapikey,
                "Content-type": "application/json"
            }
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Blacklist", params, url, headers)
            logger = setup_logger()

            if res.status_code == 202:
                str_res = res.text
                json_response = json.loads(str_res)
                logger.error(json_response)

                if "content" in json_response:
                    if json_response["content"]["blacklisted"] > 0:
                        threat_score = 5

                    if ("comment" in json_response["content"]) and (json_response["content"]["comment"] is not None):
                        category_str = jsonResponse["content"]["comment"]

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "BlackList" + " | " + "Reputation:" + str(threat_score) + " | " + "Reason:" + str(category_str) + " | " + "Country:" + str(country) + " | "
                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "BlackList",
                       "Reason": category_str,
                       "Reputation": threat_score, "Country": country}
                sys.exit()

            else:
                ip_details_dict = "Black list response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("Black list response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}


        except Exception as e:
            logger = setup_logger()
            logger.error("Black list Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(BlackListAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)











