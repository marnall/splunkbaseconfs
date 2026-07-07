import json
import time
import sys
import os
from variables import ipstackkey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class IPStackAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        category = ''
        risk_score = 0
        country = "NA"
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
            url = "http://api.ipstack.com/" + ip_address + "?access_key="+ipstackkey+"&security=1"
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "IP Stack", params, url)
            logger = setup_logger()
            json_response = res.json()

            if res.status_code == 200:
                if json_response["country_name"] is not None:
                    country = json_response["country_name"]

                if "security" in json_response:
                    # get the category of the threat
                    if json_response["security"]["threat_level"] is not None:
                        if json_response["security"]["threat_level"] == "medium":
                            risk_score = 4
                        elif json_response["security"]["threat_level"] == "high":
                            risk_score = 8
                        else:
                            risk_score = 0

                    # get type of the threat
                    if json_response["security"]["threat_types"] is not None:
                        for threatType in json_response["security"]["threat_types"]:
                            category = category + threatType + ","
                        category = category.strip(",")
                    else:
                        category = None

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "IPStack" + " | " +\
                                  "Reputation:" + str(risk_score) + " | " + "Reason:" + str(category) + " | " +\
                                  "Country:" + str(country) + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "IPStack", "Reason": category,
                       "Reputation": risk_score, "Country": country}
                sys.exit()

            elif json_response["error"]["code"] == 101:
                ip_details_dict = "OOPS! You have Entered Invalid API Key"
                logger.error("IPStack API Response, OOPS! You have Entered Invalid API Key for ip_address: %s" % (
                             str(ip_address)))

            elif json_response["error"]["code"] == 105:
                ip_details_dict = "The current subscription plan does not support this API endpoint:"
                logger.error("IPStack API Response, OOPS! The current "
                             "subscription plan does not support this API endpoint: %s" % (str(ip_address)))

            else:
                ip_details_dict = "IPStack API response status " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("IPStack API response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("IP Stack Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(IPStackAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)

