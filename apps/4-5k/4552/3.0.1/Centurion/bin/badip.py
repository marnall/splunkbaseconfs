import json
import time
import sys
import os
from variables import index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'

@Configuration()
class BadIPCommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        category_str = ''
        average_score = 0
        total_score = 0
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
            url = "https://www.badips.com/get/info/" + ip_address
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Bad IP", params, url)
            logger = setup_logger()
            if res.status_code == 200:
                str_response = res.text
                json_response = json.loads(str_response)
                if "Listed" in json_response:
                    if json_response["Listed"] is True:
                        if (json_response["Whois"] is not None) and (json_response["Whois"] is not "null"):
                            if "country" in json_response["Whois"]:
                                country = json_response["Whois"]["country"]
                        elif "CountryCode" in json_response and ((json_response["CountryCode"] is not "null") and (json_response["CountryCode"] is not None)):
                            country = json_response["CountryCode"]
                        else:
                            country = "NA"

                        if "Categories" in json_response:
                            category = json_response["Categories"]
                            for i in category:
                                total_score = total_score + json_response["Score"][i]
                                average_score = round(total_score / len(category),2)

                            for i in range(len(category)):
                                category_str = category_str + category[i] + ","

                            category_str = category_str.strip(",")

                    else:
                        category_str = 'Not listed as bad IP'

                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "BadIP" + " | " + \
                                  "Reputation:" + str(average_score) + " | " + "Reason:" + category_str + " | " + \
                                  "Country:" + country + " |"

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name,
                       "IPAddress": str(ip_address), "IOCProvider": "BadIP", "Reason": category_str, "Reputation": average_score,
                       "Country": country}
                sys.exit()

            else:
                ip_details_dict = "Bad IP response status: " + str(res.status_code) + "and error msg is: " + str(res.text)
                logger.error("Bad IP response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), st(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Bad IP Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(BadIPCommand, sys.argv, sys.stdin, sys.stdout, __name__)
