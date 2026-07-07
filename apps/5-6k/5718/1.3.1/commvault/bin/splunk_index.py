import splunk.Intersplunk
import splunklib.client as splunk_client

try:
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    auth_string = settings["authString"]
    first_split = auth_string.split("<authToken>")
    auth_token = first_split[1].split("</authToken>")[0]
    service = splunk_client.connect(token=auth_token)
    indexes = service.indexes
    fp = open("../local/splunkindex.conf","w")
    wc = ""
    for index in indexes:
        wc = wc + index.name + "\n"
    fp.write(wc)
    fp.close()

except Exception as excp:
    fp = open("internal_log.txt","a")
    fp.write(str(excp) + '\n')
    fp.close()
