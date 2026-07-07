import splunk
import json
import hashlib
import uuid
import sys
import requests

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())

        search_array = ["| makeresults | eval id = \"{0}\" | eval owner = \"Unassigned\" | eval status = \"New\" | eval comment = \"no comment\"".format(str(uuid.uuid4()))]
        search_table = []
        for i in payload["result"]:
            value = payload["result"][i]

            if i == "_timediff": 
                continue
            elif i == "_time":
                search_array.append("| eval _time = {0}".format(value))
                search_array.append("| eval edit_time = {0}".format(value))
            elif i in ["Destination", "app", "dest_port"]:
                if type(value) == list:
                    if len(value) > 1:
                        search_array.append("| eval {0} = \"{1}\" | makemv {2}".format(i, " ".join(value), i))
                else:
                    search_array.append("| eval {0} = \"{1}\"".format(i, value))
            else:
                search_array.append("| eval {0} = \"{1}\"".format(i, value))
            search_table.append(i)

        table = "| table {0}, edit_time, id, owner, status, comment".format(", ".join(search_table))

        url = "https://localhost:8089/servicesNS/nobody/search/search/jobs/export?output_mode=json"
        headers = {
        'Authorization': 'Splunk %s' % payload.get('session_key'),
        'Content-Type': 'application/json'}

        data = {
            "search": "{0} {1} | collect index=pvx_alerts".format(" ".join(search_array), table)
        }
        
        r = requests.post(url, data=data, headers=headers, verify=False)
