import sys
import search_request
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration

@Configuration()
class Abuseipdbaccount(StreamingCommand):
  """ %(synopsis)
  Returns the account information for the AbuseIPDB API key.
  """

  def stream(self, records):

    for record in records:
      
      params = {}
      record = search_request.make_account_request_in_search_event(self.service, record, params)
      yield record

dispatch(Abuseipdbaccount, sys.argv, sys.stdin, sys.stdout, __name__)
