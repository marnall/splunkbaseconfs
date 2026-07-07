import sys
import re
import custom_regex
import search_request
import abuse_helpers
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option

@Configuration()
class Abuseipdbreport(StreamingCommand):
  """
  Submits a report for the given IP address to the AbuseIPDB database. IP and categories are required.
  """

  ip = Option(doc=
    '''
    **Syntax:** **ip=***<ipAddress>*
    **Description:** IP Address to check
    ''',
    require=True)

  categories = Option(doc=
    '''
    **Syntax:** **categories=***<list>*
    **Description: **List of categories for the report
    ''',
    require=True)

  comment = Option(doc=
    '''
    **Syntax:** **comment=***<string>*
    **Description: **Set comment parameter
    ''',)

  timestamp = Option(doc=
    '''
    **Syntax:** **timestamp=***<timestamp>*
    **Description: **Set timestamp parameter
    ''',
    )

  def stream(self, records):

    for record in records:

      #check if search received an IP, field of IPs, or an invalid parameter for IP
      if abuse_helpers.is_valid_ip(self.ip):
        ip = self.ip
      elif re.match(custom_regex.fieldname_pattern, self.ip):
        if self.ip in record and abuse_helpers.is_valid_ip(record[self.ip]):
          ip = record[self.ip]
        else:
          yield record
          continue
      else:
        raise ValueError('The ip parameter does not contain a valid fieldname or ip address.')

      if re.match(custom_regex.categories_pattern, self.categories):
        categories = self.categories
      else:
        raise ValueError('The categories parameter does not match the requested format.')

      # e.g. if comment is set but the comment field isn't found
      if self.comment and self.comment not in record:
        raise ValueError('The comment parameter does not contain a valid fieldname.')

      # no way to disambiguate between general comment for all reports and specific per report comments. right now only per-report comments are supported
      if self.comment:
        comment = record[self.comment]
      else:
        comment = None

      if self.timestamp:
        if re.match(custom_regex.timestamp_pattern, self.timestamp):
          timestamp = self.timestamp
        elif re.match(custom_regex.fieldname_pattern, self.timestamp):
          timestamp = record[self.timestamp]
        else:
          raise ValueError('The provided timestamp is not in the ISO 8601 format that is required.')
      else:
        timestamp = None

      params = {}
      params['ip'] = ip
      params['categories'] = categories
      if comment:
        params['comment'] = comment
      if timestamp:
        params['timestamp'] = timestamp

      record  = search_request.make_report_request_in_search_event(self.service, record, params)

      yield record

dispatch(Abuseipdbreport, sys.argv, sys.stdin, sys.stdout, __name__)
