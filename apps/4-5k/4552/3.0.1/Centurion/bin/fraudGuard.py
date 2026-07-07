import json
import time
import sys
import os
from variables import fraudGuard_user, fraudGuard_pass, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'

@Configuration()
class FraudGuardAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        proxy_username = 'NA'
        proxy_pass = 'NA'
        risk_score = 0
        category = "NA"
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

            url = 'https://api.fraudguard.io/v2/ip/' + ip_address
            username = fraudGuard_user
            password = fraudGuard_pass
            params = None
            headers = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Fraud Guard", params, url, headers, username, password)
            logger = setup_logger()
            str_response = res.text

            if res.status_code == 200:
                json_response = json.loads(str_response)

                if 'country' in json_response:
                    country = json_response["country"]

                if "risk_level" in json_response:
                    risk_score = json_response["risk_level"]
                    category = json_response["threat"]

                else:
                    logger.warning("OOPS! There is no information about this IP in FraudGuard, ip searched : %s" % (str(ip_address)))
                    sys.exit()

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "FraudGuard" + " | " + \
                                  "Reputation:" + str(risk_score) + " | " + "Reason:" + category + " | " + \
                                  "Country:" + country + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "FraudGuard",
                       "Reason": category, "Reputation": risk_score, "Country": country}

                sys.exit()

            elif res.status_code == 429:
                ip_details_dict = "Fraud Guard: You've exceeded the number of API requests allocated in your pricing plan."
                logger.error("Fraud Guard: You've exceeded the number of API requests allocated in your pricing plan,"
                             " ip searched : %s" % (str(ip_address)))

            elif res.status_code == 401:
                ip_details_dict = "Fraud Guard: Your login credentials are invalid"
                logger.error("Fraud Guard: Your login credentials are invalid, ip searched : %s" % (str(ip_address)))

            elif res.status_code == 503:
                ip_details_dict = "Fraud Guard: We're temporarily offline for maintenance."
                logger.error("Fraud Guard: We're temporarily offline for maintenance."
                             " Please try again later, ip searched : %s" % (str(ip_address)))

            elif res.status_code == 400:
                ip_details_dict = "Fraud Guard: Your request is invalid for IP address. response: " + str(res.text)
                logger.error("Fraud Guard: Your request is invalid for IP address %s is: %s" % (str(ip_address), str(res.text)))

            elif res.status_code == 500:
                ip_details_dict = "Fraud Guard: Internal Server Error " + str(res.text)
                logger.error("Fraud Guard: Internal Server Error, searched IP address %s is: %s" % (str(ip_address), str(res.text)))

            else:
                ip_details_dict = "Fraud Guard response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("Fraud Guard: response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Fraud Guard Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(FraudGuardAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)