import json
import time
import sys
import os
from variables import ipdatacokey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


def get_ip_scores(ip_threat):
    try:
        score = 0
        if ip_threat["is_tor"]:
            score += (10 / 7)

        if ip_threat["is_proxy"]:
            score += (10 / 7)

        if ip_threat["is_known_attacker"]:
            score += (10 / 7)

        if ip_threat["is_known_abuser"]:
            score += (10 / 7)

        if ip_threat["is_anonymous"]:
            score += (10 / 7)

        if ip_threat["is_threat"]:
            score += (10 / 7)

        if ip_threat["is_bogon"]:
            score += (10 / 7)
        return score

    except Exception as e:
        logger = setup_logger()
        logger.error("IPDataCo Api General Exception while calculating risk_score for IP Address %s is : %s"
                     % (str(ip_address), str(e)))
        sys.exit()


@Configuration()
class IPDataCoCommand(GeneratingCommand):
    ip = Option(require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        risk_score = 0
        category = []
        string_category = 'NA'
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

            url = 'https://api.ipdata.co/' + ip_address
            params = {'api-key': ipdatacokey}
            headers = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "IPDataCo", params, url, headers)
            logger = setup_logger()

            # in case of success
            if res.status_code == 200:
                response_json = res.json()

                # getting country info
                if "country_name" in response_json:
                    country = response_json["country_name"]

                # getting category and risk_score
                if response_json["threat"]:
                    risk_score = get_ip_scores(response_json["threat"])

                    for key in response_json["threat"]:
                        if response_json["threat"][key]:
                            category.append(key)

                        string_category = ''
                        for i in range(len(category)):
                            if i == len(category)-1:
                                string_category = string_category + str(category[i])
                            else:
                                string_category = string_category + str(category[i]) + ","

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "IPDataCo" + " | " + \
                                  "Reason:" + string_category + " | " + "Country:" + country + \
                                  " | " + "Reputation:" + str(risk_score)

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, "IPAddress": str(ip_address), "IOCProvider": "IPDataCo",
                       "Reason": string_category, "Reputation": risk_score, "Country": country}

                sys.exit()

            else:
                ip_details_dict = "IPDataCo response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("IPDataCo response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("IPDataCo Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(IPDataCoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
