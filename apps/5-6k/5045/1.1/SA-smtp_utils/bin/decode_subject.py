# -*- coding: utf-8 -*-
# v 1.0.2 - python 3 changes plus skip events without the field
# Dominique Vocat
from __future__ import print_function
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators
import email.header
from email.header import Header, decode_header, make_header
import sys

@Configuration()

def decode_mime_words(s):
    return u''.join(
        word.decode(encoding or 'utf8') if isinstance(word, bytes) else word
        for word, encoding in email.header.decode_header(s))


@Configuration()
class decodesubject(StreamingCommand):
    field = Option(name='fieldname', require=True)
    show_error = Option(name='show_error', require=False, default=False, validate=validators.Boolean())

    def stream(self, events):
 
        for event in events:
            if self.field in event:
                print(event[self.field], file=sys.stderr)
                try:
                    #event[self.field] = decode_mime_words(str(event[self.field]).encode('utf-8'))
                    event[self.field] = str(make_header(decode_header(event[self.field])))
                except Exception as e:
                    event[self.field] = event[self.field]
                    print(str(e), file=sys.stderr)
                    print(str(Exception), file=sys.stderr)
                    if not self.show_error :
                        pass #raise e
            yield event

#if __name__ == "__main__":
#    dispatch(decodesubject, sys.argv, sys.stdin, sys.stdout, __name__)
dispatch(decodesubject, sys.argv, sys.stdin, sys.stdout, __name__)