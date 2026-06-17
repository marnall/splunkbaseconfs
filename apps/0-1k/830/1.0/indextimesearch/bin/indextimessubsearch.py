import sys, os, time, traceback, re
import splunk.mining.dcutils as dcu
import splunk.Intersplunk as isp
import splunk.search
import logging

EARLIEST_INDEXTIME = 'earliest_indextime'
LATEST_INDEXTIME = 'latest_indextime'
INDEXTIME_FIELDNAME = '_indextime'

logger = dcu.getLogger()

#--------------------------------------------------------------
#take the range of indextime prefixes and flatten them down to a manageable number
def flatten_results( input , max ):
    result = set(input)
    while len(result) > max:
        newset = set()
        for r in result:
            newset.add(str(r)[0:-1])
        result = newset

    starred = set()
    for r in result:
        starred.add( str(r) + "*" )
        #make it a string just in case the length of result is never actually > max

    starred = list(starred)
    starred.sort()

    return starred

#get the set of times to actually search against. 
#Since indextime is actually just stored as a string, 
#the best we can do it search against patterns, which is still better than scanning everything.
def build_times( earliest, latest ):
    earliest = int(round(int(earliest),-1))
    latest = int(round(int(latest),-1))

    flattened = flatten_results( range(earliest,latest,10) , 25 )

    output = []

    for r in flattened:
        output.append(str(r))
        logger.debug("Appending " + str(r))

    return output

#build the actual search, using the flattened patterns from above
def build_subsearch(times):
    output = []
    for t in times:
        output.append( ( "%s=%s " % (INDEXTIME_FIELDNAME,t) ) )
    return " OR ".join(output)

#extract bits of xml from the authToken that comes in on STDIN
def getfield(authString,f):
    if( authString.find('<'+f+'>') > 0 ):
        start = authString.find('<'+f+'>') + len(f) + 2
        stop = authString.find('</'+f+'>')
        return authString[start:stop]

#query Splunk itself to retrieve the appropriate epoch strings.
def build_epochs_from_relative_times(token,earliest,latest):
    logger.debug("build_epochs_from_relative_times.")
    #the coalesce is here to handle "now" in the latest time slot. It's inadvisable to use that anyway, but you know people would.
    s = '|stats count | eval %s=round(relative_time(now(),"%s")) | eval %s=round( coalesce( relative_time(now(),"%s") ,  relative_time(now(),"-0s") ) ) | fields - count' % (EARLIEST_INDEXTIME,earliest,LATEST_INDEXTIME,latest)

    logger.debug(s)

    r = splunk.search.searchOne(s, sessionKey=token)
    logger.debug(r)
    logger.debug("Finished search")

    return r


#
# main
#

def main():
    try:        
        authString = sys.stdin.readline()
        #<auth><userId>admin</userId><username>admin</username><authToken>cbd900f3b28014a1e233679d05dcd805</authToken></auth>

    #    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
        keywords, argvals = isp.getKeywordsAndOptions()

        # run generator
        earliest = argvals.get(EARLIEST_INDEXTIME, None)
        if earliest is None:
            raise Exception("Must supply relative start time in "+EARLIEST_INDEXTIME+". Optionally provide "+LATEST_INDEXTIME+". For example: "+EARLIEST_INDEXTIME+"=-2h@h "+LATEST_INDEXTIME+"=-1h@h")

        latest = argvals.get(LATEST_INDEXTIME, '-0h')

        token = getfield(authString,'authToken')
        if token is None:
            raise Exception("authToken was not extracted. This means misconfiguration of some sort.")
        r = build_epochs_from_relative_times(token,earliest,latest)
        times = build_times( str( r[EARLIEST_INDEXTIME] ), str( r[LATEST_INDEXTIME] ) )
        subsearch = build_subsearch( times )

        results = []
        row = {}
        row['search'] = subsearch
        results.append(row)

        #results = build_epochs_from_relative_times(token,earliest,latest)

    except Exception, e:
        logger.exception(e)
        results = isp.generateErrorResults(str(e))

    # dump out to Intersplunk
    isp.outputResults(results)

if __name__ == '__main__':
    main()



