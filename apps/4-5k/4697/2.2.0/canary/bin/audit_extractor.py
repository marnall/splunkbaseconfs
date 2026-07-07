# Copyright (C) 2022-2026 Sideview LLC.  All Rights Reserved.

import json
import re
import sys
import splunk

from splunklib.searchcommands import dispatch, StreamingCommand, Configuration #, Option, validators


ST_COUNT_PREFIX = "sourcetype_count__"

def extract_fields_from_audit_events(raw_text):
    values = {}

    match_from_end = re.compile(r"(?ms),\s((?P<key>[\w\-_]+)='(?P<value>[^']*)'\Z|(?P<key2>[\w\-_]+)=\"(?P<value2>[^\"]*)\"\Z|(?P<key3>[\w\-_]+)=(?P<value3>[^,|^ ]+)\Z)")
    match_from_start = re.compile(r"(?ms),\s((?P<key>[\w\-_]+)='(?P<value>[^']*)'|(?P<key2>[\w\-_]+)=\"(?P<value2>[^\"]*)\"|(?P<key3>[\w\-_]+)=(?P<value3>[^,]+))")
    finish_him = re.compile(r"(?ms)^\,\s(?P<key>search)='(?P<value>.+)'$")

    raw_text = raw_text.rstrip("]")

    loud = False

    for i, regex in enumerate([match_from_end, match_from_start, finish_him]):
        #print("NEW REGEX %s" % i)
        while True:
            if loud:
                print("\ni=%s about to search \n%s\n" % (i, raw_text))
            match = re.search(regex, raw_text)
            if loud:
                print(type(match))
            if match is None:
                if loud:
                    print("match is none. i=%s breaking" % i)
                break
            if loud:
                print(match[0])
                print(match.groupdict())
            key_dict = match.groupdict()

            key = key_dict.get("key",  None)
            key2 = key_dict.get("key2", None)
            key3 = key_dict.get("key3", None)
            value = key_dict.get("value", None)
            value2 = key_dict.get("value2", None)
            value3 = key_dict.get("value3", None)
            if not key and not value:
                key = key2
                value = value2
            if not key and not value:
                key = key3
                value = value3
            #print("key is %s and value is %s" % (key, value))
            #we save 'search' for the very end.
            if key=="search" and i<2:
                break
            if key or value:
                # if everything is going according to plan,
                # the key will NEVER be in there already.
                if key not in values:
                    values[key] = value

            if loud:
                print("values now is")
                print(values)
            if i==0:
                index = len(raw_text) - len(match[0])
                raw_text = raw_text[:index]
            elif i==1:
                start_index = raw_text.find(match[0]) + len(match[0])
                #print("match is x" + match[0] + "x")
                #print("start index is " + str( start_index ))
                raw_text = raw_text[start_index:]
            elif i==2:
                break


            #print("new raw text is now \n" + raw_text)

    #print("WE ARE LEFT WITH " + raw_text)


    #print(values)



    return values


@Configuration()
class AuditExtractorCommand(StreamingCommand):

    def stream(self, records):
        """ """

        for record in records:

            record["commandApp"] = "canary"
            sourcetype = record.get("sourcetype", None)
            index = record.get("index", None)
            if index!="_audit" or sourcetype != "audittrail":
                yield record
                continue

            event_text = record.get("_raw", None)
            assert(event_text is not None)

            explicit_dict = extract_fields_from_audit_events(event_text)


            sourcetypes_data = {}

            total = 0
            for key in explicit_dict:
                if key.find(ST_COUNT_PREFIX) == 0:
                    name = key.replace(ST_COUNT_PREFIX,"")
                    count = int(explicit_dict.get(key))
                    sourcetypes_data[name] = count
                    total += count


            sourcetypes = []
            sourcetypes_verbose = []
            sourcetypes_ratio = []
            for name in sourcetypes_data:
                count = sourcetypes_data.get(name)
                ratio = count / total
                sourcetypes.append(name)
                sourcetypes_verbose.append("%s (%d)" % (name,count))
                sourcetypes_ratio.append("%s::%f" % (name,ratio))


            record["keys_written"] = ",".join(explicit_dict.keys())
            for key in explicit_dict:
                record[key] = explicit_dict.get(key)
            record["sourcetypes"] = sourcetypes
            record["sourcetypes_verbose"] = sourcetypes_verbose
            record["sourcetypes_ratio"] = sourcetypes_ratio

            yield record


dispatch(AuditExtractorCommand, sys.argv, sys.stdin, sys.stdout, __name__)
