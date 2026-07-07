#!/usr/bin/python3
# Parts of this have been copied from Splunks DNSLookup and other examples.
# You can sumbit up to 25 "resources" to VT, however this script does not do that.
import os
import sys
import requests
import configparser
import re, collections, json, csv, sys, urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, \
    urllib.parse
import splunk.Intersplunk, string
import splunk.entity as entity
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


def makehash():
    return collections.defaultdict(makehash)


# def read_conf(conf_file):
#     if not os.path.exists(conf_file):
#         return False
#     else:
#         config = configparser.ConfigParser()
#         config.read(conf_file)
#         if not config.has_section('setupentity') or not config.has_option('setupentity','vt_api_key'):
#             return False
#         data = config['setupentity']
#         return data

def hashlookup(md5, vt_key, err_msg):
    try:
        # vt_report_api_url = "https://www.virustotal.com/vtapi/v2/file/report"
        vt_report_api_url = "https://www.virustotal.com/api/v3/files/%s"% md5
        headers = {'x-apikey': '%s' % vt_key}
        # params = {'apikey': '%s' % vt_key, 'resource': '%s' % md5}
        response = requests.get(vt_report_api_url, headers=headers)
        # print(md5, response.status_code)
        # print(response.json())
        if 299 >= response.status_code >= 200:
            return response.json()
        if response.status_code == 404:
            return response.json()
        print(err_msg)
        exit(1)
    except Exception as err:
        return err


def urllookup(url, vt_key, err_msg):
    try:
        # vt_report_api_url = "https://www.virustotal.com/vtapi/v2/url/report"
        vt_report_api_url = "https://www.virustotal.com/api/v3/files/%s"% url
        headers = {'x-apikey': '%s' % vt_key }
        # params = {'apikey': '%s' % vt_key, 'resource': '%s' % url}
        response = requests.get(vt_report_api_url, headers=headers)
        # print(md5sum, response.headers)
        if 299 >= response.status_code >= 200:
            return response.json()
        if response.status_code == 404:
            return response.json()
        print(err_msg)
        exit(1)
    except Exception as err:
        return err


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
        if c['username'] == 'vt_api_key':
            return c['username'], c['clear_password']


def get_session_key(app_name, err_msg_no_key):
    try:
        # print("Getting session key")
        # read session key sent from splunkd
        results, dummy, settings = splunk.Intersplunk.getOrganizedResults()
        session_key = settings.get("sessionKey")
        # session_key = sys.stdin.readline().strip()
        # print("Session key is :", session_key)
        if len(session_key) == 0:
            print("Did not receive a session key from splunkd. Please contact the administrator\n")
            exit(1)

        # now get twitter credentials - might exit if no creds are available 
        username, password = get_credentials(session_key, app_name)
        return (password)
    except Exception as e:
        print(err_msg_no_key)
        return False

def write_to_csv(result_json):
    output = csv.writer(sys.stdout)
    data = [['vt'], [result_json]]
    output.writerows(data)


def main():
    (isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
    if len(sys.argv) < 2:
        splunk.Intersplunk.parseError("No arguments provided")
        # print "python vt.py MD5 VT"
        sys.exit(0)

    err_msg_no_key = "VT Api key not found, please go to Help -> Configure App and provide a valid api key"
    err_msg_invalid = "VT Api key is invalid. please go to Help -> Configure App and provide a valid api key"

    app_name = "FireEye_v3"
    vt_api_key = get_session_key(app_name, err_msg_no_key)
    if not vt_api_key:
        exit(1)

    # base_dir = make_splunkhome_path(["etc", "apps", "FireEye_v3"])
    # conf_file = 'fireeye.conf'
    # conf_dir = os.path.join(base_dir, 'local')
    # conf_path = os.path.join(conf_dir, conf_file)

    # conf_data = read_conf(conf_path)
    # if not conf_data:
    #     print(err_msg_no_key)

    # vt_api_key = conf_data['vt_api_key']

    # print (vt_api_key)
    userinput = sys.argv[1].strip()
    # userinput = '57f222d8fbe0e290b4bf8eaa994ac641'
    if (re.findall(r"(^[a-fA-F\d]{32})", userinput)):
        md5f = userinput
        result_json = hashlookup(md5f, vt_api_key, err_msg_invalid)
    else:
        urlf = userinput
        result_json = urllookup(urlf, vt_api_key, err_msg_invalid)
    write_to_csv(result_json)


main()
