import zipfile
from urllib2 import urlopen
import os
import json

url = 'https://nvd.nist.gov/feeds/json/cve/1.0/nvdcve-1.0-recent.json.zip'
zip_file = os.path.basename(url)

def make_path(url, target_path, zip_file):
    app_root = os.path.dirname(os.path.dirname(os.path.join(os.getcwd(), __file__))) 
    base_url = os.path.join(app_root, target_path)
    file_name = os.path.join(base_url, zip_file)
    return (base_url, zip_file) 

if os.name == 'nt':
    base_url, file_name = make_path(url, "nvd", zip_file)
    output_file = os.path.join(base_url, file_name)
    print("base_url = " + base_url)
    print("file_name = " + file_name)

else:
    base_url, file_name = make_path(url, "nvd", zip_file)
    output_file = os.path.join(base_url, file_name)


f = urlopen(url)

with open(output_file, "wb") as local_file:
    local_file.write(f.read())


print("Unzipping file.")
with zipfile.ZipFile(output_file) as zf:
    zf.extractall(base_url)


print("Load the JSON file into Python.")
with open(output_file[:-4], "r") as read_file:
    data = json.load(read_file)


print("Output the JSON file into a new file.")
outpath = os.path.join(base_url, "nvdcve-1.0-recent" + data["CVE_data_timestamp"].replace(":","_") + ".json")
with open(outpath, "w") as write_file:
    json.dump(data["CVE_Items"], write_file)

print("Remove uncompressed file")
os.remove(output_file[:-4])
