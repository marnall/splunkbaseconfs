import splunk.Intersplunk as si
import os
import base64
import sys
import struct
import re

charset = "0123456789abcdef"
groupings = [6, 6, 8, 4]

def random_long():
    return struct.unpack("<L", os.urandom(4))[0]

def get_group(num, charset):
    charset_len = len(charset)
    result = ""
    while num > 0:
        idx = random_long() % charset_len
        result += charset[idx]
        num -= 1
    return result

def generate_guid(groupings, charset):
    "wrap guid creation in a function"
    guid = ""
    for length in groupings:
        guid += get_group(length, charset) + "-"
    guid = guid[:-1]

    return guid

if __name__ == '__main__':
    keywords, options = si.getKeywordsAndOptions()
    if 'charset' in options:
        charset = options['charset']
    if 'groupings' in options:
        grouping_match = re.match(r"^(\d+,)*\d+$", options['groupings'])
        if grouping_match is None:
            si.parseError("'groupings' must be a list of numeric lengths separated by commas, e.g. \"6,6,8,4\"")
        groupings = [int(i) for i in options['groupings'].split(",")]
    if len(keywords) < 1:
        si.parseError("Must specify an output field for guid")
    results = si.readResults(None, None, True)
    messages = {}
    for res in results:
        res[keywords[0]] = generate_guid(groupings, charset)
    si.outputResults(results, messages=messages)
