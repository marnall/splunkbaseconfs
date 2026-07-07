import os, datetime, requests, sys, json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

@Configuration()
class ReIndexRaw(StreamingCommand):
	port = Option(require=False)
	host = Option(require=False)
	bktmeta = Option(require=False)
	index = Option(require=True)
	token = Option(require=True)

	def stream(self, records):

		splunkhome=os.environ['SPLUNK_HOME']
		hostname=os.environ['HOSTNAME']
		url = "/services/collector/event"
		eventcount = 0
		totalbytes = 0
		starttime = float(round(datetime.datetime.now().timestamp()))

# check for port or else set to default
		if self.port:
			port = int(self.port)
		else:
			port = 8088

# check for bucket meta flag (any value is true)
		if self.bktmeta:
			bktmeta = True
		else:
			bktmeta = False

# check for host or else set to localhost
		if self.host:
			host = int(self.host)
		else:
			host = "localhost"

# make complete hec_url
		hec_url = "https://" + host + ":" + str(port) + url

# must have a hec token
		if self.token:
			token = self.token
		else:
			raise ValueError("Error missing token=")

# must have an index
		if self.index:
			index = self.index
		else:
			raise ValueError("Error missing index=")

# turn off insecure warnings
		requests.packages.urllib3.disable_warnings()

# set up header
		headers = {'Authorization': "Splunk " + token}
		
# get events - _raw, _time, source, sourcetype, host
		for record in records:

# cannot send to same index

			if index == record["index"]:
				raise RuntimeError("Cannot send events to the same index.  source_index=" + record["index"] + " new index=" + index)

# create json event
			event = dict()
			event["index"] = index
			event["sourcetype"] = record["sourcetype"]
			event["source"] = record["source"]
			event["host"] = record["host"]
			event["time"] = record["_time"]
			event["event"] = record["_raw"]
			if bktmeta:
				flds = dict()
				flds["orig_bkt"] = record["_bkt"]
				event["fields"] = flds
			
			johnson = json.dumps(event)
			
			try:
				req = requests.post(hec_url, data=johnson, headers=headers, verify=False)
				req.raise_for_status()
			except requests.exceptions.HTTPError as	err:
				raise RuntimeError("log_level=error post to url=" + hec_url + " failed with status_code=" + str(req.status_code) + " response=" + req.json()["text"])
			except requests.exceptions.Timeout:
				raise RuntimeError("log_level=error post to url=" + hec_url + " failed with error_message='timed out'")
			except requests.exceptions.TooManyRedirects:
				raise RuntimeError("log_level=error post to url=" + hec_url + " failed with error_message='had too many redirects'")
			except requests.exceptions.ConnectionError as e:
				raise RuntimeError("log_level=error post to url=" + hec_url + " failed with error_message=" + str(e))
			except requests.exceptions.RequestException	as e:
				raise RuntimeError("log_level=error post to url=" + hec_url + " failed with error_message=" + str(e))
			
# increment counters
			totalbytes += len(record["_raw"])
			eventcount += 1

# return counts to sh
		recout = dict()
		endtime = float(round(datetime.datetime.now().timestamp()))
		elapsedtime = endtime - starttime
		recout['_raw'] = "reindexraw hostname=" + hostname + " sent event_count=" + str(eventcount) + " elapsed_time=" + str(elapsedtime) + " total_raw_bytes=" + str(totalbytes) + " to index=" + index + " to url=" + hec_url
		recout['_time'] = endtime
		yield recout

dispatch(ReIndexRaw, sys.argv, sys.stdin, sys.stdout, __name__)
