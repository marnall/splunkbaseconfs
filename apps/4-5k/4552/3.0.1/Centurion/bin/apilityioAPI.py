import json
import time
import sys
import os
from variables import apilityioapikey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class ApilityIOAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        category = 'NA'
        risk_score = 0
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
            url = "https://api.apility.net/v2.0/ip/" + ip_address
            headers = {'Accept': 'application/json', 'X-Auth-Token': apilityioapikey}
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Apilityio", params, url, headers)
            logger = setup_logger()
            if res.status_code == 200:
                str_res = res.text
                json_response = json.loads(str_res)
                if 'geo' in json_response['fullip']:
                    country = json_response['fullip']['geo']['country_names']["en"]

                # get score of the ip address
                if 'badip' in json_response['fullip']:
                    if ('blacklists' in json_response['fullip']['badip']) and (len(json_response['fullip']['badip']["blacklists"])>0):
                        category = ""
                        for i in range(len(json_response['fullip']['badip']["blacklists"])):
                            category = str(category) + str(json_response['fullip']['badip']["blacklists"][i]) + ','
                        category = category.strip(',')

                    if 'score' in json_response['fullip']:
                        if json_response['fullip']['badip']["score"] > -1:
                            risk_score = 0
                        if json_response['fullip']['badip']["score"] < 0:
                            risk_score = 6

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "Abilityio" + " | " + \
                                  "Reason:" + str(category) + " | " + "Reputation:" + str(risk_score) + " | " + \
                                  "Country:" + country + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "Abilityio",
                       "Reason": str(category), "Reputation": str(risk_score), "Country": country}

                sys.exit()

            elif res.status_code == 401:
                ip_details_dict = "Apilityio: Unauthorized -- Your API key is wrong"
                logger.error("Apilityio: Unauthorized -- Your API key is wrong, searched for ip: %s" % (str(ip_address)))

            elif res.status_code == 403:
                ip_details_dict = "Apilityio: Forbidden -- Your API key does not have enough " \
                                  "permissions to perform the action requested"
                logger.error("Apilityio: Forbidden -- Your API key does not have enough"
                             " permissions to perform the action requested, searched for ip: %s" % (str(ip_address)))

            elif res.status_code == 429:
                ip_details_dict = "Apilityio: Too Many Requests -- You have ran out of quota."
                logger.error("Apilityio: Too Many Requests -- You have ran out of quota. "
                             "Please consider upgrading your plan, searched for ip: %s" % (str(ip_address)))

            elif res.status_code == 503:
                ip_details_dict = "Apilityio: Service Unavailable -- We're temporarily offline for maintenance."
                logger.error("Apilityio: Service Unavailable -- We're temporarily offline for maintenance. "
                             "Please try again later, searched for ip: %s" % (str(ip_address)))

            elif res.status_code == 500:
                ip_details_dict = "Apilityio: Internal Server Error -- We had a problem with our server. " \
                                  "Please report to our support team"
                logger.error("Apilityio: Internal Server Error -- We had a problem with our server."
                             "Please report to our support team, searched for ip: %s" % (str(ip_address)))

            elif res.status_code == 400:
                ip_details_dict = "Apilityio: Bad Request"
                logger.error("Apilityio: Bad Request, searched for ip: %s. error msg: %s" % (str(ip_address), str(res.text)))

            elif res.status_code == 404:
                ip_details_dict = "Apilityio: No data found for the , searched ip"
                logger.error("Apilityio: No data found for the , searched ip: %s. error msg: %s" % (str(ip_address)))

            else:
                ip_details_dict = "Apilityio response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("Apilityio response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Apilityio Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(ApilityIOAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)
