###############
#
#   Name: ga.py (v1.1)
#   Desc: Takes a single IP address field as input
#         and outputs its corresponding Country, AS Number and Organization
#  Input: ip
# Output: country asn org
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
import csv,sys,os.path,traceback,string,re
import GeoIP

DB_PATH = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'GeoASN','lookups','GeoLiteCity.dat')
ASN_PATH = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'GeoASN','lookups','GeoIPASNum.dat')

gi = GeoIP.open(DB_PATH,GeoIP.GEOIP_MEMORY_CACHE)
ai = GeoIP.open(ASN_PATH,GeoIP.GEOIP_MEMORY_CACHE)

def main():
    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
    header = []
    first = True

    ipi       = -1
    countryi  = -1
    asni      = -1
    orgi      = -1

    # RFC 1918 regex (thanks to Thomas Petersen)
    iprfc = re.compile("(?:10|192\.168|172\.1[6-9]|172\.2\d|172\.3[01])(?:\.\d{1,3}){2,3}")

    for line in r:
        if first:
            header = line

            try:
                ipi = header.index("ip")
            except:
                print "IP field must exist in CSV data"
                sys.exit(0)

            if "country" in header:
                countryi = header.index("country")
            if "asn" in header:
                asni = header.index("asn")
            if "org" in header:
                orgi = header.index("org")

            w.writerow(header)
            first = False
            continue

        try:
            gir = gi.record_by_addr(line[ipi])
        except: continue;
        if gir:
            line[countryi] = unicode(gir['country_name'])
        else:
            # check for RFC 1918 address
            ip = line[ipi]
            if (iprfc.match(ip)):
                line[countryi] = unicode('RFC1918')
            else:
                line[countryi] = unicode('Unknown')

        try:
            air = ai.org_by_addr(line[ipi])
        except: continue;
        if air:
            try: 
		(asn, org) = air.split(' ', 1)
                line[asni] = unicode(asn[2:]) # remove the 'AS' from 'AS1234'
                line[orgi] = unicode(string.replace(org,",",":"))
            except: continue;
        else:
            # check for RFC 1918 address
            ip = line[ipi]
            if (iprfc.match(ip)):
                line[asni]     = "0" # Set AS to 0 for RFC 1918 addresses
                line[orgi]     = unicode('RFC1918')
            else:
                line[asni]     = "0" # Set AS to 0 for unknown addresses
                line[orgi]     = unicode('Unknown')

        w.writerow(line)
    
main()
