import json
import time
import sys
import os
from variables import hetrixtoolskey, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class HetrixToolAPICommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        proxy_username = 'NA'
        proxy_pass = 'NA'
        risk_score = 0
        category = "NA"

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

            url = "https://api.hetrixtools.com/v2/"+hetrixtoolskey+"/blacklist-check/ipv4/" + ip_address + "/"
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Hetrix tool", params, url)
            logger = setup_logger()
            if res.status_code == 200:
                str_response = res.text
                json_response = json.loads(str_response)

                if "status" in json_response:
                    # if status of returned response is error
                    if json_response["status"] == "ERROR":
                        ip_details_dict = "Hetrix tool: ERROR : " + str(json_response["error_message"])
                        logger.error("Hetrix tool: ERROR for IP address %s is: %s" % (str(ip_address), str(json_response["error_message"])))

                    # if status of returned response is success
                    elif json_response["status"] == "SUCCESS":
                        if json_response["blacklisted_count"] > 0:
                            risk_score = 8
                            category = "BlackListed"

                        else:
                            risk_score = 0
                            category = "Not BlackListed"

                        ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "HetrixTool" + " | "\
                                          + "Reputation:" + str(risk_score) + " | " + "Reason:" + category + " | " + \
                                          "Country:" + country + " | "

                        index_to_write = self.service.indexes[index_name]
                        index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                        yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript',
                               'sourcetype': 'iocdata', 'index': index_name, "IPAddress": str(ip_address),
                               "IOCProvider": "HetrixTool", "Reason": category, "Reputation": risk_score,
                               "Country": country}
                        sys.exit()
                    else:
                        ip_details_dict = "Hetrix tool: Oops! unexpected response from the API" + str(json_response)
                        logger.error("Hetrix tool: Oops! unexpected response of the API for %s is: %s" %
                                     (str(ip_address), str(json_response)))
                else:
                    ip_details_dict = "Hetrix tool: Oops! unexpected response from the API" + str(json_response)
                    logger.error("Hetrix tool: Oops! unexpected response of the API for %s is: %s" % (str(ip_address), str(json_response)))

            else:
                ip_details_dict = "Hetrix tool response status: " + str(res.status) + " and error msg is: " + str(res.text)
                logger.error("Hetrix tool response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("Hetrix tool Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(HetrixToolAPICommand, sys.argv, sys.stdin, sys.stdout, __name__)
