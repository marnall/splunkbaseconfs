import json
import time
import sys
import os
from variables import alienvaultkey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'

@Configuration()
class AlienVaultAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        category_str = ''
        proxy_username = 'NA'
        proxy_pass = 'NA'
        threat_score = 0
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
            url_reputation = "https://otx.alienvault.com/api/v1/indicators/IPv4/" + ip_address + "/reputation"
            url_geo = "https://otx.alienvault.com/api/v1/indicators/IPv4/" + ip_address + "/geo"
            headers = {
                'x-otx-api-key': alienvaultkey,
            }
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res_reputation = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Alien Vault", params, url_reputation, headers)
            res_geo = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Alien Vault", params, url_geo, headers)
            logger = setup_logger()
            logger.warning(self.service.apps)

            if res_geo.status_code == 200:
                # reading data that we got as a response
                str_res = res_geo.text
                json_response = json.loads(str_res)
                # get the country of the searched ip address
                if 'country_name' in json_response:
                    country = json_response['country_name']
            else:
                logger.warning("Alien Vault geo response status for IP address %s is: %s and error msg is: %s" %
                               (str(ip_address), str(res_geo.status_code), str(res_geo.text)))

            # get reputation details from the API response
            if res_reputation.status_code == 200:
                # reading data that we got as a response
                str_res = res_reputation.text
                json_response = json.loads(str_res)

                if json_response["reputation"] is not None:
                    country = json_response["reputation"]["country"]
                    threat_score = json_response["reputation"]["threat_score"]
                    category_dict = json_response["reputation"]["counts"]

                    for category in category_dict:
                        category_list.append(category)

                    category_set = set(category_list)

                    for category in category_set:
                        category_str = category_str + str(category) + " , "

                    category_str = categoryStr.strip(" , ")

                else:
                    category_str = 'NA'
                    threat_score = 0

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "AlienVault" + " | " + \
                                  "Reputation:" + str(threat_score) + " | " + "Reason:" + str(category_str) + " | " + \
                                  "Country:" + country + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "AlienVault",
                       "Reason": category_str, "Reputation": threat_score, "Country": country}

                sys.exit()
            else:
                ip_details_dict = "Alien Vault response status " +  str(res_reputation.status_code) + " and error msg is: " + str(res_reputation.text)
                logger.error("Alien Vault response status(risk_score) for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res_reputation.status_code), str(res_reputation.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Alien Vault Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(AlienVaultAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)
