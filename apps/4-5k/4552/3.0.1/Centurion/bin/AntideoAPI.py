import json
import time
import sys
import os
from variables import Antideokey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class AntideoAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        category = ''
        score = 0
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
            params = None
            url_health = "https://api.antideo.com/ip/health/" + ip_address
            url_location = "https://api.antideo.com/ip/location/" + ip_address

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res_health = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Antideo", params, url_health)
            res_location = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Antideo", params, url_location)
            logger = setup_logger()

            # getting location of the ip address
            if res_location.status_code == 200:
                data = res_location.text
                json_response = json.loads(data)

                if 'location' in json_response:
                    country = json_response['location']['country']
            else:
                logger.warning("Antideo response status for IP address %s is: %s and error msg is: %s" %
                               (str(ip_address), str(res_location.status_code), str(res_location.text)))

            # getting reputation of the ip address
            if res_health.status_code == 200:
                data = res_health.text
                json_response = json.loads(data)

                for i in json_response["health"]:
                    if json_response["health"][i] is not False:
                        category = category + str(i) + ','
                        if i == "toxic":
                            score = score + 5
                        else:
                            score = score + 2.5
                    else:
                        score = score + 0
                category = category.strip(',')

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "Antideo" + " | " + "Reputation:" + str(score) + " | " + "Reason:" + category + " | " + "Country:" + country + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript','sourcetype': 'iocdata', 'index': index_name,
                   "IPAddress": str(ip_address),"IOCProvider": "Antideo", "Reason": category, "Reputation": score, "Country": country}

                sys.exit()

            else:
                ip_details_dict = "Antideo response status " + str(res_health.status_code) + "and error msg is: " + str(res_health.text)
                logger.error("Antideo response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res_health.status_code), str(res_health.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Antideo Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(AntideoAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)
