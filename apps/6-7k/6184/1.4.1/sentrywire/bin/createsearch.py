#!/usr/bin/env python

import sys
import os
import time
import configparser
from swlogin import getcreds
from datetime import datetime

if os.getenv("DEBUG"):
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
except ImportError as e:
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".", "lib"))
    from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

from sentrywire.client import Sentrywire
from sentrywire.exceptions import InvalidAuthentication

WAIT_FOR_SEARCH_TIME = 500
PCAPDIRECTORY = os.getenv("SPLUNK_HOME") + "/etc/apps/sentrywire/appserver/static/pcaps/"
os.makedirs(PCAPDIRECTORY, exist_ok=True)
AUTHFILE = os.getenv("SPLUNK_HOME") + "/etc/apps/sentrywire/auth/authenticated.csv"

try:
    config = configparser.ConfigParser()
    config.read(os.getenv("SPLUNK_HOME") + "/etc/apps/sentrywire/local/app.conf")
    FRONTEND = config["install"]["frontend"]
    DOWNLOAD = config["install"]["return_pcaps"]
    if DOWNLOAD == 'on':
        DOWNLOAD = 1
    elif DOWNLOAD == 'off':
        DOWNLOAD = 0
    else:
        raise ValueError("Invalid DOWNLOAD value")
except Exception as e:
    sys.stderr.write("Sentrywire app is not configured correctly: " + str(e))
    exit(1)


@Configuration()
class SentrywireCommand(StreamingCommand):
    ip = Option(require=True, validate=validators.Match("ip", ".*"))
    rest_token = Option(require=False, validate=validators.Match("rest_token", ".*"))
    start_time = Option(require=False, validate=validators.Match("start_time", ".*"))
    end_time = Option(require=False, validate=validators.Match("end_time", ".*"))
    search_name = Option(require=True, validate=validators.Match("search_name", ".*"))
    bpf_filter = Option(require=True, validate=validators.Match("bpf_filter", ".*"))
    node_name = Option(require=True, validate=validators.Match("node_name", ".*"))
    max_packets = Option(require=False, default=10000, validate=validators.Integer())

    def stream(self, events):
        startTime = time.time()

        # If user defines time span, use that, otherwise use native splunk time span.
        search_results = self.search_results_info
        try:
            if not self.start_time:
                self.start_time = datetime.fromtimestamp(search_results.search_et).strftime("%Y-%m-%d %H:%M:%S")
            if not self.end_time:
                self.end_time = datetime.fromtimestamp(search_results.search_lt).strftime("%Y-%m-%d %H:%M:%S")
        except:
            # Firefox does not require time in a datetime input, the issue parses the search values as such
            if self.start_time == "end_time=":
                sys.stderr.write("You must input a time in addition to a date")
                exit(1)
            sys.stderr.write("Date format could not be parsed. Please use %Y-%m-%dT%H:%M:%S")
            sys.stderr.write("\nStart time: " + str(self.start_time) + 
                             "\nEnd time: " + str(self.end_time) +
                             "\nSearch name: " + str(self.search_name) +
                             "\nBpf filter: " + str(self.bpf_filter) +
                             "\nMax packets: " + str(self.max_packets))
            exit(1)
            

        # If user defines credentials use those, otherwise lookup stored creds for the current user.
        if not self.rest_token:
            rest_token = getcreds(self._metadata.searchinfo.username, self.ip)
        else:
            rest_token = self.rest_token
        if not rest_token:
            sys.stderr.write("No rest token found, please use authentication page.")
            exit(1)
            return

        output = CreateSentrywireSearch(self.ip, rest_token, self.node_name, self.start_time,
                                        self.end_time, self.search_name, self.bpf_filter, self.max_packets).execute()
        if not output:
            yield {"Error": "No output?"}
        else:
            for x in output:
                yield x
        yield {'_time': time.time(), 'event_no': 2,
               '_raw': 'Time elapsed: ' + str(round(time.time() - startTime, 2)) + ' seconds'}


