import sys,splunk.Intersplunk
import time

results = []
actual = set()
newresults = {}


try:
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    
    for result in results:
        for key in result:
            if (result[key]) :
                actual.add(key)

except Exception as e:
    newresults = splunk.Intersplunk.generateErrorResults("Error occurred while running custom command: '%s'" % str(e))

newresults['uniqueFieldList'] = list(actual)
newresults['_time'] = time.time()

splunk.Intersplunk.outputResults([ newresults ])
