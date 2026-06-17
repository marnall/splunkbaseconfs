###############
#
#   Name: geoasn.py (v1.1)
#   Desc: Takes two IP address fields as input
#         and outputs their corresponding Country, AS number and Org information
#  Input: src_ip dest_ip      
# Output: src_country dest_country src_asn src_as src_org dest_asn dest_as dest_org
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

    src_ipi       = -1
    dest_ipi      = -1
    src_countryi  = -1
    dest_countryi = -1
    src_asni      = -1
    src_asi       = -1
    src_orgi      = -1
    dest_asni     = -1
    dest_asi      = -1
    dest_orgi     = -1

    # RFC 1918 regex (thanks to Thomas Petersen)
    iprfc = re.compile("(?:10|192\.168|172\.1[6-9]|172\.2\d|172\.3[01])(?:\.\d{1,3}){2,3}")

    for line in r:
        if first:
            header = line

            try:
                src_ipi = header.index("src_ip")
            except:
                print "IP field must exist in CSV data"
                sys.exit(0)

            if "dest_ip" in header:
                dest_ipi = header.index("dest_ip")
            if "src_country" in header:
                src_countryi = header.index("src_country")
            if "dest_country" in header:
                dest_countryi = header.index("dest_country")
            if "src_asn" in header:
                src_asni = header.index("src_asn")
            if "src_as" in header:
                src_asi = header.index("src_as")
            if "src_org" in header:
                src_orgi = header.index("src_org")
            if "dest_asn" in header:
                dest_asni = header.index("dest_asn")
            if "dest_as" in header:
                dest_asi = header.index("dest_as")
            if "dest_org" in header:
                dest_orgi = header.index("dest_org")

            w.writerow(header)
            first = False
            continue

        try:
            src_gir = gi.record_by_addr(line[src_ipi])
        except: continue;
        if src_gir:
            line[src_countryi] = unicode(src_gir['country_name'])
        else:
            # check for RFC 1918 address
            ip = line[src_ipi]
            if (iprfc.match(ip)): 
                line[src_countryi] = unicode('RFC1918')
            else:
                line[src_countryi] = unicode('Unknown')

        try:
            dest_gir = gi.record_by_addr(line[dest_ipi])
        except: continue;
        if dest_gir:
            line[dest_countryi] = unicode(dest_gir['country_name'])
        else:
            # check for RFC 1918 address
            ip = line[dest_ipi]
            if (iprfc.match(ip)):
                line[dest_countryi] = unicode('RFC1918')
            else:
                line[dest_countryi] = unicode('Unknown')

        try:
            src_asn = ai.org_by_addr(line[src_ipi])
        except: continue;
        if src_asn:
            try: 
		(src_as, src_org) = src_asn.split(' ', 1)
                line[src_asi] = unicode(src_as[2:]) # remove the 'AS' from 'AS1234'
                line[src_asni] = unicode(src_asn)
                line[src_orgi] = unicode(src_org)
                if len(src_org) > 45: # truncate Orgnames longer than 45 chars
                    line[src_orgi] = unicode(string.replace(src_org[:45],",",":"))
                else:
                    line[src_orgi] = unicode(string.replace(src_org,",",":"))
            except: continue;
        else:
            # check for RFC 1918 address
            ip = line[src_ipi]
            if (iprfc.match(ip)):
                line[src_asi]      = "0" # Set AS to 0 for RFC 1918 addresses
                line[src_asni]     = unicode('RFC1918')
                line[src_orgi]     = unicode('RFC1918')
                line[src_countryi] = unicode('RFC1918')
            else:
                line[src_asi]      = "0" # Set AS to 0 for unknown addresses
                line[src_asni]     = unicode('Unknown')
                line[src_orgi]     = unicode('Unknown')

        try:
            dest_asn = ai.org_by_addr(line[dest_ipi])
        except: continue;
        if dest_asn:
            try: 
		(dest_as, dest_org) = dest_asn.split(' ', 1)
                line[dest_asi] = unicode(dest_as[2:]) # remove the 'AS' from 'AS1234'
                line[dest_asni] = unicode(dest_asn)
                line[dest_orgi] = unicode(dest_org)
                if len(dest_org) > 45: # truncate Orgnames longer than 45 chars
                    line[dest_orgi] = unicode(string.replace(dest_org[:45],",",":"))
                else:
                    line[dest_orgi] = unicode(string.replace(dest_org,",",":"))
            except: continue;
        else:
            # check for RFC 1918 address
            ip = line[dest_ipi]
            if (iprfc.match(ip)):
                line[dest_asi]      = "0" # Set AS to 0 for RFC 1918 addresses
                line[dest_asni]     = unicode('RFC1918')
                line[dest_orgi]     = unicode('RFC1918')
                line[dest_countryi] = unicode('RFC1918')
            else:
                line[dest_asi]      = "0" # Set AS to 0 for unknown addresses
                line[dest_asni]     = unicode('Unknown')
                line[dest_orgi]     = unicode('Unknown')

        w.writerow(line)
    
main()
