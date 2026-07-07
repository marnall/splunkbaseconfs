import sys
import re
import custom_regex
import search_request
import abuse_helpers
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class Abuseipdbreports(StreamingCommand):
  """ %(synopsis)
  Returns the AbuseIPDB reports for the given IP address. IP is required.
  """

  ip = Option(doc=
    '''
    **Syntax:** **ip=***<fieldname>*
    **Description:** IP Address to retrieve reports on
    ''',
    require=True)
  
  maxAgeInDays = Option(doc=
    '''
    **Syntax:** **maxAgeInDays=***<number>*
    **Description:** Set maxAgeInDays
    ''',
    validate=validators.Integer(minimum=1, maximum=365))
  
  numReports = Option(doc=
    '''
    **Syntax:** **numReports=***<number>*
    **Description:** Set the number of reports to return
    ''',
    validate=validators.Integer(minimum=1, maximum=500))

  def stream(self, records):

    ip_is_literal = abuse_helpers.is_valid_ip(self.ip)
    ip_is_fieldname = re.match(custom_regex.fieldname_pattern, self.ip)

    params = {}
    if self.maxAgeInDays:
      params['maxAgeInDays'] = self.maxAgeInDays
    if self.numReports:
      params['perPage'] = self.numReports
    else:
      params['perPage'] = 1000

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
      
      reports = search_request.make_reports_request_in_search_event(self.service, record, params)

      for report in reports:
        yield report

dispatch(Abuseipdbreports, sys.argv, sys.stdin, sys.stdout, __name__)
