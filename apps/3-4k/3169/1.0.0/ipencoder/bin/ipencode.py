from __future__ import print_function
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import sys
import socket
import struct


@Configuration()
class IPEncodeCommand(StreamingCommand):

    def stream(self, records):
        self.logger.debug('IPEncodeCommand: %s', self)  # logs command line

        for record in records:
            for field in self.fieldnames:
                record[field] = self.ip2int(record[field])
            yield record

    def ip2int(self, intIP):
        try:
            return struct.unpack('!L', socket.inet_aton(intIP))
        except:
            return '-'

dispatch(IPEncodeCommand, sys.argv, sys.stdin, sys.stdout, __name__)
