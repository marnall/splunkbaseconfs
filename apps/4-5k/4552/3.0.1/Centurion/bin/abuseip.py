import json
import time
import sys
import os
from variables import abuseipkey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class AbuseIPCommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        category_list = []
        risk_score = 0
        categories = 'NA'
        country = "NA"
        categories_dict = {3: "Fraud Orders", 4: "DDoS Attack", 5: "FTP Brute-Force", 6: "Ping of Death",
                           7: "Phishing", 8: "Fraud VoIP", 9: "Open Proxy", 10: "Web Spam",
                           11: "Email Spam", 12: "Blog Spam", 13: "VPN IP", 14: "Port Scan",
                           15: "Hacking", 16: "SQL Injection", 17: "Spoofing", 18: "Brute-Force",
                           19: "Bad Web Bot", 20: "Exploited Host",
                           21: "Web App Attack", 22: "SSH", 23: "IoT Targeted"}
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

            url = 'https://api.abuseipdb.com/api/v2/check'
            params = {'ipAddress': ip_address,
                      'verbose': True, 'maxAgeInDays': 90}

            headers = {'Key': abuseipkey, 'Accept': 'application/json'}

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Abuse IP", params, url, headers)
            logger = setup_logger()
            str_res = res.text

            if res.status_code == 503:
                ip_details_dict = "Service Unavailable"
                logger.error("AbuseIP response status for IP address %s is: %s and error msg is: Service Unavailable" %
                             (str(ip_address), str(res.status_code)))

            elif res.status_code == 200:
                ip_details_dict = "NA"
                json_response = json.loads(str_res)

                if len(json_response) > 0:
                    if "countryName" in json_response["data"]:
                        country = json_response["data"]["countryName"]
                    else:
                        country = "NA"

                    if "abuseConfidenceScore" in json_response["data"]:
                        risk_score = int(json_response["data"]["abuseConfidenceScore"])
                        if risk_score > 10:
                            risk_score = 10
                    else:
                        risk_score = 0

                    for i in range(len(json_response["data"]["reports"])):
                        category_list.append(json_response["data"]["reports"][i]["categories"])
                        flat_list = []
                        if risk_score > 0:
                            categories = ""
                            for sublist in category_list:
                                for j in sublist:
                                    flat_list.append(j)

                            flat_list = set(flat_list)

                            for k in flat_list:
                                categories = categories + categories_dict[k] + ","
                            categories = categories.strip(",")

                    ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "AbuseIP" + " | " + \
                                      "Reputation:" + str(risk_score) + " | " + "Reason:" + str(categories) + " | " + \
                                      "Country:" + country + "|"

                    index_to_write = self.service.indexes[index_name]
                    index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                    yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript',
                           'sourcetype': 'iocdata', 'index': index_name, "IPAddress": str(ip_address),
                           "IOCProvider": "AbuseIP", "Reason": categories, "Reputation": risk_score,
                           "Country": country}
                    sys.exit()

            else:
                ip_details_dict = "AbuseIP response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("AbuseIP response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("AbuseIP Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(AbuseIPCommand, sys.argv, sys.stdin, sys.stdout, __name__)