from __future__ import print_function
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import sys
import socket
import struct


@Configuration()
class IPDecodeCommand(StreamingCommand):

    def stream(self, records):
        self.logger.debug('IPDecodeCommand: %s', self)  # logs command line

        for record in records:
            for field in self.fieldnames:
                record[field] = self.int2ip(record[field])
            yield record

    def int2ip(self, intIP):
        try:
            return socket.inet_ntoa(struct.pack('!L', int(intIP)))
        except:
            return '-'

dispatch(IPDecodeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
