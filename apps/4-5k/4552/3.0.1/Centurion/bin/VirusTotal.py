import json
import time
import sys
import os
from variables import virustotalkey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class VirusTotalCommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        ip_score_list = []
        category_str = None
        average_threat_score = 0
        proxy_username = 'NA'
        proxy_pass = 'NA'
        country = "NA"

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

            url = 'https://www.virustotal.com/vtapi/v2/ip-address/report'
            params = {'apikey': virustotalkey, 'ip': ip_address}
            headers = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "virus_total", params, url, headers)
            logger = setup_logger()
            if res.status_code == 204:
                ip_details_dict = "You are making more requests than allowed.Daily quotas" \
                                  " are reset every day at 00:00 UTC."
                logger.error("You are making more requests than allowed.Daily quotas"
                             " are reset every day at 00:00 UTC.")

            elif res.status_code == 400:
                ip_details_dict = "Bad request. Caused by missing arguments or arguments with wrong values."
                logger.error("Bad request. Caused by missing arguments or arguments with wrong values.")

            elif res.status_code == 403:
                ip_details_dict = "You don't have enough privileges to make the request." \
                                  "requesting without providing an API key or with a Private API"
                logger.error("You don't have enough privileges to make the request. "
                             "requesting without providing an API key or with a Private API")

            # in case of success
            elif res.status_code == 200:
                response_json = res.json()

                if 'country' in response_json:
                    country = response_json['country']
                else:
                    country = "NA"

                # getting data from the returned json response and storing it into the index
                if "detected_downloaded_samples" in response_json:
                    for i in range(len(response_json["detected_downloaded_samples"])):
                        ip_score_list.append(response_json['detected_downloaded_samples'][i]["positives"])
                if "detected_urls" in response_json:
                    for i in range(len(response_json["detected_urls"])):
                        ip_score_list.append(response_json['detected_urls'][i]["positives"])
                if "undetected_downloaded_samples" in response_json:
                    for i in range(len(response_json["undetected_downloaded_samples"])):
                        ip_score_list.append(response_json['undetected_downloaded_samples'][i]["positives"])

                # giving score out of 10, anything greater than 10 will be considered as 10
                if len(ip_score_list) > 0:
                    if max(ip_score_list) > 0:
                        average_threat_score = sum(ip_score_list) / len(ip_score_list)
                    if average_threat_score > 10:
                        average_threat_score = 10
                else:
                    average_threat_score = 0

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "VirusTotal" + " | " +\
                                  "Reputation:" + str(average_threat_score) + " | " + "Reason:" + str(category_str) + \
                                  " | " + "Country:" + str(country) + " | "
                # writing data into the index
                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript','sourcetype': 'iocdata', 'index': index_name,
                       "IPAddress": str(ip_address),"IOCProvider": "VirusTotal", "Reason": category_str,
                       "Reputation": average_threat_score, "Country": country}
                sys.exit()

            else:
                ip_details_dict = "VirusTotal response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("VirusTotal response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("VirusTotal Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(VirusTotalCommand, sys.argv, sys.stdin, sys.stdout, __name__)
