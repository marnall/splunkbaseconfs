#Copyring 2010 Splunk, Inc
#Written initially by Vincent Bumgarner, December 20th, 2010
#vbumgarner@splunk.com

import json
import types
import sys,splunk.Intersplunk

def handle_node(dest, input, key_prefix=[]):
    if type(input) is types.DictType:
        handle_dict(dest, input, key_prefix)
    elif type(input) is types.ListType:
        handle_list(dest, input, key_prefix)
    else:
        #actually insert the value if it is neither a dict nor a list
        dest_key = '_'.join(key_prefix)

        #handle multiple values
        if dest_key in dest:
            #this is only the second value, so convert value to a list
            if type(dest[dest_key]) is not types.ListType:
                dest[dest_key] = [dest[dest_key]]
            #append the value to the list
            dest[dest_key].append(str(input))
        else:
            #insert the simple value
            dest[dest_key] = str(input)

def handle_list(dest, input, key_prefix=[]):
    for v in input:
        handle_node(dest, v, key_prefix)

def handle_dict(dest, input, key_prefix=[]):
    for k,v in input.items():
        #add to the key prefix
        key_prefix.append(k)
        handle_node(dest, v, key_prefix)
        key_prefix.pop()


try:
    #get the results we've been handed
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

    #loop through the results, looking for a json field, otherwise extracting from _raw
    for r in results:
        if 'json' in r:
            json_text = r['json']
        else:
            raw = r['_raw']
            json_text = raw[ raw.index( '{' ) : raw.rindex( '}' )+1 ]
        #the root node should be a dict
        handle_dict(r, json.loads(json_text))

except:
    import traceback
    stack =  traceback.format_exc()
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

#return the results
splunk.Intersplunk.outputResults( results )

