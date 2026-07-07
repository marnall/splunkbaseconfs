'''
This is a simple class for writing data in the chunked format expected by
splunk
'''

import sys
import json

class ChunkedWriter:

    def __init__(self, stream_type="raw", out=sys.stdout):
       self.out = out
       self.stream_type = stream_type

    def write(self, header, body):
        '''
        Writes data to stdout using chunked streaming protocol, as expected 
        by splunk search process' stdin

        Format:
        chunked 1.0,<header-size>,<body-size>

        Example:
        chunked 1.0,1024,65535 
        {"stream_type": "raw", "some": "header-stuff like",
         "field.source": "/foo/bar/baz.log" ... }
        [raw 64K payload body, some of it's properties can be described in 
         the header] 
        '''
        hlen = 0
        blen = 0
        bstr = ''
        hstr = ''
        if header != None: 
           if not 'stream_type' in header:
              header['stream_type'] = self.stream_type
           hstr = json.dumps(header)
           hlen = len(hstr)
        if body != None:
           bstr = str(body)
           blen = len(bstr)

        self.out.write("chunked 1.0,%d,%d\n" % (hlen,blen))
        self.out.write(hstr)
        self.out.write(bstr)   
