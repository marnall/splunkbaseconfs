import sys
from splunklib.searchcommands import (dispatch, StreamingCommand, Option, Configuration, validators)
from html2text import HTML2Text  # or whichever library you're using for HTML to text conversion

@Configuration()
class HTMLToTextCommand(StreamingCommand):
    """Converts HTML to plain text."""
    
    fieldname = Option(require=True, validate=validators.Fieldname())

    def stream(self, records):
        h = HTML2Text()
        h.ignore_links = True
        for record in records:
            if self.fieldname in record:
                record[self.fieldname + "_plaintext"] = h.handle(record[self.fieldname]).strip()
            yield record

dispatch(HTMLToTextCommand, sys.argv, sys.stdin, sys.stdout, __name__)

