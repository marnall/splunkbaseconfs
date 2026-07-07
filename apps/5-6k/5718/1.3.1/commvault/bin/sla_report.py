import splunk.Intersplunk
import helper
import splunklogger as SL
import sys

try:
    fp = open("../local/commcell.conf","r")
    contents = fp.read()
    content_list = contents.split("\n")
    processed_commcell = []
    output_list = []

    commcell_name = ""

    for i in range(0,len(content_list)-1,4):
        commcell_name = content_list[i+1].split("=",1)[1].strip()

    if commcell_name == "":
        SL.make_entry("sla_report", "Failed to get commcell name")
        exit(0)

    fp.close()
    res,d1,settings = splunk.Intersplunk.getOrganizedResults()
    session_key = settings['sessionKey']

    SL.make_entry("sla_report","Getting latest SLA")
    username,password,url = helper.get_credentials(commcell_name, session_key)

    auth_code = helper.get_authcode(username, password, url)

    met_sla = helper.get_sla_report(auth_code, url)
    if(met_sla == -1):
        SL.make_entry("sla_report", "Failed to get sla count")
        exit(0)

    missed_sla = 100 - met_sla

    json_list = []

    json_dict = {}
    json_dict["SLA Type"] = "MetSLA"
    json_dict["Count"] = met_sla
    json_list.append(json_dict)

    json_dict = {}
    json_dict["SLA Type"] = "MissedSLA"
    json_dict["Count"] = missed_sla
    json_list.append(json_dict)

    splunk.Intersplunk.outputResults(json_list)

except Exception as excp:
    exc_type, exc_obj, exc_tb = sys.exc_info()
    entry_content = "ERROR " + str(exc_tb.tb_lineno) + ' ' + str(excp)
    SL.make_entry("sla_report", entry_content)
