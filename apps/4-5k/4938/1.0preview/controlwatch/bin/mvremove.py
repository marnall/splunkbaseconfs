import splunk.Intersplunk as si
import os
import base64
import sys
import collections

def is_sequence(obj):
    if isinstance(obj, collections.Sequence) and not \
       isinstance(obj, basestring):
        return True
    return False

if __name__ == '__main__':
    try:
        keywords, options = si.getKeywordsAndOptions()
        if len(keywords) < 2:
            si.parseError("Must specify a value to remove and a field to remove from")
        results = si.readResults(None, None, True)
        messages = {}
        for res in results:
            # si.parseError(res[keywords[1]].split('\n'))
            # si.parseError(res[keywords[0]])
            if keywords[0] in res and keywords[1] in res:
                vals_to_remove = res[keywords[0]]
                if not is_sequence(vals_to_remove):
                    vals_to_remove = [vals_to_remove]
                for remove_val in vals_to_remove:
                    values = res[keywords[1]]
                    if isinstance(values, basestring) == True:
                        if values == remove_val:
                            res[keywords[1]] = ""
                    else:
                        res[keywords[1]] = filter(lambda x: x != remove_val, res[keywords[1]])
        si.outputResults(results, messages=messages)
    except KeyError as e:
        si.parseError("Error source: {}".format(e))
