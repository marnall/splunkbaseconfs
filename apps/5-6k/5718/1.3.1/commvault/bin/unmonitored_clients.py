import json
import os
import sys
import splunk.Intersplunk
import helper
import splunklogger as SL

def write_to_file(all_client_content):
    fp = open('../local/all_unmonitored_clients.conf','w')
    fp.write('[' + commserve + ']\n')
    if all_client_content == "":
        fp.write('None\n')
    else:
        fp.write(all_client_content)
    fp.close()

try:
    SL.make_entry("unmonitored_clients", "Getting unmonitored clients")
    commserve = sys.argv[1]
    results, dr, settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']
    username,password,url = helper.get_credentials(commserve, session_key)
    json_list = []
    auth_code = helper.get_authcode(username,password,url)
    resp = helper.get_clients(auth_code,url)
    json_resp = helper.convert_to_json(resp)
    client_properties = json_resp["clientProperties"]
    all_config_clients = helper.get_configured_clients()

    if commserve in all_config_clients:
        req_client_list = all_config_clients[commserve]
    else:
        req_client_list = []

    buffered_clients = helper.get_buffered_clients()

    all_client_content = ""
    for i in client_properties:
        client_name = i["client"]["clientEntity"]["clientName"]
        if client_name not in req_client_list:
            display_name = i["client"]["clientEntity"]["displayName"]
            client_id = i["client"]["clientEntity"]["clientId"]
            host_name = i["client"]["clientEntity"]["hostName"]
            cvd_port = i["client"]["cvdPort"]
            if(cvd_port != 0):
                temp_dict = {}
                temp_dict["DisplayName"] = client_name
                all_client_content += client_name + "\n"
                temp_dict["HostName"] = host_name
                if(client_name not in buffered_clients):
                    json_list.append(temp_dict)

    write_to_file(all_client_content)
    splunk.Intersplunk.outputResults(json_list)
    SL.make_entry("unmonitored_clients", "Successfully retrieved unmonitored client list")

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = 'ERROR ' + str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("unmonitored_clients",entry_content)
