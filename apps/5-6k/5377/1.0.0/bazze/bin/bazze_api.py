import argparse
import urllib.parse
import urllib.request
import datetime
import calendar
import json
import time
import sys

x=1000000
sys.setrecursionlimit(x)

from_date = datetime.datetime.now()
from_date = calendar.timegm(from_date.timetuple())
from_date = int(from_date) - 86400
from_date = datetime.datetime.fromtimestamp(from_date).strftime('%Y-%m-%d %H:%M:%S').replace(' ','T').replace(':','%3A')

to_date = datetime.datetime.now()
to_date = calendar.timegm(to_date.timetuple())
to_date = int(to_date) - 84600
to_date = datetime.datetime.fromtimestamp(to_date).strftime('%Y-%m-%d %H:%M:%S').replace(' ','T').replace(':','%3A')

parser = argparse.ArgumentParser()
parser.add_argument('-t', '--token', dest='token',  required=True, help="API token for querying Bazze API.")
parser.add_argument('-l', '--limit', dest='limit',  required=True, help="Number of records pulled limit.")
parser.add_argument('-c', '--country', dest='country',  required=True, help="Country to pull records from. Specify ALL to pull data from all avaialble countries.")
args = parser.parse_args()

url = None

if args.country.lower() != "all":
    url = "https://api.bazze.io/v1/records?wait=false&limit="+args.limit+"&from_date="+from_date+"&to_date="+to_date+"&country="+args.country
else:
    url = "https://api.bazze.io/v1/records?wait=false&limit="+args.limit+"&from_date="+from_date+"&to_date="+to_date

def requestScrollResults(queryData,tries):
    resultsReq = urllib.request.Request("https://api.bazze.io/v1/scrollResults",queryData)
    resultsReq.add_header('x-api-key',args.token)
    resultsReq.add_header('content-type','application/json')
    resultsReq.add_header('accept','application/json')
    response = urllib.request.urlopen(resultsReq)
    results = json.loads(response.read().decode('utf-8'))

    if "Status" in results:
        if tries < 50000:
            time.sleep(5)
            requestScrollResults(queryData,tries+1)

    else:
        records = results['results']

        for r in records:
            record = {
                'advertising_id': r['advertising_id'],
                'bazze_device_id': r['bazze_device_id'],
                'bazze_event_id': r['bazze_event_id'],
                'bazze_geohash': r['bazze_geohash'],
                'bazze_mgrs': r['bazze_mgrs'],
                'country': r['country'],
                'ip_address': r['ip_address'],
                'latitude': r['latitude'],
                'longitude': r['longitude'],
                'timestamp': r['timestamp'],
                'user_agent': r['user_agent'],
                'wifi_ssid': r['wifi_ssid']
            }

            print(json.dumps(record)+'\n')

        if "NextToken" in results:
            queryData = "{\"MaxResults\":1000,\"NextToken\":\""+results['NextToken']+"\",\"QueryExecutionId\":\""+execID+"\"}"  
            queryData = queryData.encode('ascii')
            requestScrollResults(queryData,0)
        else:
            sys.exit()

def scrollResults(execID):
    queryData = "{\"MaxResults\":1000,\"NextToken\":\"\",\"QueryExecutionId\":\""+execID+"\"}"  
    queryData = queryData.encode('ascii')
    scroll = requestScrollResults(queryData,0)

try:
    queryReq = urllib.request.Request(url)
    queryReq.add_header('x-api-key',args.token)
    queryReq.add_header('content-type','application/json')
    queryReq.add_header('accept','application/json')
    response = urllib.request.urlopen(queryReq)

    if response.code == 200:
        execID = json.loads(response.read().decode('utf-8'))['QueryExecutionId']
        results = scrollResults(execID)

except urllib.error.URLError as e:
    print(e.reason)