# This script flattens a Zope trace log. 
# http://www.splunk.com/doc/3.3.4/developer/searchscripts
# http://blogs.splunk.com/david/2008/08/29/write-your-own-search-language/

import sys,splunk.Intersplunk,sets,os,re

results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

output = []
queue = {}

for result in results:
    result['metric'] = result.get('metric', 'n/a')
    
    request_id = result['req_id']
    
    if result['entrytype'] == 'B':
        httpmethod, uri = result['metric'].split(' ')
        result['method'] = httpmethod
        result['uri'] = uri
        
        endl = queue.get(request_id, None)
        
        if endl:                    
            result['req_time'] = int(endl['_time']) - int(result['_time']) 
            del queue[request_id]
        else:
            result['req_time'] = 'n/a'

        output.append(result)
    
    # the "end" (E) logline is returned from Splunk before the the "begin" (B)    
    elif result['entrytype'] == 'E':
        queue[request_id] = result


splunk.Intersplunk.outputResults(output)
