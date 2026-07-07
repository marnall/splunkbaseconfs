from __future__ import absolute_import, division, print_function, unicode_literals
import os,sys,ssl,json,csv
bin_path = os.path.abspath(os.path.join(os.path.dirname(__file__)))
if bin_path not in sys.path:
    sys.path.insert(0, bin_path)

from io import StringIO, BytesIO
from urllib import error as urllib_error
from urllib import request as urllib_request
from urllib import parse as urllib_parse


sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, GeneratingCommand, Configuration #, Option, validators
import configparser
path = os.path.join(os.path.dirname(__file__), "..", "local/containers.conf")
config = configparser.ConfigParser()
config.read(path)

@Configuration(local=True)
class ComputeCommand(StreamingCommand):
    def stream(self, records):
        # prepare configs and meta data
        url = config.get('__dev__', 'api_url')
        url = f"{url}/compute"
        data_object = {"meta":{}, "data":[]}

        raw_options = self.metadata.searchinfo.args
        list_args = [item for item in raw_options if ':' in item]
        list_keys = [item for item in raw_options if ':' not in item]

        list_args = {item.split(':')[0]: item.split(':')[1] for item in list_args}
        data_object['meta']['params'] = list_args


        data_object['meta']['algo'] = list_args['algo']

        #data_object['meta']['algorithm'] = self.algorithm
        data_object['meta']['fieldnames'] = list_keys
        data_object['meta']['configuration'] = str(self._configuration)
        #data_object['meta']['configuration.streaming_preop'] = str(self.configuration.streaming_preop)
        data_object['meta']['splunk_sid'] = str(self.search_results_info.sid)
        data_object['meta']['metadata.action'] = str(self.metadata.action)
        data_object['meta']['metadata.preview'] = str(self.metadata.preview)
        data_object['meta']['metadata.searchinfo.args'] = str(self.metadata.searchinfo.args)

        # filter and prepare dataset
        # list_keys = self.fieldnames
        data_records = list(records)
        data_records_filtered = [{key:val for key, val in ele.items() if key in list_keys} for ele in data_records]
        data_object['data'] = data_records_filtered

        # data_object['meta']['raw_data'] = data_records_filtered

        # prepare payload
        payload = json.dumps(data_object)
        content_type='application/json'
        if payload:                
            #data_encoded = str.encode(data)
            payload_encoded = BytesIO(str.encode(payload))
            request = urllib_request.Request(url, payload_encoded, {'Content-Type': content_type})
        else:
            request = urllib_request.Request(url)

        # get endpoint cert and create ssl context
        url_parsed = urllib_parse.urlparse(url)
        server_cert = ssl.get_server_certificate((url_parsed.hostname,url_parsed.port))
        ssl_context = ssl.create_default_context(cadata=server_cert)
        check_hostname=False
        ssl_context.check_hostname = check_hostname

        # get response
        response = urllib_request.urlopen(request, context=ssl_context)
        #status = response.getcode()
        returns = response.read() #.decode('utf-8')
        returned_json = json.loads(returns)
        #return returned_json
        returned_results = json.loads(returned_json['results'])

        result_set = []
        # TODO check for same length or different length
        for (x,y) in iter(zip(data_records, returned_results)):
            for key in y:
                x[key] = y[key]
            result_set.append(x)
            #yield x

        return result_set

if __name__ == "__main__":
    dispatch(ComputeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
