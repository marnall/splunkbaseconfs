###############
#
#   Name: geo.py (v1.1)
#   Desc: Takes a single IP address field as input and output its corresponding country, region, city, latitude and longitude
#  Input: clientip
# Output: client_country client_region client_city client_lat client_lon
#
# Based on Will Hayes @ Splunk's MAXMIND Geo Location Lookup Script.
# But rewritten to use the native Maxmind C libraries, for increased 
# speed and functionality.
#
# This requires that you build the Maxmind C SDK and Python SDK, 
# and install the libraries in $SPLUNK_HOME (see README)
# 
# Henrik Strom, Telenor Norway, April 2011
#
###############
import csv,sys,os.path,traceback,re
import GeoIP

DB_PATH = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'GeoASN','lookups','GeoLiteCity.dat')

gi = GeoIP.open(DB_PATH,GeoIP.GEOIP_MEMORY_CACHE)

def do_replacement(gir, line, index, attr):
    if index != -1 and gir.get(attr, None):
        try:
            line[index] = unicode(gir[attr])
        except:
            pass
            
def main():
    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
    header = []
    first = True

    ipi      = -1
    countryi = -1
    regioni  = -1
    cityi    = -1
    lati     = -1
    loni     = -1

    # RFC 1918 regex (thanks to Thomas Petersen)
    iprfc = re.compile("(?:10|192\.168|172\.1[6-9]|172\.2\d|172\.3[01])(?:\.\d{1,3}){2,3}")

    for line in r:
        if first:
            header = line

            try:
                ipi = header.index("clientip")
            except:
                print "IP field must exist in CSV data"
                sys.exit(0)

            if "client_country" in header:
                countryi = header.index("client_country")
            if "client_region" in header:
                regioni = header.index("client_region")
            if "client_city" in header:
                cityi = header.index("client_city")
            if "client_lat" in header:
                lati = header.index("client_lat")
            if "client_lon" in header:
                loni = header.index("client_lon")

            w.writerow(header)
            first = False
            continue

        try:
            gir = gi.record_by_addr(line[ipi])
        except: 
            continue
        if gir:
            do_replacement(gir, line, countryi, 'country_name');
            do_replacement(gir, line, regioni,  'region_name');
            do_replacement(gir, line, cityi,    'city');
            do_replacement(gir, line, lati,     'latitude');
            do_replacement(gir, line, loni,     'longitude');
        else:
            # check for RFC 1918 address
            ip = line[ipi]
            if (iprfc.match(ip)):
                line[countryi]  = unicode('RFC1918')
                line[regioni]   = unicode('RFC1918')
                line[cityi]     = unicode('RFC1918')
            else:
                line[countryi]  = unicode('Unknown')
                line[regioni]   = unicode('Unknown')
                line[cityi]     = unicode('Unknown')

        w.writerow(line)
    
main()
