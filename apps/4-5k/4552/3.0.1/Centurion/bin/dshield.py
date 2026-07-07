import json
import time
import sys
import os
from variables import index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
import xmltodict
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'

@Configuration()
class DShieldAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        risk_score = 4
        country = "NA"
        category = ""
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

            url = "http://isc.sans.edu/api/ip/" + ip_address
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Dshield", params, url)

            logger = setup_logger()
            if res.status_code == 200:
                json_response = json.loads(json.dumps(xmltodict.parse(res.text)))
                if "error" in json_response["ip"]:
                    logger.error("DShield error message for %s : %s" % (str(ip_address), str(json_response["ip"]["error"])))
                    sys.exit()

                # get country information
                if "ascountry" in json_response["ip"] and json_response["ip"]["ascountry"] is not None:
                    country = json_response["ip"]["ascountry"]

                # calculate risk score
                if "threatfeeds" in json_response and json_response["ip"]["threatfeeds"] is not None:
                    if json_response["ip"]["maxrisk"] is not None and int(json_response["ip"]["maxrisk"]) > 0:
                        risk_score = 4
                    else:
                        risk_score = 2
                elif "threatfeeds" in json_response and json_response["ip"]["threatfeeds"] is None:
                    if json_response["ip"]["maxrisk"] is not None and int(json_response["ip"]["maxrisk"]) > 0:
                        risk_score = 4
                else:
                    logger.error("DShield:OOPS! returned response does not have proper information for %s" % str(ip_address))


                # create final dictionary
                ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "DShield" + " | " +\
                                  "Reputation:" + str(risk_score) + " | " + "Reason:" + category + " | " + \
                                  "Country:" + country + " | "

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name,
                       "IPAddress": str(ip_address), "IOCProvider": "DShield", "Reason": category, "Reputation": risk_score,
                       "Country": country}
                sys.exit()

            else:
                ip_details_dict = "DShield response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("DShield response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("DShield Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(DShieldAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)
