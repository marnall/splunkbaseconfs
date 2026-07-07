import splunk, sys, json, os, logging, requests, configparser,time,hashlib, xml.etree.ElementTree as elementTree
from splunk.persistconn.application import PersistentServerConnectionApplication
from urllib.parse import urlencode
from urllib.parse import unquote, unquote_plus
from http.client import HTTPConnection

conf = os.path.join(os.path.join(os.environ.get('SPLUNK_HOME')), 'etc', 'apps', 'TA-rest-interface', 'local', 'ta_rest_interface_settings.conf')
config = configparser.ConfigParser()

logfile = os.sep.join([os.environ['SPLUNK_HOME'], 'var', 'log', 'splunk', 'ta_rest_interface_service.log'])
logging.basicConfig(filename=logfile,level=logging.DEBUG) #SET TO DEBUG IF YOU WANT MORE LOGZ
HTTPConnection.debuglevel = 0

class TriforkRest(PersistentServerConnectionApplication):
    def __init__(self, _command_line, _command_arg):
        super(PersistentServerConnectionApplication, self).__init__()

    # Handle a syncronous from splunkd.
    def handle(self, in_string):
        """
        Called for a simple synchronous request.
        @param in_string: request data passed in
        @rtype: string or dict
        @return: String to return in response.  If a dict was passed in,
                 it will automatically be JSON encoded before being returned.
        """


        if not os.path.exists(conf):
          logging.debug("Conf file {} dosnt exist,creating".format(conf))
          with open(conf, 'w') as f:
            f.write('[Settings]\nhecToken = insertHecToken\nhecHost = https://127.0.0.1:8088\n')  
        
        config.read(conf)
        hecToken = config.get("Settings","hecToken") 
        hecHost = config.get("Settings","hecHost")  

        args = self.parse_in_string(in_string)
        logging.debug(args)
        logging.debug("Using token: {}".format(hecToken))

        query = args['query_parameters']

        splunkId = hashlib.sha1(bytes(str(time.time()), encoding="utf-8")).hexdigest()[:10]
        logging.debug("Using this ID for this transaction: {}".format(splunkId))

        payload = args['payload']
        payload = unquote_plus(payload)
        orgPayload = payload
        logging.debug("Payload-PRE: {}".format(payload))


        dataType = ""
        endpoint = ""
        if args['rest_path'] == "/rest-event":
          # long story short, extract the event from data, append splunkRestId to it and then merge it again with the original payload
          payload = json.loads(payload)
          orgPayload = json.loads(orgPayload)
          payload = json.dumps(payload['event'])
          if payload.startswith('"') and payload.endswith('"'):
            payload = payload[1:-1]

          logging.debug("Payload-event: {}".format(payload))

        if self.is_json(payload) and "{" in payload:
          dataType = "json"
          logging.debug("looks like json")
          payload = json.loads(payload)
          payload['splunkRestId'] = splunkId

        elif self.is_xml(payload):
          logging.debug("looks like xml")
          xml = elementTree.fromstring(payload)
          sid = elementTree.Element("splunkRestId")
          sid.text = splunkId
          xml.append(sid)
          payload = elementTree.tostring(xml).decode("utf-8") 

        else:
          logging.debug("looks like ordinary text")
          payload += "\nsplunkRestId={}".format(splunkId)


        endpoint = ""
        if args['rest_path'] == "/rest-raw":
          endpoint = "raw"
          if dataType == "json":
            payload = json.dumps(payload)

        if args['rest_path'] == "/rest-event":
          endpoint = "event"
          orgPayload['event'] = payload
          payload = json.dumps(orgPayload)

        logging.debug("Payload-POST: {}".format(payload))

        my_headers = {'Authorization' : 'Splunk '+hecToken}
        response = requests.post("{}/services/collector/{}".format(hecHost,endpoint), params=query, headers=my_headers,verify=False,data=payload)
        logging.debug(response.text)

        responseJson = json.loads(response.text)
        if responseJson['code'] == 0:
          responseJson['splunkRestId'] = splunkId


        return {'payload': responseJson, 'status': response.status_code} 

    def handleStream(self, handle, in_string):
        """
        For future use
        """
        raise NotImplementedError(
            "PersistentServerConnectionApplication.handleStream")

    def done(self):
        """
        Virtual method which can be optionally overridden to receive a
        callback after the request completes.
        """
        pass


    def is_xml(self, myxml):
        try:
            elementTree.fromstring(myxml)
        except elementTree.ParseError:
            return False
        return True

    def is_json(self, myjson):
        try:
            json.loads(myjson)
        except ValueError as e:
            return False
        return True

    def convert_to_dict(self, query):
        """
        Create a dictionary containing the parameters.
        """
        parameters = {}

        for key, val in query:

            # If the key is already in the list, but the existing entry isn't a list then make the
            # existing entry a list and add thi one
            if key in parameters and not isinstance(parameters[key], list):
                parameters[key] = [parameters[key], val]

            # If the entry is already included as a list, then just add the entry
            elif key in parameters:
                parameters[key].append(val)

            # Otherwise, just add the entry
            else:
                parameters[key] = val

        return parameters

    def parse_in_string(self, in_string):
        """
        Parse the in_string
        """

        params = json.loads(in_string)

        params['method'] = params['method'].lower()

        params['form_parameters'] = self.convert_to_dict(params.get('form', []))
        params['query_parameters'] = self.convert_to_dict(params.get('query', []))
        return params
