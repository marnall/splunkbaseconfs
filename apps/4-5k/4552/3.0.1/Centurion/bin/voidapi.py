import json
import time
import sys
import os
from variables import voidapikey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


@Configuration()
class VoidAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        category = ""
        country = "NA"
        proxy_pass = "NA"
        proxy_username = "NA"
        risk_score = 0
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

            url = "https://endpoint.apivoid.com/iprep/v1/pay-as-you-go/?key="+voidapikey+"&ip=" + ip_address
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "void", params, url)
            logger = setup_logger()

            str_response = res.text

            if res.status_code == 200:
                json_response = json.loads(str_response)
                if "error" not in json_response:

                    # get country field
                    if "country_name" in json_response["data"]["report"]["information"]:
                        country = json_response["data"]["report"]["information"]["country_name"]

                    # get risk score field
                    if json_response["data"]["report"]["blacklists"]["detections"] > 35:
                        risk_score = 8

                    elif json_response["data"]["report"]["blacklists"]["detections"] > 20:
                        risk_score = 5

                    elif json_response["data"]["report"]["blacklists"]["detections"] > 0:
                        risk_score = 2
                    else:
                        risk_score = 0

                    # get category field
                    if json_response["data"]["report"]["anonymity"]["is_proxy"] is True:
                        category = category + "Proxy" + ","

                    if json_response["data"]["report"]["anonymity"]["is_webproxy"] is True:
                            category = category + "Web Proxy" + ","

                    if json_response["data"]["report"]["anonymity"]["is_vpn"] is True:
                        category = category + "Vpn" + ","

                    if json_response["data"]["report"]["anonymity"]["is_hosting"] is True:
                        category = category + "Hosting" + ","

                    if json_response["data"]["report"]["anonymity"]["is_tor"] is True:
                        category = category + "Tor" + ","

                    category = category.strip(",")

                    ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "Void" + " | " + \
                                      "Reputation:" + str(risk_score) + " | " + "Reason:" + category + " | " + \
                                      "Country:" + country + " | "

                    index_to_write = self.service.indexes[index_name]
                    index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                    yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript','sourcetype': 'iocdata', 'index': index_name,
                           "IPAddress": str(ip_address),"IOCProvider": "Void", "Reason": category, "Reputation": risk_score, "Country": country}
                    sys.exit()
                else:
                    ip_details_dict = "Void Api response message:  " + str(json_response)
                    logger.error("Void Api response message for IP address %s is: %s" % (str(ip_address), str(json_response)))

            else:
                ip_details_dict = "Void Api response status " + str(res.status_code) + "and error msg is: " + str(res.text)
                logger.error("Void Api response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Void Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(VoidAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)
