#a command to split an event into multiple events
#this is useful when something has gone terribly wrong and you end up with 
#lots of events combined together into one event and you can't 
#dump everything and reindex
#
#the big caveat is that all fields that were parsed with the first message 
#end up attached to all messages, including the date
#
#let me know if you find this useful or need someone to scream at - vincent.bumgarner [at] riskmetrics.com
#

import re,sys
import splunk.Intersplunk as si

RAW = '_raw'
START_REQUIRED_MESSAGE = "start required. start should be a regex that matches the beginning of what you would like to see as a new event, such as start=\"^\d+-\d+-\d+\s\""

def buildnewresult(result,splititem):
    newres = result.copy()
    newres[RAW] = splititem
    newres['foo'] = 'bar'
    return newres

def findmatching( compiledpattern , str ):
    result = []

    pos = 0
    previous_pos = 0
    previous_end = 0

    #just in case the user does something stupid, like search for ^
    safetyvalve = 10000 
    #someone with more python chops can probably make this more efficient
    while ( compiledpattern.search(str, previous_end) and safetyvalve>0 ):
        m = compiledpattern.search(str, previous_end)
        pos = m.start()
        previous_end = m.end()
        if pos > 0:
            result.append( str[previous_pos:pos] )
        previous_pos = pos
        safetyvalve -= 1
    result.append( str[previous_pos:len(str)] )

    return result


if __name__ == '__main__':
    try:
        keywords,options = si.getKeywordsAndOptions()

        #get the pattern.  explode if it's not there.
        start = options.get('start', None)
        if start == None:
            si.generateErrorResults(START_REQUIRED_MESSAGE)
            exit(0)

        compiledpattern = re.compile(start, re.M | re.I)

        results,dummyresults,settings = si.getOrganizedResults()

        newresults = []
        for result in results:
            for m in findmatching( compiledpattern , result[RAW] ):
                newresults.append(buildnewresult(result,m))
        si.outputResults(newresults)
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'. %s" % (e, stack))

