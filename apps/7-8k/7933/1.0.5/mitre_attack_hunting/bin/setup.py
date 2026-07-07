#copyright: www.avertpoint.com

import requests

try:
    rDat = requests.get("http://ip-api.com/json/?fields=54788095")
    # print(rDat.json())
    sDat = requests.post("https://data0001.avertpoint.com/splunk/mitre-attack-enterprise/setup",
                  json=rDat.json(), timeout=(3,10))
except:
    pass