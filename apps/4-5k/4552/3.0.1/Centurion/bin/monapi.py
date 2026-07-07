import json
import time
import sys
import os
from variables import monapikey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class MonAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        category = ""
        proxy_username = 'NA'
        proxy_pass = 'NA'
        risk_score = 0
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

            url = 'https://api.monapi.io/v1/ip/'+ip_address
            headers = {'accept': "application/json",'authorization': monapikey}
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Mon", params, url, headers)
            logger = setup_logger()

            if res.status_code == 200:
                json_response = res.json()

                # get the risk_score of the ip address
                if "threat_level" in json_response:
                    if json_response["threat_level"] == "low":
                        risk_score = 2
                    elif json_response["threat_level"] == "medium":
                        risk_score = 5
                    else:
                        risk_score = 8

                else:
                    risk_score = 0

                # get the geo location of the ip address
                if "country" in json_response:
                    country = json_response["country"]

                # get the category of the ip address
                if "threat_class" in json_response:
                    for i in range(len(json_response["threat_class"])):
                        if category != "":
                            category = category + "," + str(json_response["threat_class"][i])
                        else:
                            category = str(json_response["threat_class"][i])
                else:
                    category = "NA"

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "Mon" + " | " + \
                                  "Reputation:" + str(risk_score) + " | " + "Reason:" + str(category) + " | " +\
                                  "Country:" + country + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "Mon", "Reason": category,
                       "Reputation": risk_score, "Country": country}
                sys.exit()

            else:
                ip_details_dict = "Mon response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("Mon response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Mon Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(MonAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)

