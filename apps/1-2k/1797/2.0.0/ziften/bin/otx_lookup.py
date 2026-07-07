import csv
import sys
import urllib
import urllib2
import os

baseurl = "https://reputation.alienvault.com"

def lookup_revision():
    try:
        response = urllib2.urlopen("%s/%s" % (baseurl, "reputation.rev"))
        lines = response.read().split("\n")[0]
    except:
        lines = '0'
    return lines

def lookup_reputation():
    try:
        response = urllib2.urlopen("%s/%s" % (baseurl, "reputation.data"))
        lines = response.read()
    except:
        lines = ''
    return lines

def revision_already_processed(revision):
    result=False
    
    ziften_splunk_bin_dir = os.path.realpath(__file__)
    ziften_splunk_bin_dir = os.path.dirname(ziften_splunk_bin_dir)
    ziften_splunk_base_dir = os.path.dirname(ziften_splunk_bin_dir) 
    ziften_splunk_local_dir = os.path.join(ziften_splunk_base_dir, 'local') 
    if not os.path.exists(ziften_splunk_local_dir):
        ziften_splunk_local_dir = ziften_splunk_bin_dir

    lock_file = os.path.join(ziften_splunk_local_dir ,"revision.lock")
    if os.path.exists(lock_file):
        f = open(lock_file, 'r')
        last_revision = f.read()
        f.close()
        if last_revision == revision:
            result=True
    f = open(lock_file, 'w')
    f.write(revision)
    f.close()
    return result

def main():
    if len(sys.argv) != 11:
        print len(sys.argv)
        print "python otx_lookup.py ipaddress reliability risk classification countrycode city lat lon revision unknown"
        sys.exit(1)

    ipaddress_field = sys.argv[1]
    reliability_field = sys.argv[2]
    risk_field = sys.argv[3]
    classification_field = sys.argv[4]
    countrycode_field = sys.argv[5]
    city_field = sys.argv[6]
    lat_field = sys.argv[7]
    lon_field = sys.argv[8]
    revision_field = sys.argv[9]
    unknown_field = sys.argv[10]

    first = True
    revision = lookup_revision()
    
    current_script_dir = os.path.dirname(os.path.realpath(__file__))
    current_app_dir = os.path.dirname(current_script_dir)
    otx_lookup_file = os.path.join(current_app_dir, "lookups", "otx_lookup.csv")
    otx_lookup_file_exists = os.path.exists(otx_lookup_file)
    
    #OTX data is a dict keyed by ipaddresses.
    otx_data = {}

    if not revision_already_processed(revision) or not otx_lookup_file_exists:
        otx_lookup_file_handle = open(otx_lookup_file, 'w')
        reputation_data = lookup_reputation()
        headers = ["ipaddress","reliability","risk","classification",
                "countrycode","city","lat","lon","revision","unknown"]


        for line in reputation_data.split("\n"):
            row = {
                "ipaddress":"", 
                "reliability":"",
                "risk":"", #risk
                "classification":"", #activity
                "countrycode":"",
                "city":"",
                "lat":"",
                "lon":"",
                "revision":"",
                "unknown":""}
            if first:
                w = csv.DictWriter(otx_lookup_file_handle, headers)
                w.writeheader()
                first = False
            try: 
                line_data = line.split("#")
                row["ipaddress"] = line_data[0]
                row["reliability"] = line_data[1]
                row["risk"] = line_data[2]
                row["classification"] = line_data[3]
                row["countrycode"] = line_data[4]
                row["city"] = line_data[5]
                lat_lon = line_data[6].split(",")
                row["lat"] = lat_lon[0]
                row["lon"] = lat_lon[1]
                row["revision"] = revision
                row["unknown"] = line_data[7]
                classifications = row["classification"].split(';')
                otx_data[row["ipaddress"]] = row
                for classification in classifications:
                    row["classification"] = classification
                    w.writerow(row)
            except:
                pass
        otx_lookup_file_handle.close()
    else:
        otx_lookup_file_handle = open(otx_lookup_file, 'r')
        r = csv.DictReader(otx_lookup_file_handle)
        for row in r:
            #TODO: combine classifications for duplicate hits
            otx_data[row["ipaddress"]] = row
        #read the file and fill otx_data
        otx_lookup_file_handle.close()

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for line in r:
        result = otx_data.get(line[ipaddress_field], None)
        if result:
            line[reliability_field] = result.get("reliability", None)
            line[risk_field] = result.get("risk", None)
            line[classification_field] = result.get("classification", None)
            line[countrycode_field] = result.get("countrycode", None)
            line[city_field] = result.get("city", None)
            line[lat_field] = result.get("lat", None)
            line[lon_field] = result.get("lon", None)
            line[revision_field] = result.get("revision", None)
            line[unknown_field] = result.get("unknown", None)
            w.writerow(line)

main()
