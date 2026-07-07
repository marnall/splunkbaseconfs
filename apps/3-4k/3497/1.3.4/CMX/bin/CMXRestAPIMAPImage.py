import logging
import os
import sys
from logging.handlers import RotatingFileHandler
import json

import splunk.search as splunk_search
import requests
from requests.auth import HTTPBasicAuth
import splunk.rest


splunk_home = os.environ['SPLUNK_HOME']


def get_logger(logger_id):
    maxbytes = 2000000

    log_path = splunk_home + '/var/log/CMX'

    if not (os.path.isdir(log_path)):
        os.makedirs(log_path)

    handler = RotatingFileHandler(log_path + '/cmx.log', maxBytes = maxbytes, backupCount = 20)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger = logging.getLogger(logger_id)
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


logger = get_logger("RESTIMAGEMAP")
session_key = sys.stdin.readline().strip()
protocol = "https://"

def get_image(loginurl, username, password, verify_cert = True):
    try:
        r = requests.get(url = loginurl, auth = HTTPBasicAuth(username, password), verify = verify_cert)
        return r

    except Exception:
        logger.error("Error in login", exc_info = True)
        print "STATUS UNKNOWN-In valid web proxy IP or Web proxy is not responding."
        sys.exit(3)


if __name__ == '__main__':
    try:
        r = splunk.rest.simpleRequest(
            "/services/cmx/cmximagemapendpoint?output_mode=json", session_key, method = 'GET')

        conf_dict = {}
        result = json.loads(r[1])
        inputargs = {}
        if 200 <= int(r[0]["status"]) <= 300:
            inputargs = result["entry"][0]["content"]

        verify_cert = not (bool(int(inputargs.get("ALLSSC", 0))))


        url = protocol + inputargs[
                "RESTSERVER"] + "/api/config/v1/maps/image/"


        r = splunk.rest.simpleRequest("/servicesNS/nobody/CMX/storage/passwords?output_mode=json&search=CMX",
                                      session_key,
                                      method = 'GET')
        if 200 <= int(r[0]["status"]) <= 300:
            result_data = json.loads(r[1])

            user_name = ""
            password = ""
            if len(result_data["entry"]) > 0:
                for ele in result_data["entry"]:
                    if ele["content"]["realm"] == "CMX":
                        password = ele["content"]["clear_password"]
                        user_name = ele["content"]["username"]
                        break

        search = "| savedsearch \"Get_Campus_Details\""
        results = splunk_search.searchAll(search, earliest_time = "-60m", latest_time = "+5m", sessionKey = session_key,
                                          namespace = "CMX")

        search = "|inputlookup CampusImageLookup"
        results = splunk_search.searchAll(search, earliest_time = "-60m", latest_time = "+5m", sessionKey = session_key)

        # Need to set the sessionKey (input.submit() doesn't allow passing the sessionKey)

        if results is not None:
            for i, x in enumerate(results):
                campus = x['CampusName']
                building = x['BuildingName']
                floor = x['FloorName']
                image_name = x['image_name']

                r = get_image(url + str(campus) + "/" + str(building) + "/" + str(floor), user_name, password,
                              verify_cert)

                path = splunk_home + "/etc/apps/CMX/static/" + str(image_name)
                if r.status_code == 200:
                    with open(path, 'wb') as f:
                        for chunk in r:
                            f.write(chunk)
    except Exception, err:
        logger.error("Error in RESTMAP", exc_info = True)
