import re
import sys
import custom_regex
import search_request
import abuse_helpers
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class Abuseipdbcheckblock(StreamingCommand):
  """
  Checks the given network subnet against the AbuseIPDB database. network is required.
  """

  network = Option(doc=
    '''
    **Syntax:** **network=***<fieldname>*
    **Description:** Subnet to check
    ''',
    require=True)
  
  maxAgeInDays = Option(doc=
    '''
    **Syntax:** **maxAgeInDays=***<number>*
    **Description:** Set maxAgeInDays
    ''',
    validate=validators.Integer(minimum=1, maximum=365))

  def stream(self, records):
    
    network_is_valid = abuse_helpers.is_valid_cidr(self.network)
    network_is_fieldname = re.match(custom_regex.fieldname_pattern, self.network)

    params = {}
    if self.maxAgeInDays:
      params['maxAgeInDays'] = self.maxAgeInDays

    for record in records:
      if network_is_valid:
        network = self.network
      elif network_is_fieldname:
        if self.network in record and abuse_helpers.is_valid_cidr(record[self.network]):
          network = record[self.network]
        else:
          yield record
          continue
      else:
        raise ValueError('The ip parameter does not contain a valid fieldname or ip address.')

      params['network'] = network

      record = search_request.make_checkblock_request_in_search_event(self.service, record, params)

      yield record

dispatch(Abuseipdbcheckblock, sys.argv, sys.stdin, sys.stdout, __name__)
