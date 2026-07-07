from __future__ import print_function
from io import BytesIO
from zipfile import ZipFile
import requests
import json

years = [
    "2020",
    "2019",
    "2018"
]

for year in years:
    url = 'https://nvd.nist.gov/feeds/json/cve/1.1/nvdcve-1.1-%s.json.zip' % year
    response = requests.get(url)
    data = {}
    zipfile = ZipFile(BytesIO(response.content)) 

    for i in zipfile.namelist():
        if i == "nvdcve-1.1-%s.json" % year:
            data = json.loads(zipfile.read(i))
            break

    for d in data["CVE_Items"]:
        if "configurations" in list(d.keys()):
            del d["configurations"]
        print(json.dumps(d))
