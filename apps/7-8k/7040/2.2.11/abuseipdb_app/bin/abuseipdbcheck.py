import re
import sys
import custom_regex
import search_request
import abuse_helpers
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class Abuseipdbcheck(StreamingCommand):
  """
  Checks the given IP address against the AbuseIPDB database. IP is required.
  """

  ip = Option(doc=
    '''
    **Syntax:** **ip=***<fieldname>*
    **Description:** IP Address to check
    ''',
    require=True)
  
  maxAgeInDays = Option(doc=
    '''
    **Syntax:** **maxAgeInDays=***<number>*
    **Description:** Set maxAgeInDays
    ''',
    validate=validators.Integer(minimum=1, maximum=365))

  verbose = Option(doc=
    '''
    **Syntax:** **verbose=***<value>*
    **Description:** Set verbose
    ''',
    validate=validators.Boolean())

  def stream(self, records):
    
    ip_is_literal = abuse_helpers.is_valid_ip(self.ip)
    ip_is_fieldname = re.match(custom_regex.fieldname_pattern, self.ip)

    params = {}
    if self.maxAgeInDays:
      params['maxAgeInDays'] = self.maxAgeInDays
    if self.verbose:
      params['verbose'] = "1"

    for record in records:
      if ip_is_literal:
        ip = self.ip
      elif ip_is_fieldname:
        if self.ip in record and abuse_helpers.is_valid_ip(record[self.ip]):
          ip = record[self.ip]
        else:
          yield record
          continue
      else:
        raise ValueError('The ip parameter does not contain a valid fieldname or ip address.')

      params['ipAddress'] = ip

      record = search_request.make_check_request_in_search_event(self.service, record, params)

      yield record

dispatch(Abuseipdbcheck, sys.argv, sys.stdin, sys.stdout, __name__)
