import splunk.appserver.mrsparkle.lib.util as util
import requests
import os

def validate_input(helper, definition):
    pass

def collect_events(helper, ew):
    url = lambda file : "http://34.72.20.253/{0}".format(file)
    ip_ti = "rf_ip_risklist.csv"
    domain_ti = "rf_domain_risklist.csv"

    write_to_csv(ip_ti, url(ip_ti))
    write_to_csv(domain_ti, url(domain_ti))

def write_to_csv(csv, link):
    lookup = os.path.join(util.get_apps_dir(), 'TA-skylight-for-splunk', 'lookups', csv)

    with open(lookup, "wb") as f:
        response = requests.get(link, stream=True)
        content_length = response.headers.get('content-length')

        if content_length is None:
            f.write(response.content)
        else:
            downloaded_bytes = 0 

            try:
                for data in response.iter_content(chunk_size=4096):
                    downloaded_bytes += len(data)
                    f.write(data)
            except:
                exit()
