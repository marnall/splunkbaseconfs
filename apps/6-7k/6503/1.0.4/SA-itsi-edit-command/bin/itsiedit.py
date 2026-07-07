import itsi_declare

import splunklib.client as client
import sys,re, subprocess, requests, json
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
from json.decoder import JSONDecodeError

@Configuration(local=True)
class itsieditSearchCommand(StreamingCommand):
  
  fieldField = Option(
    doc='''
      **Syntax:** **fieldname=***<fieldname>*
      **Description:** Name of the input field''',
      require=True)

  valueField = Option(
    doc='''
      **Syntax:** **fieldname=***<fieldname>*
      **Description:** Name of the input field''',
      require=True)

  episodeidField = Option(
    doc='''
      **Syntax:** **fieldname=***<fieldname>*
      **Description:** Name of the input field''',
      require=True)


  def stream(self, records):

    self.logger.debug("session token key is: %s", self._metadata.searchinfo.session_key)
    my_headers = {'Authorization' : 'Bearer '+self._metadata.searchinfo.session_key, 'Content-Type':'application/json'}

    for record in records:
      field = record[self.fieldField]
      value = record[self.valueField]
      episodeid = record[self.episodeidField]

      payload = {field: value}
      if field == "ack":
        payload = {"status":"2","action_type":"acknowledge","owner":value,"_key":episodeid} 

      payload = json.dumps(payload)
      uri = self._metadata.searchinfo.splunkd_uri
   
      response = requests.post("{}/servicesNS/nobody/SA-ITOA/event_management_interface/notable_event_group/{}/?is_partial_data=1".format(uri,episodeid), headers=my_headers,verify=False,data=payload)
      record['response'] = response.text

      yield record

if __name__ == "__main__":
    dispatch(itsieditSearchCommand, sys.argv, sys.stdin, sys.stdout, __name__)
