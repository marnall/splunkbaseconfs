#Send API, LAT, LON
from WunderClass import *

import sys, os, platform, re
import xml.dom.minidom, xml.sax.saxutils
import logging
import urllib2
import json
import sched, time

logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)

(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)

if len(sys.argv) < 1:
    splunk.Intersplunk.parseError("No arguments provided")
    
    
if isgetinfo:
    splunk.Intersplunk.outputInfo(False, False, True, False, None, True)
    # outputInfo automatically calls sys.exit()    
    
def getParameters():
    argcount = len(sys.argv)
    field="_raw"
    apikey = None
    params = re.findall('(\\w+)\s*=\s*"?(\\w+)', " ".join(sys.argv))
    for k,v in params:
        v = v.lower()
        if k=="apikey": field=v
        else:   usage()       
    return field, apikey

if __name__ == '__main__':
    try:
        field, apikey = getParameters()
        srcfield = "_raw"
        wunderBread = WunderAPI(apikey)
        csv.field_size_limit(sys.maxint)
        rows = [r for r in unicode_csv_reader(sys.stdin)]
        outrows = []
        fieldpos = lonpos = latpos = None
        # for each row
        for row in rows:
            if fieldpos == None:
                 fieldpos = row.index(srcfield) if srcfield in row else -1
                 latpos = row.index("lat")
                 lonpos = row.index("lon")
                 if fieldpos < 0:
                     raise Exception('Search results do not have the specified text field: "%s"' % srcfield)
                 row.append('temp_f')
                 row.append('temp_c')
                 row.append('wind_dir')
                 row.append('wind_degrees')
                 row.append('wind_mph')
                 row.append('wind_gust_mph')
                 row.append('wind_kph')
                 row.append('wind_gust_kph')
                 row.append('pressure_in')
                 row.append('pressure_mb')
                 row.append('dewpoint_f')
                 row.append('dewpoint_c')
                 row.append('heat_index_f')
                 row.append('heat_index_c')
                 row.append('windchill_f')
                 row.append('windchill_c')
                 row.append('feelslike_f')
                 row.append('feelslike_c')
                 row.append('visibility_mi')
                 row.append('visibility_km')
                 row.append('uv')
                 row.append('precip_1hr_in')
                 row.append('precip_1hr_metric')
                 row.append('precip_today_in')
                 row.append('precip_today_metric')
                 row.append('solarradiation')
            else:
                 lat = row[latpos]      
                 lon = row[lonpos]
                 jCO = json.loads("{\"lat\":\"%s\",\"lng\":\"%s\",\"feature\":\"%s\""%(lat,lon,"geolookup"))
                 jS = json.loads(wunderBread.RunAPI(jCO))
                 city = state = None
                 city = jS["location"]["city"]
                 state = jS["location"]["state"]
                 if len(state) < 1:
                     state = jS["location"]["country_name"]
                 jCO = json.loads("{\"country\":\"%s\",\"city\":\"%s\",\"feature\":\"%s\""%(state,city,"conditions"))
                 jR = json.loads(wunderBread.RunAPI(jCO))
                 c = jR["current_observation"]
                 row.append(c['temp_f'])
                 row.append(c['temp_c'])
                 row.append(c['wind_dir'])
                 row.append(c['wind_degrees'])
                 row.append(c['wind_mph'])
                 row.append(c['wind_gust_mph'])
                 row.append(c['wind_kph'])
                 row.append(c['wind_gust_kph'])
                 row.append(c['pressure_in'])
                 row.append(c['pressure_mb'])
                 row.append(c['dewpoint_f'])
                 row.append(c['dewpoint_c'])
                 row.append(c['heat_index_f'])
                 row.append(c['heat_index_c'])
                 row.append(c['windchill_f'])
                 row.append(c['windchill_c'])
                 row.append(c['feelslike_f'])
                 row.append(c['feelslike_c'])
                 row.append(c['visibility_mi'])
                 row.append(c['visibility_km'])
                 row.append(c['uv'])
                 row.append(c['precip_1hr_in'])
                 row.append(c['precip_1hr_metric'])
                 row.append(c['precip_today_in'])
                 row.append(c['precip_today_metric'])
                 row.append(c['solarradiation'])
        # output rows
        csv.writer(sys.stdout).writerows(rows)
        exit(0)
    except Exception, e:
        h = ["ERROR"]
        results = [ {"ERROR": e} ]
        dw = csv.DictWriter(sys.stdout, h)
        dw.writerow(dict(zip(h, h)))
        dw.writerows(results)
        exit(-1)