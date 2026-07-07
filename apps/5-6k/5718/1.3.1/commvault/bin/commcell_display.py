import splunk.Intersplunk
import splunklib.client as splunk_client
import helper
import splunklogger as SL
import os


def create_local_dir():
    if not os.path.isdir('../local'):
        os.mkdir('../local')

try:

    create_local_dir()
    try:
        fp = open("../local/commcell.conf","r")
    except Exception as excp:
        SL.make_entry("commcell_display","No commcell found")
        exit(0)

    contents = fp.read()
    commcell_list = contents.split("\n")
    SL.make_entry("commcell_display","Getting Configured commserve")
    comm_client = helper.get_configured_clients()
    processed_commcells = []
    output_list = []
    for i in range(0,len(commcell_list)-1,4):
        if(commcell_list[i] not in processed_commcells):
            record = {}
            commcell_name = commcell_list[i+1].split("=",1)[1].strip()
            username = commcell_list[i+2].split("=",1)[1]
            webserver = commcell_list[i].strip("]")
            webserver = webserver.split("[")[1]
            record["webservers"] = webserver
            record["username"] = username
            record["Commcell"] = commcell_name
            if commcell_name in comm_client.keys():
                record["MonitoredClients"] = len(comm_client[commcell_name])
            else:
                record["MonitoredClients"] = 0
            processed_commcells.append(commcell_list[i])
            output_list.append(record)

    splunk.Intersplunk.outputResults(output_list)

except Exception as excp:
    entry_content = "ERROR " + str(excp)
    SL.make_entry("commcell_display",entry_content)
