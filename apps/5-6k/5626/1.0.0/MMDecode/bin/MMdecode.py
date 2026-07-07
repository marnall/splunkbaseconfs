#!/usr/bin/env python
from email.header import decode_header
import quopri
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, StreamingCommand, Configuration, Option, validators


def encoding_shift(orig_encoding):
    target_encoding=orig_encoding
    if(orig_encoding.lower() == 'gb2312'):
        target_encoding='gb18030'

    return target_encoding

def mime_decode(payload):
    if len(payload) == 0:
        return payload
    payload=payload.strip()
    payload_arr=payload.split('\\r\\n ')
    result_str=[]
    
    for p in payload_arr:
        try:
            if "?B?" in p:
                try:
                    tmp =decode_header(p)
                    (byte_str,encoding)=tmp[0]
                    encoding=encoding_shift(encoding)
                    decoded_str=byte_str.decode(encoding,'ignore')
                    result_str.append(decoded_str)
                except Exception as e:
                    result_str.append(p)
            elif "?b?" in p:
                try:
                    tmp =decode_header(p)
                    (byte_str,encoding)=tmp[0]
                    encoding=encoding_shift(encoding)
                    decoded_str=byte_str.decode(encoding,'ignore')
                    result_str.append(decoded_str)
                except Exception as e:
                    result_str.append(p)
            elif "?Q?" in p:
                try:
                    code_arr=p.split('?')
                    base64_str=code_arr[3]
                    encoding=encoding_shift(code_arr[1])
                    byte_str=quopri.decodestring(base64_str,True)
                    decoded_str=byte_str.decode(encoding,'ignore')
                    result_str.append(decoded_str)
                except Exception as e:
                    result_str.append(p)
            elif "?q?" in p:
                try:
                    code_arr=p.split('?')
                    base64_str=code_arr[3]
                    encoding=encoding_shift(code_arr[1])
                    byte_str=quopri.decodestring(base64_str,True)
                    decoded_str=byte_str.decode(encoding,'ignore')
                    result_str.append(decoded_str)
                except Exception as e:
                    result_str.append(p)
        except Exception as e:
            result_str.append(e)
    if(len(result_str)==0):
        return ""
    return "".join(result_str)


@Configuration()
class MMDecodeCommand(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """
    def stream(self, events):
        # get the argument - fieldname with mime-encoded string
        field_in = self.fieldnames[0]
        field_out = self.fieldnames[1]
        for record in events:
            if field_in in record:
                record[field_out] = mime_decode(record[field_in])
                yield record


dispatch(MMDecodeCommand, sys.argv, sys.stdin, sys.stdout, __name__)

