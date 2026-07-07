import sys, string, csv, re, logging
import splunk.Intersplunk as si

logger = logging.getLogger() # Root-level logger
logger.setLevel(logging.WARN)

logfile = logging.StreamHandler(open("/opt/splunk/var/log/splunk/clusterstats.log", "a"))
logfile.setLevel(logging.WARN)
logfile.setFormatter(logging.Formatter('%(asctime)s [%(process)06d] %(levelname)-8s %(name)s:  %(message)s'))
logger.addHandler(logfile)

def usage():
    logger.warn("outputting usage info")
    results = si.generateErrorResults(" maxspansecs=X argument required")
    si.outputResults(results)

def calcstats(spanint, results):
    cltxncount = 0
    clstarttime = None
    cllasttime = None
    cltotaltime = None
    clendtime = None
    clmaxdur = None
    clmeandur = None
    clsumdur = None
    # basically for every result, if the current time is 
    # < lastTime - spanint then include it in the cluster
    # otherwise close the current cluster and start a new one 
    myresults = []
    for result in results:
	logger.debug("processing result: " + repr(result))
        if '_time' not in result:
            si.generateErrorResults("Missing required _time field in data")    
	logger.debug("testing for new cluster with txn count of:" + str(cltxncount) + " and clstarttime, cllasttime, spanint are " + str(clstarttime) + ", " + str(cllasttime) + ", " + str(spanint))
        if clstarttime == None or float(result['_time']) > cllasttime + spanint:
            # about to initialize a new cluster
            # if this is not the first cluster, store the stats
            # from the last cluster
	    logger.debug("in new cluster block with a cluster txn count of:" + str(cltxncount) + " and clstarttime, cllasttime, spanint are " + str(clstarttime) + ", " + str(cllasttime) + ", " + str(spanint))
            if clstarttime != None:
		logger.debug("building row")
                row = {}
                row['_time'] = clstarttime
                row['cluster_last_txn_start'] = cllasttime
                row['cluster_txn_count'] = cltxncount
                row['cluster_end_time'] = clendtime
                row['cluster_max_duration'] = clmaxdur
                row['cluster_mean_duration'] = clsumdur/cltxncount 
                myresults.append(row)
	    else:
		logger.debug("clstarttime was None - no row was appended - txn count was: " +  str(cltxncount))
            # init the new cluster values    
            clstarttime = float(result['_time'])
            cltxncount = 0
            clsumdur = 0
            clmaxdur = float(result['duration'])
            clendtime = clstarttime + clmaxdur
        # every result increments txncount and sets last time and adds to sumdur
	cltxncount += 1
	logger.debug("in outer loop: " + str(cltxncount))
        clsumdur += float(result['duration'])    
        cllasttime = float(result['_time'])
        if float(result['duration']) > clmaxdur:
            clmaxdur = float(result['duration'])
        if clendtime < float(result['_time']) + float(result['duration']):
            clendtime = float(result['_time']) + float(result['duration'])
    # take care of the last cluster
    if clstarttime != None:
	logger.debug("building last row: " + str(cltxncount))
        row = {}
        row['_time'] = clstarttime
        row['cluster_last_txn_start'] = cllasttime
        row['cluster_txn_count'] = cltxncount
        row['cluster_end_time'] = clendtime
        row['cluster_max_duration'] = clmaxdur
        row['cluster_mean_duration'] = clsumdur/cltxncount
        myresults.append(row)
 	logger.debug("results: " + repr(myresults))
    si.outputResults(myresults)
        

            
def main():
    (isgetinfo, sys.argv) = si.isGetInfo(sys.argv)
    if isgetinfo:
        si.outputInfo(False, False, False, False, None, True)
        # outputInfo automatically calls sys.exit()    
    logger.debug("starting clusterstats")
    argc = len(sys.argv)	
    if argc != 2: 
        usage()
    match = re.search("(?i)maxspansecs=(\d+)", sys.argv[1])
    if match == None: 
        usage()	
    input_secs = match.group(1)
    span_secs = input_secs = int(input_secs)
    results, dummyresults, settings = si.getOrganizedResults()
    logger.debug("Settings passsed in to clusterstats: %r", settings)

    logger.info("clusterstats processing %d results", len(results))
            
    calcstats(span_secs, results)

try:
    main()
except Exception, e:
    # Catch any exception, and also return a simplified version back to splunk (should be displayed in red at the top of the page)
    logger.warn("Exception" + str(e))
    results = si.generateErrorResults("Error in 'clusterstats'': " + str(e))
    si.outputResults(results)
