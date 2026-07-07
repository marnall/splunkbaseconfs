import sys
import search_request
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

@Configuration(type='reporting')
class Abuseipdbblacklist(GeneratingCommand):
  """ %(synopsis)
  Returns a one-off copy of the abuseIPDB blacklist.
  """

  confidenceMinimum = Option(doc=
    '''
    **Syntax:** **confidenceMinimum=***<number>*
    **Description:** Set confidenceMinimum
    ''',
    validate=validators.Integer(minimum=25, maximum=100))
  
  limit = Option(doc=
    '''
    **Syntax:** **limit=***<number>*
    **Description:** Set limit
    ''',
    validate=validators.Integer(minimum=1, maximum=500000))

  onlyCountries = Option(doc=
    '''
    **Syntax:** **onlyCountries=***<string>*
    **Description:** Set onlyCountries
    ''')

  exceptCountries = Option(doc=
    '''
    **Syntax:** **exceptCountries=***<string>*
    **Description:** Set exceptCountries
    ''')
  
  ipVersion = Option(doc=
    '''
    **Syntax:** **ipVersion=***<string>*
    **Description:** Set ipVersion
    ''')
  
  def generate(self):

    params = {}
    if self.confidenceMinimum:
      params['confidenceMinimum'] = self.confidenceMinimum
    if self.limit:
      params['limit'] = self.limit
    if self.onlyCountries:
      params['onlyCountries'] = self.onlyCountries
    if self.exceptCountries:
      params['exceptCountries'] = self.exceptCountries
    if self.ipVersion:
      params['ipVersion'] = self.ipVersion
    
    blacklist = search_request.make_blacklist_request_in_search_event(self.service, None, params)

    for record in blacklist:
      yield record

dispatch(Abuseipdbblacklist, sys.argv, sys.stdin, sys.stdout, __name__)
