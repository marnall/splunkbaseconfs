import os
import sys
import csv
import string
import logging
import requests
import configparser

import splunk.Intersplunk
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import splunk.Intersplunk,string
import splunk.entity as entity




# def read_conf(conf_file):
#     if not os.path.exists(conf_file):
#         return False
#     else:
#         config = configparser.ConfigParser()
#         config.read(conf_file)
#         if not config.has_section('setupentity') or not config.has_option('setupentity','dod_api_key'):
#             return False
#         data = config['setupentity']
#         return data


def validate_dod_api_key(feye_auth_key):

    url_health = "https://feapi.marketplace.apps.fireeye.com/health"
    headers = {"feye-auth-key": feye_auth_key}
    parameters = {}
    try:
        response = requests.request(url="https://feapi.marketplace.apps.fireeye.com/health", method='GET',
                                    headers=headers, verify=False, timeout=3)
    except requests.exceptions.HTTPError as err:
        return False
        # raise requests.exceptions.HTTPError(
        #     "An HTTP Error occured while trygin to access the Octopus Deploy API: " + str(err))

    r_status = response.status_code
    if r_status != 200:
        # check the response status, if the status is not sucessful, raise requests.HTTPError
        # response.raise_for_status()
        return False

    r_json = response.json()
    # status_response = (json.dumps(r_json["status"]))
    status_response = r_json["status"]
    api_key_validity = r_json["api_key_valid"]
    if (status_response == "failed") or not api_key_validity:
        message_response = r_json["message"]
        # message_response = json.dumps(r_json["message"])
        # raise ValueError(message_response)
        return False

    return True

def get_credentials(session_key, app_name):

   try:
      # list all credentials
      entities = entity.getEntities(['storage', 'passwords'], namespace=app_name, 
                                    owner='nobody', sessionKey=session_key) 
   except Exception as e:
        print("Could not get %s credentials from splunk. Error: %s"
              % (app_name, str(e)))
   # return first set of credentials
   for i, c in entities.items(): 
        if c['username']=='dod_api_key': 
             return c['username'], c['clear_password']

def get_session_key(app_name, err_msg_no_key):
    try:
        #print("Getting session key")
        # read session key sent from splunkd
        results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
        session_key = settings.get("sessionKey")
        #session_key = sys.stdin.readline().strip()
        #print("Session key is :", session_key)
        if len(session_key) == 0:
            print("Did not receive a session key from splunkd. Please contact the administrator\n")
            exit(1)        
        # now get twitter credentials - might exit if no creds are available 
        username, password = get_credentials(session_key,app_name)
        return (password)
    except Exception as e:
        print(err_msg_no_key)
        return False


def write_to_csv(err_msg):
    output = csv.writer(sys.stdout)
    data = [['answer'],[err_msg]]
    output.writerows(data)


def main(report_id):

    # base_dir = make_splunkhome_path(["etc", "apps", "FireEye_v3"])
    # conf_file = 'fireeye.conf'
    # conf_dir = os.path.join(base_dir, 'local')
    # conf_path = os.path.join(conf_dir,conf_file)

    app_name = "FireEye_v3"
    parameters = {"expiry": 24}
    pre_signed_url = "https://feapi.marketplace.apps.fireeye.com/presigned-url/%s" % report_id
    err_msg_no_key =  "DOD Api key not found, please go to Help -> Configure App and provide a valid api key"
    err_msg_invalid = "DOD Api key is invalid. please go to Help -> Configure App and provide a valid api key"

    dod_api_key = get_session_key(app_name, err_msg_no_key)
    if not dod_api_key:
        exit(1)

    # conf_data = read_conf(conf_path)
    # if not conf_data:
    #     print(err_msg_no_key)
    # dod_api_key = conf_data['dod_api_key']
    # print("dod api key is: ", dod_api_key)

    if not validate_dod_api_key(dod_api_key):
        print(err_msg_invalid)
        exit(1)

    headers = {"feye-auth-key": "%s" % dod_api_key}
    # print(pre_signed_url)
    response = requests.get(pre_signed_url, params=parameters, headers=headers, timeout=5)

    if 299 >= response.status_code >= 200:
        json_response = response.json()
        status = json_response['status']

        if status != 'success':
            response.raise_for_status()

        report_link = json_response['presigned_report_url']
        write_to_csv(report_link)
        # print(report_link)

    else:
        response.raise_for_status()


if __name__ == '__main__':
    (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
    if len(sys.argv) < 2:
        splunk.Intersplunk.parseError("No arguments provided")
        sys.exit(0)

    # print(sys.argv[1])
    report_id = sys.argv[1].strip()
    # report_id = "05365743-6e32-40f6-8fea-83f54e8a888d"
    main(report_id)
