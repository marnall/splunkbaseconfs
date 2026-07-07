import sys,re
from pywhat import identifier
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration

@Configuration()
class whatthis(StreamingCommand):
  def stream(self, records):
    for record in records:
        id_obj = identifier.Identifier()
        record['what'] = id_obj.identify({str(record['_raw'])}, api=True)
        yield record

if __name__ == "__main__":
  dispatch(whatthis, sys.argv, sys.stdin, sys.stdout, __name__)
