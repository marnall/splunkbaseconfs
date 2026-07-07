from builtins import str
import json
import sys
import requests
import datetime

if __name__ == "__main__":
  if len(sys.argv) > 1 and sys.argv[1] == "--execute":
     data = json.loads(sys.stdin.read())

     if data["result"]["source"] == "/var/log/messages":
         logfile = "messagesReport.log"
         ip = data["configuration"]["ip"]
     elif data["result"]["source"] == "/var/log/secure":
         logfile = "secureReport.log"
         ip = data["result"]["ip"]
     url = data["configuration"]["base_url"]
     categories = data["configuration"]["categories"]
     comment = data["configuration"]["comment"] +":\n" + data["result"]["_raw"]
     headers = {
          "Accept":"application/json",
          "Key":data["configuration"]["key"]
     }

     querystring = {
            "ip":ip,
            "categories":categories,
            "comment":comment
     }


     if ip != "YOUR_IP_HERE" and ip != "YOUR_IP_HERE":
         f = open(logfile, "a")
         response = requests.request(method='POST', url=url, headers=headers, params=querystring)
         decodedResponse = json.loads(response.text)
         f.write("\n**********************************************\n")
         f.write(str(datetime.datetime.now()) + "Report to AbuseIPDB Response:")
         f.write("\n**********************************************\n")

     if response.status_code == 200:
         f.write(json.dumps(decodedResponse, sort_keys=True, indent=4))
     elif response.status_code == 429:
         f.write(json.dumps(decodedResponse, sort_keys=True, indent=4))
     elif response.status_code == 422:
         f.write(json.dumps(decodedResponse, sort_keys=True, indent=4))
     elif response.status_code == 302:
         f.write("Unsecure protocol requested. Redirected to HTTPS.")
     elif response.status_code == 401:
         f.write(json.dumps(decodedResponse, sort_keys=True, indent=4))
     else:
         f.write("Unexpected server response. Status Code: " + response.status_code)
     f.close()
