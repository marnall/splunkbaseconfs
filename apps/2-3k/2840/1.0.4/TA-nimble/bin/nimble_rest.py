import sys
import os

from splunklib.modularinput import *
import httplib2
import requests,json
import traceback

class NimbleREST(Script):

    def get_scheme(self):
        # Setup scheme.
        scheme = Scheme("Nimble Array Rest API")
        scheme.description = "Streams information about array from Nimble REST API"
        scheme.use_external_validation = True

        #Add arguments
        array_argument = Argument("array")
        array_argument.data_type = Argument.data_type_string
        array_argument.description = "Host or IP Address of Nimble Array"
        array_argument.required_on_create = True
        scheme.add_argument(array_argument)

        username_argument = Argument("username")
        username_argument.data_type = Argument.data_type_string
        username_argument.description = "Nimble Array username"
        username_argument.required_on_create = True
        scheme.add_argument(username_argument)

        password_argument = Argument("password")
        password_argument.data_type = Argument.data_type_string
        password_argument.description = "Nimble Array Password"
        password_argument.required_on_create = True
        scheme.add_argument(password_argument)

        return scheme

    def stream_events(self, inputs, ew):
        # Splunk Enterprise calls the modular input, 
        # streams XML describing the inputs to stdin,
        # and waits for XML on stdout describing events.
        ca_bundle_path = os.path.join(os.environ.get('SPLUNK_HOME'), 'etc', 'apps', 'TA-nimble', 'certs', 'nimble_cacert.pem')

        for input_name,input_item in inputs.inputs.iteritems():
            ARRAY = input_item["array"]
            USERNAME = input_item["username"]
            PASSWORD = input_item["password"]
            is_authenticated = False
            ew.log("INFO","Starting Nimble Array REST input processing:  ARRAY=%s USERNAME=%s" % (ARRAY,USERNAME))

            try:
               #### AUTHENTICATION
               ew.log("INFO", 'Authenticating with array REST service')
               DATASTRING={'data':{'password':PASSWORD,"username":USERNAME}}
               URL = 'https://%s:5392/v1/tokens' % (ARRAY)
               r = requests.post(URL, data=json.dumps(DATASTRING), verify='%s' % ca_bundle_path)
               session_token = r.json()['data']['session_token']
               session_header = {'X-Auth-Token' : session_token}
               is_authenticated = True

            except Exception as e:
               ew.log('ERROR','Error authenticating with the Nimble Array REST Endpoint : %s (see trace for details)' % e)
               traceback.print_exc()

            if is_authenticated :
               try:
                  #### VOLUMES DETAIL
                  ew.log("INFO", 'Getting volume data from array REST service')
                  URL = 'https://%s:5392/v1/volumes/detail' % (ARRAY)            
                  r = requests.get(URL, headers=session_header, verify='%s' % ca_bundle_path)
                  data = r.json()['data']
                  for row in data:
                      raw_event = Event()
                      raw_event.stanza = input_name
                      raw_event.source = "nimble:rest:volumes_detail"
                      raw_event.host = ARRAY
                      raw_event.data = json.dumps(row)
                      raw_event.sourcetype = "nimble:rest:volumes_detail"
                      ew.write_event(raw_event)

                  #### ARRAY DETAIL
                  ew.log("INFO", 'Getting array details from array REST service')
                  URL = 'https://%s:5392/v1/arrays/detail' % (ARRAY)
                  r = requests.get(URL, headers=session_header, verify='%s' % ca_bundle_path)
                  data = r.json()['data']
                  for row in data:
                      raw_event = Event()
                      raw_event.stanza = input_name
                      raw_event.source = "nimble:rest:arrays_detail"
                      raw_event.host = ARRAY
                      raw_event.data = json.dumps(row)
                      raw_event.sourcetype = "nimble:rest:arrays_detail"
                      ew.write_event(raw_event)
   
                  #### INITIATORS DETAIL
                  ew.log("INFO", 'Getting initiator details from array REST service')
                  URL = 'https://%s:5392/v1/initiators/detail' % (ARRAY)
                  r = requests.get(URL, headers=session_header, verify='%s' % ca_bundle_path)
                  data = r.json()['data']
                  for row in data:
                      raw_event = Event()
                      raw_event.source = "nimble:rest:initiators_detail"
                      raw_event.host = ARRAY
                      raw_event.stanza = input_name
                      raw_event.data = json.dumps(row)
                      raw_event.sourcetype = 'nimble:rest:initiators_detail'
                      ew.write_event(raw_event)

                  #### INITIATOR_GROUPS DETAIL
                  ew.log("INFO", 'Getting initiator group details from array REST service')
                  URL = 'https://%s:5392/v1/initiator_groups/detail' % (ARRAY)
                  r = requests.get(URL, headers=session_header, verify='%s' % ca_bundle_path)
                  data = r.json()['data']
                  for row in data:
                      raw_event = Event()
                      raw_event.source = "nimble:rest:initiator_groups_detail"
                      raw_event.host = ARRAY
                      raw_event.stanza = input_name
                      raw_event.data = json.dumps(row)
                      raw_event.sourcetype = 'nimble:rest:initiator_groups_detail'
                      ew.write_event(raw_event)

                  #### VOLUME_COLLECTIONS DETAIL
                  ew.log("INFO", 'Getting volume collection details from array REST service')
                  URL = 'https://%s:5392/v1/volume_collections/detail' % (ARRAY)
                  r = requests.get(URL, headers=session_header, verify='%s' % ca_bundle_path)
                  data = r.json()['data']
                  for row in data:
                      raw_event = Event()
                      raw_event.source = "nimble:rest:volume_collections_detail"
                      raw_event.host = ARRAY
                      raw_event.stanza = input_name
                      raw_event.data = json.dumps(row)
                      raw_event.sourcetype = 'nimble:rest:volume_collections_detail'
                      ew.write_event(raw_event)

                  #### POOLS DETAIL
                  ew.log("INFO", 'Getting pool details from array REST service')
                  URL = 'https://%s:5392/v1/pools/detail' % (ARRAY)
                  r = requests.get(URL, headers=session_header, verify='%s' % ca_bundle_path)
                  data = r.json()['data']
                  for row in data:
                      raw_event = Event()
                      raw_event.source = "nimble:rest:pools_detail"
                      raw_event.host = ARRAY
                      raw_event.stanza = input_name
                      raw_event.data = json.dumps(row)
                      raw_event.sourcetype = 'nimble:rest:pools_detail'
                      ew.write_event(raw_event)

                  #### REPLICATION_PARTNERS DETAIL
                  ew.log("INFO", 'Getting replication partner details from array REST service')
                  URL = 'https://%s:5392/v1/replication_partners' % (ARRAY)
                  r = requests.get(URL, headers=session_header, verify='%s' % ca_bundle_path)
                  data = r.json()['data']
                  for row in data:
                      raw_event = Event()
                      raw_event.source = "nimble:rest:replication_partners_detail"
                      raw_event.host = ARRAY
                      raw_event.stanza = input_name
                      raw_event.data = json.dumps(row)
                      raw_event.sourcetype = 'nimble:rest:replication_partners_detail'
                      ew.write_event(raw_event)

               except Exception as e:
                  ew.log('ERROR','Error retrieving data from the Nimble Array REST Endpoint data: %s (see trace for details)' % e)
                  traceback.print_exc()
   
if __name__ == "__main__":
    sys.exit(NimbleREST().run(sys.argv))