class CreateSentrywireSearch:
    def __init__(self, ip, rest_token, node_name, start_time, end_time, search_name, bpf_filter, max_packets):
        self.max_packets = max_packets
        self.node_name = node_name
        if bpf_filter[0] == '"':
            bpf_filter = bpf_filter[1:]
        if bpf_filter[-1] == '"':
            bpf_filter = bpf_filter[:-1] 
        self.bpf_filter = bpf_filter
        self.search_name = search_name
        self.end_time = end_time
        self.start_time = start_time
        self.rest_token = rest_token
        self.ip = ip

    def execute(self):
        try:
            # Create instance of a handler for our server
            # Add verify=False when testing against self signed certs
            if os.getenv("DEBUG"):
                sw = Sentrywire(self.ip, rest_token=self.rest_token, ssl_verify=False)
            else:
                sw = Sentrywire(self.ip, rest_token=self.rest_token)
            # Check that token is valid and that server version matches API wrapper version
            sw.server.status()
        except Exception as e:
            return [{'_time': time.time(), 'event_no': 1, '_raw': "Error: " + str(e)}]
            


        start = None
        end = datetime.now()
        try:
            start = datetime.strptime(self.start_time,"%Y-%m-%dT%H:%M:%S")
            end = datetime.strptime(self.end_time,"%Y-%m-%dT%H:%M:%S")
        except:
            pass
        
        if not start and end:
            try:
                start = datetime.strptime(self.start_time,"%Y-%m-%dT%H:%M")
                end = datetime.strptime(self.end_time,"%Y-%m-%dT%H:%M")
            except:
                pass
        
        if not start and end:
            try:
                start = datetime.strptime(self.start_time,"%Y-%m-%d %H:%M")
                end = datetime.strptime(self.end_time,"%Y-%m-%d %H:%M")
            except:
                pass
        
        if not start and end:
            try:
                start = datetime.strptime(self.start_time,"%Y-%m-%d %H:%M:%S")
                end = datetime.strptime(self.end_time,"%Y-%m-%d %H:%M:%S")
            except:
                pass
        
        if not start and end:
            sys.stderr.write("Date format could not be parsed. Please use %Y-%m-%dT%H:%M:%S")
            sys.stderr.write("Start time: " + str(self.start_time) + 
                             "\nEnd time: " + str(self.end_time) +
                             "\nSearch name: " + str(self.search_name) +
                             "\nBpf filter: " + str(self.bpf_filter) +
                             "\nMax packets: " + str(self.max_packets))
            exit(1)

        # Create search with parameters
        response = sw.searches.create(self.search_name,
                                      start,
                                      end,
                                      search_filter=self.bpf_filter,
                                      max_packets=self.max_packets)
        search_token = response["searchname"]

        if not DOWNLOAD:
            return [{'_time': time.time(), 'event_no': 1,
                    '_raw': 'Sentrywire search created with identifier: ' + search_token}]
        else:
            program_timeout = time.time() + WAIT_FOR_SEARCH_TIME

            while True:
                time.sleep(5)
                response = sw.searches.status(self.node_name, search_token)
                if time.time() > program_timeout:
                    sys.stderr.write("Timed out waiting for search to complete")
                    exit(1)
                if "SearchStatus" in response:
                    continue
                elif "SearchResult" in response:
                    time.sleep(5)
                    break
                else:
                    raise Exception("Unexpected search state")

            # Pull PCAP of search results
            zip_file = PCAPDIRECTORY + search_token + ".zip"

            sw.searches.pcaps.get(self.node_name, search_token, 1, zip_file)

            #sw.authentication.logout()

            bytes_size = os.path.getsize(zip_file)

            def sizeof_fmt(num, suffix="B"):
                for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
                    if abs(num) < 1024.0:
                        return f"{num:3.1f} {unit}{suffix}"
                    num /= 1024.0
                return f"{num:.1f}Yi{suffix}"

            file_size = sizeof_fmt(bytes_size)

            return [
                    {'_time': time.time(), 'event_no': 1,
                    '_raw': 'Sentrywire PCAP location: ' + FRONTEND + '/static/app/sentrywire/pcaps/' + search_token + '.zip'},
                    {'_time': time.time(), 'event_no': 2,
                     '_raw': 'PCAP size: ' + file_size}
                    ]


try:
    dispatch(SentrywireCommand, sys.argv, sys.stdin, sys.stdout, __name__)
except Exception as e:
    print(str(e))
