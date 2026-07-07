import json
import time
import sys
import os
from variables import neutrinouser_id, neutrinokey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class NeutrinoAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        category = ""
        country = "NA"
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
            url_for_reputation = 'https://neutrinoapi.com/ip-blocklist'
            url_for_location = 'https://neutrinoapi.com/ip-info'
            params = {'user-id': neutrinouser_id, 'api-key': neutrinokey, 'ip': ip_address}

            # Make api call to get reputation and country info
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res_score = get_ioc_score_from_api.get_score_using_urllib(proxy_username, proxy_pass, "Neutrino", params, url_for_reputation)
            res_country = get_ioc_score_from_api.get_score_using_urllib(proxy_username, proxy_pass, "Neutrino", params, url_for_location)

            logger = setup_logger()

            if res_country.getcode() == 200:
                json_response_country = json.loads(res_country.read())
                country = json_response_country["country"]
                # city = json_response_country["city"]

            else:
                logger.warning("Neutrino  response status(geo) for IP address %s is: %s and error msg is: %s" %
                               (str(ip_address), str(res_country.getcode()), str(res_country.read())))

            if res_score.getcode() == 200:
                json_response_score = json.loads(res_score.read())

                if "blocklists" in json_response_score and len(json_response_score["blocklists"]) > 0:
                    risk_score = len(json_response_score["blocklists"])

                    for i in range(len(json_response_score["blocklists"])):
                        category = category + str(json_response_score["blocklists"][i]) + ','

                    category = category.strip(",")

                else:
                    logger.warning("Neutrino response does not have block list attribute for IP address %s" % (str(ip_address)))

                ip_details_dict = "IPAddress:" + str(
                    ip_address) + " | " + "IOCProvider:" + "Neutrino" + " | " + "Reputation:" + str(
                    risk_score) + " | " + "Reason:" + category + " | " + "Country:" + country + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name,"IPAddress": str(ip_address), "IOCProvider": "Neutrino", "Reason": category, "Reputation": risk_score,
                       "Country": country}
                sys.exit()
            else:
                ip_details_dict = "Neutrino response status: " + str(res_score.getcode()) + " and error msg is: " + str(res_score.read())
                logger.warning("Neutrino response status(risk_score) for IP address %s is: %s and error msg is: %s" %
                               (str(ip_address), str(res_score.getcode()), str(res_score.read())))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Neutrino Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(NeutrinoAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)

