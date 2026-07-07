import splunklib.client as client
import splunklib.results as results
import splunk.Intersplunk
import splunklogger as SL
import csv
import sys
import pickle

def get_association(head,query_string):
    for i in head:
        if(len(i) != 0):
            if query_string in i[0].lower():
                return i[1].strip()
    return ""

def get_credentials():
        fp = open("../local/splunkdetails.conf","r")
        contents = fp.read()
        contents_list = contents.split("\n")
        auth_token = contents_list[0]
        return auth_token

def get_key(file_name, host_name, index_name):

    #token = get_credentials()
    HOST = "127.0.0.1"
    PORT = "8089"
    USERNAME = "splunkcv"
    PASSWORD = "splunkcv@123"
    service = client.connect(host=HOST,port=PORT,username=USERNAME,password=PASSWORD)
    #service = client.connect(token=self._metadata.searchinfo.session_key)

    searchquery_oneshot = "search index=" + index_name + " host=" + host_name + " module" + " version"
    oneshotsearch_results = service.jobs.oneshot(searchquery_oneshot,count=0)
    # Get the results and display them using the ResultsReader
    reader = results.ResultsReader(oneshotsearch_results)
    head = []
    count = 0
    for item in reader:
        if(item['source'] == file_name):
            count += 1
            head_str = item['_raw']
            head = head + head_str.split('\n')
            break

    searchquery_oneshot = "search index=" + index_name + " host=" + host_name + " os type"

    oneshotsearch_results = service.jobs.oneshot(searchquery_oneshot,count=0)
    # Get the results and display them using the ResultsReader
    reader = results.ResultsReader(oneshotsearch_results)

    for item in reader:
        if(item['source'] == file_name):
            head_str = item['_raw']
            head = head + head_str.split('\n')
            break

    for i in range(len(head)):
        head[i] = head[i].strip()
        head[i] = head[i].strip("*")
        head[i] = head[i].strip()

    for i in range(len(head)):
        if ":" in head[i]:
            head[i] = head[i].split(":",1)
    d = {}

    machine = get_association(head,"machine")
    if(machine != ""):
        d["machine"] = machine

    commserver = get_association(head,"commserver")
    if(commserver != ""):
        d["commserver"] = commserver

    version = get_association(head,"version")
    if(version != ""):
        d["version"] = version

    ostype = get_association(head,"os type")
    if(ostype != ""):
        d["ostype"] = ostype

    module = get_association(head,"module")
    if(module != ""):
        d["module"] = module

    return d

def load_source_dict():
    try:
        fp = open('header_info.p', 'rb')
        req_ds = pickle.load(fp)
        return req_ds
    except Exception as excp:
        return {}

def pickle_write(source):
    fp = open('header_info.p', 'wb')
    pickle.dump(source, fp)

def main():
    source = sys.argv[1]
    machine = sys.argv[2]
    commserver = sys.argv[3]
    version = sys.argv[4]
    ostype = sys.argv[5]
    module = sys.argv[6]
    index = sys.argv[7]
    host = sys.argv[8]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    source_dict = {}

    source_dict = load_source_dict()

    for result in r:
        file_name = result[source]
        host_name = result[host]
        index_name = result[index]
        file_and_host_name  = host_name + "&+&" + file_name

        if file_and_host_name not in  source_dict.keys():
            continue
            SL.make_entry("splunk_external","Getting New " + file_and_host_name)
            try:
                returned_dict = get_key(file_name, host_name, index_name)
            except Exception as excp:
                SL.make_entry("splunk_external","ERROR in splunk external lookup " + str(excp))
                continue
            source_dict[file_and_host_name] = {}
            if("commserver" in returned_dict.keys()):
                result[commserver] = returned_dict["commserver"]
                source_dict[file_and_host_name]["commserver"] = returned_dict["commserver"]
            if("machine" in returned_dict.keys()):
                result[machine] = returned_dict["machine"]
                source_dict[file_and_host_name]["machine"] = returned_dict["machine"]
            if("version" in returned_dict.keys()):
                result[version] = returned_dict["version"]
                source_dict[file_and_host_name]["version"] = returned_dict["version"]
            if("ostype" in returned_dict.keys()):
                result[ostype] = returned_dict["ostype"]
                source_dict[file_and_host_name]["ostype"] = returned_dict["ostype"]
            if("module" in returned_dict.keys()):
                result[module] = returned_dict["module"]
                source_dict[file_and_host_name]["module"] = returned_dict["module"]


        else:
            continue
            SL.make_entry("splunk_external","Already Exists")
            if("commserver" in source_dict[file_and_host_name].keys()):
                result[commserver] = source_dict[file_and_host_name]["commserver"]
            if("machine" in source_dict[file_and_host_name].keys()):
                result[machine] = source_dict[file_and_host_name]["machine"]
            if("version" in source_dict[file_and_host_name].keys()):
                result[version] = source_dict[file_and_host_name]["version"]
            if("ostype" in source_dict[file_and_host_name].keys()):
                result[ostype] = source_dict[file_and_host_name]["ostype"]
            if("module" in source_dict[file_and_host_name].keys()):
                result[module] = source_dict[file_and_host_name]["module"]

        w.writerow(result)

    pickle_write(source_dict)

main()
