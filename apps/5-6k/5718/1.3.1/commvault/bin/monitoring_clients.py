import sys
import splunk.Intersplunk
import helper
import splunklogger as SL

try:
    SL.make_entry("monitoring_clients", "Getting monitored clients list")
    commserve = sys.argv[1]
    res,d1,d2 = splunk.Intersplunk.getOrganizedResults()
    all_config_clients = helper.get_configured_clients()

    if commserve in all_config_clients:
        req_client_list = all_config_clients[commserve]
    else:
        exit(0)

    fp = open("../local/client_details.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    n = len(content_list)
    i = 0
    json_list = []
    while(i < n-1):
        if commserve in content_list[i]:
            client_name = content_list[i+1].split(":")[1].strip("\r")
            if client_name in req_client_list:
                display_name = content_list[i+3].split(":")[1].strip("\r")
                host_name = content_list[i+4].split(":")[1].strip("\r")
                client_ip = content_list[i+5].split(":")[1].strip("\r")
                os_type = content_list[i+6].split(":")[1].strip("\r")
                temp_dict = {}
                temp_dict["DisplayName"] = client_name
                temp_dict["HostName"] = host_name
                temp_dict["ClientIP"] = client_ip
                temp_dict["OSType"] = os_type
                json_list.append(temp_dict)
        i = i + 9
    splunk.Intersplunk.outputResults(json_list)
    SL.make_entry("monitoring_clients", "Successfully retrieved monitoring client list")

except Exception as excp:
    fp = open('internal_log.txt','a')
    fp.write(str(excp) + '\n')
    fp.close()
