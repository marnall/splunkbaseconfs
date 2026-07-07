import json
import time
import sys
import os
from variables import blacklistMaster_username, blacklistMaster_pass, index_name
from api_call import GetIOCScoreFromAPI

splunkhome = os.environ['SPLUNK_HOME']
sys.path.append(os.path.join(splunkhome, 'etc', 'apps', 'Centurion', 'lib'))
from error_logging import setup_logger, ipv4_check
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

# __author__ = 'Ekta Siwani'
# __version__ = '1.1.0'


@Configuration()
class BlacklistMasterCommand(GeneratingCommand):
    ip = Option(
        # Syntax: **  ip =  < ip_address >
        # Description: ** Name of the field that will hold the ip address used for hunting
        require=True)

    def generate(self):
        # variable declaration
        country = "NA"
        risk_score = 0
        proxy_username = 'NA'
        proxy_pass = 'NA'
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

            url = 'https://www.blacklistmaster.com/restapi/v0/blacklistcheck/ip/'+ip_address
            username = blacklistMaster_username
            password = blacklistMaster_pass
            params = None
            headers = None

            # Make api call to get reputation
            get_ioc_score_from_api = GetIOCScoreFromAPI()
            res = get_ioc_score_from_api.get_score(proxy_username, proxy_pass, "Blacklist Master", params, url, headers, username, password)
            logger = setup_logger()
            str_response = res.text

            if res.status_code == 200:
                json_response = json.loads(str_response)

                if "status" in json_response:
                    if json_response["status"] == "Blacklisted":
                        if "blacklist_severity" in json_response:
                            category = "BlackListed"
                            if json_response["blacklist_severity"] == "High":
                                risk_score = 10
                            elif json_response["blacklist_severity"] == "Medium":
                                risk_score = 6
                        else:
                            risk_score = 4
                            category = "BlackListed"
                    else:
                        risk_score = 0
                        category = "Not BlackListed"

                    ip_details_dict = "IPAddress:" + str(ip_address) + " | " + "IOCProvider:" + "BlackListMaster" + \
                                      " | " + "Reputation:" + str(risk_score) + " | " + "Reason:" + category + " | " + \
                                      "Country:" + country + " | "

                    index_to_write = self.service.indexes[index_name]
                    index_to_write.submit(event=str(ip_details_dict), sourcetype="iocdata", source="PythonScript")

                    yield {'_time': time.time(), '_raw': ip_details_dict, 'source': 'PythonScript',
                           'sourcetype': 'iocdata', 'index': index_name,
                           "IPAddress": str(ip_address), "IOCProvider": "BlackListMaster", "Reason": category,
                           "Reputation": risk_score, "Country": country}
                    sys.exit()

                else:
                    ip_details_dict = "BlackListMaster Api OOPS! Some Unknown Exception " + str(json_response)
                    logger.error("BlackListMaster Api OOPS! Some Unknown Exception for ip %s : %s" %
                                 (str(ip_address), str(json_response)))

            elif res.status_code == 429:
                ip_details_dict = "BlackListMaster Api OOPS! Too many requests, Your Free Trial is Over"
                logger.error("BlackListMaster Api OOPS! Too many requests, Your Free Trial is Over, ip searched : %s" % (str(ip_address)))

            elif res.status_code == 406:
                ip_details_dict = "Blacklist Master: Invalid IP address"
                logger.error("Blacklist Master: Invalid IP address for IP address %s is: %s" % (str(ip_address), str(res.text)))

            elif res.status_code == 401:
                ip_details_dict = "Blacklist Master: Not authorize to search IP address"
                logger.error("Blacklist Master: Not authorize to search IP address %s is: %s" % (str(ip_address), str(res.text)))

            elif res.status_code == 400:
                ip_details_dict = "Blacklist Master: Bad request for IP address"
                logger.error("Blacklist Master: Bad request for IP address %s is: %s" % (str(ip_address), str(res.text)))

            elif res.status_code == 402:
                ip_details_dict = "Blacklist Master: No API calls left, please renew your subscription"
                logger.error("Blacklist Master: No API calls left, please renew your subscription"
                             " to search IP address %s is: %s" % (str(ip_address), str(res.text)))

            elif res.status_code == 204:
                ip_details_dict = "Blacklist Master: IP address does not exist"
                logger.error("Blacklist Master: IP address %s does not exist: %s" % (str(ip_address), str(res.text)))

            else:
                ip_details_dict = "BlackListMaster response status is: " + str(res.status_code) + " and error msg is: " + str(res.text)
                logger.error("BlackListMaster response status for IP address %s is: %s and error msg is: %s" %
                             (str(ip_address), str(res.status_code), str(res.text)))

            yield {'_time': time.time(), '_raw': ip_details_dict}

        except Exception as e:
            logger = setup_logger()
            logger.error("BlackListMaster Api General Exception for IP Address %s is : %s" % (str(ip_address), str(e)))


dispatch(BlacklistMasterCommand, sys.argv, sys.stdin, sys.stdout, __name__)