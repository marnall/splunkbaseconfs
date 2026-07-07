import json
import time
import sys
import os
from variables import ibmxforce_user, ibmxforce_pass, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators


# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class IBMXForceCommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        category = "NA"
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

            url = 'https://api.xforce.ibmcloud.com/ipr/history/'+ip_address
            header = None
            params = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "IBM X-Force", params, url, header, ibmxforce_user, ibmxforce_pass)
            logger = setup_logger()

            if res.status_code == 200:
                str_response = res.text
                json_response = json.loads(str_response)
                if 'history' in json_response:
                    # get the country
                    if 'geo' in json_response['history'][0]:
                        country = json_response['history'][0]['geo']['country']

                    if 'reason' in json_response['history'][0]:
                        category = json_response['history'][0]['reason']

                    if 'score' in json_response['history'][0]:
                        risk_score = json_response['history'][0]['score']

                ip_details_dict = "IPAddress:" + ip_address + " | " + "IOCProvider:" + "IBMX-Force" + " | " + \
                                  "Reason:" + category + " | " + "Reputation:" + str(risk_score) + " | " + \
                                  "Country:" + country

                index_to_write = self.service.indexes[index_name]
                index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript', 'sourcetype': 'iocdata',
                       'index': index_name, 'IPAddress': ip_address, "IOCProvider": "IBMX-Force", "Reason": category,
                       "Reputation": str(risk_score), "Country": country}
                sys.exit()

            else:
                ip_details_dict = "IBM X-Force response status: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("IBM X-Force response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("IBM X-Force Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(IBMXForceCommand, sys.argv, sys.stdin, sys.stdout, __name__)
