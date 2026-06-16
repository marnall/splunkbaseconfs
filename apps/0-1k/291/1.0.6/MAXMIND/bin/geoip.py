# An aadapter that takes CSV as input, performs a lookup to some external system, then returns the CSV results
import csv,sys,os.path, traceback
import pygeoip

#DB_PATH = os.path.join(os.environ["SPLUNK_HOME"], 'etc', 'apps', 'MAXMIND','bin','GeoLiteCity.dat')
DB_PATH=('GeoLiteCity.dat')



gi = pygeoip.GeoIP(DB_PATH)

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

        ip = line[ipi]
        try:
            gir = gi.record_by_addr(line[ipi])
        except: continue;
        if gir:
            do_replacement(gir, line, countryi, 'country_name');
            do_replacement(gir, line, regioni,  'region_name');
            do_replacement(gir, line, cityi,    'city');
            do_replacement(gir, line, lati,     'latitude');
            do_replacement(gir, line, loni,     'longitude');

        w.writerow(line)

    
main()
