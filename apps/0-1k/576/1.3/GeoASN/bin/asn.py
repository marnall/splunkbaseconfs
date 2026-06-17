###############
#
#   Name: asn.py (v1.1)
#   Desc: Takes two IP address fields as input and outputs their corresponding AS number information
#  Input: src_ip dest_ip      
# Output: src_asn dest_asn
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
import csv,sys,os.path,re
import GeoIP

DB_PATH = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'GeoASN','lookups','GeoIPASNum.dat')

gi = GeoIP.open(DB_PATH,GeoIP.GEOIP_MEMORY_CACHE)

def main():
    r = csv.reader(sys.stdin)
    w = csv.writer(sys.stdout)
    header = []
    first = True

    src_ipi   = -1
    dest_ipi  = -1
    src_asni  = -1
    dest_asni = -1

    # RFC 1918 regex (thanks to Thomas Petersen)
    iprfc = re.compile("(?:10|192\.168|172\.1[6-9]|172\.2\d|172\.3[01])(?:\.\d{1,3}){2,3}")

    for line in r:
        if first:
            header = line

            try:
                src_ipi  = header.index("src_ip")
            except:
                print "IP field must exist in CSV data"
                sys.exit(0)

            if "dest_ip" in header:
                dest_ipi = header.index("dest_ip")

            if "src_asn" in header:
                src_asni = header.index("src_asn")

            if "dest_asn" in header:
                dest_asni = header.index("dest_asn")

            w.writerow(header)
            first = False
            continue

        try:
            src_asn = gi.org_by_addr(line[src_ipi])
        except: continue
        if src_asn:
	    try:
                line[src_asni] = unicode(src_asn)
	    except: continue
        else:
             # check for RFC 1918 address
             ip = line[src_ipi]
             if (iprfc.match(ip)):
                 line[src_asni] = unicode('RFC1918')
             else:
                 line[src_asni] = unicode('Unknown')

        try:
            dest_asn = gi.org_by_addr(line[dest_ipi])
        except: continue
        if dest_asn:
	    try:
                line[dest_asni] = unicode(dest_asn)
	    except: continue
        else:
             # check for RFC 1918 address
             ip = line[dest_ipi]
             if (iprfc.match(ip)):
                 line[dest_asni] = unicode('RFC1918')
             else:
                 line[dest_asni] = unicode('Unknown')

        w.writerow(line)

main()
