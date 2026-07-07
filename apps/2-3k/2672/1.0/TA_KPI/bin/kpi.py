#   Version 4.0
import sys, os, platform, re, inspect
import xml.dom.minidom, xml.sax.saxutils
import logging
import urllib2, urllib
import json
import sched, time
import csv
from multiprocessing import Process

import splunk.Intersplunk
import splunk.entity as entity
import logging  as logger
import ast

outputFileName = 'kpi.py-log.txt'
outputFileLog = os.path.join(os.environ['SPLUNK_HOME'],'var','log','splunk',outputFileName)
logger.basicConfig(format='%(asctime)s %(levelname)s %(message)s', filename=outputFileLog, filemode='a+', level=logger.DEBUG, datefmt='%Y-%m-%d %H:%M:%S %z')
logger.Formatter.converter = time.gmtime
##  ARGS op 
##

def compareGT(aVal, eVal):
	logger.debug("Actual Value: %s, kpiValue: %s, GT: %s"%(aVal,eVal, (float(aVal) > float(eVal))))
	return float(aVal) > float(eVal)

def compareLT(aVal, eVal):
	logger.debug("Actual Value: %s, kpiValue: %s, LT: %s"%(aVal,eVal, (float(aVal) < float(eVal))))
	return float(aVal) < float(eVal)

def compareEQ(aVal, eVal):
	logger.debug("Actual Value: %s, kpiValue: %s, EQ: %s"%(aVal,eVal, (float(aVal) == float(eVal))))
	return float(aVal) == float(eVal)

CompareFunc = {
	"gt": compareGT,
	"lt": compareLT,
	"eq": compareEQ
}

def isNumber(s):
	try:
		float(s)
		return True
	except ValueError:
		return False

def handleStaticKPI(KPI, rVal):
	kpiVal = KPI["kpi_value"]
	resVal = rVal
	kpiStat = KPI["kpi_ok"]
        fn = KPI["kpi_field"]
	if not (isNumber(kpiVal) and isNumber(resVal)):
		return [{"field":"%s_kpi_error"%fn, "value": "cannot compare"} ]
	kpiVal = float(kpiVal)
	resVal = float(resVal)
	if "diff" == KPI["kpi_ok"]:
		kpiStat = resVal - kpiVal
	if CompareFunc[KPI["kpi_compare"]](resVal,kpiVal):
		kpiStat = KPI["kpi_violated"]
		if "diff" == kpiStat:
			kpiStat = resVal - kpiVal
	return [
		{"field":"%s_kpi_description"%fn, "value": KPI["kpi_description"] },
		{"field":"%s_kpi_compare"%fn,"value":KPI["kpi_compare"]},
		{"field":"%s_kpi_status"%fn,"value":kpiStat}
		]


KPIFunc = {
	"static" : handleStaticKPI,
}

def kpi(results, settings):
	resultcount = len(results)
	myKPIs = ast.literal_eval(getKPIs(settings))
	logger.debug("Got KPIS from REST API: %s"%myKPIs)
	for n in myKPIs:
		logger.debug("Found KPI: %s"%n)
	myAKPIs = [ n["eventtype"] for n in myKPIs ]
	logger.info("Set available KPIs: %s"%myAKPIs)
	op = settings["dynamic"]
        for res in results:
		logger.debug("Checking if eventtype field is present in a new event")
		if "eventtype" in res:
			logger.debug("It is : %s"%res["eventtype"])
			myET = res["eventtype"].split(" ")
			logger.debug("Checking the result's eventtypes (%s) against the list of KPIs"%myET)
			if [i for i in myET if i in myAKPIs]:
				nresults = [t for t in myKPIs if t["eventtype"] in myET]
				logger.debug("Found Available KPIs for this event: %s"%nresults)
				for n in nresults:
					logger.debug("checking if the field %s is in the event"%n["kpi_field"])
					if n["kpi_field"] in res:
						logger.debug("it is")
						res["%s_kpi_expected"%n["kpi_field"]] = n["kpi_value"]
						res["%s_kpi_actual"%n["kpi_field"]] = res[n["kpi_field"]]
						res["%s_kpi_eventtype"%n["kpi_field"]] = res["eventtype"]
						for m in KPIFunc[n["kpi_type"]](n, res[n["kpi_field"]]):
							res[m["field"]] = m["value"]
			res["aKPIs2"] = "%s"%myET
	return results

results = []
(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)

def getKPIs(settings):
        myEnt = entity.getEntity('/storage/collections/data','col_kpi', namespace='TA_KPI',sessionKey=settings['sessionKey'], owner='nobody')
        return "%s"%myEnt

if __name__ == '__main__':    
	try:
	    # poor mans opt
	    # DEFAULTS
	    settings = dict()
	    settings["dynamic"] = False
	    for a in sys.argv[1:]:
	
	        # This (old) feature just put a 'help' header for people who don't know
	        # how to read diff
	        # Commenting out for now since the header has been put into the decorations stuff.
	        if a.startswith("dynamic="):
	            where = a.find('=')
	            settings["dynamic"] = a[where+1:len(a)]
	        elif isgetinfo:
	            splunk.Intersplunk.parseError("Invalid argument '%s'" % a)
	
	    if isgetinfo:
	        splunk.Intersplunk.outputInfo(False, False, True, False, None, False)
	
	    results = splunk.Intersplunk.readResults(settings=settings, has_header=True)
	    results = kpi(results, settings)
	
	except Exception, e:
	    import traceback
	    stack =  traceback.format_exc()
	    if isgetinfo:
	        splunk.Intersplunk.parseError(str(e))
	        
	    results = splunk.Intersplunk.generateErrorResults(str(e))
	    logger.warn("invalid arguments passed to 'kpi' search operator. Traceback: %s" % stack)
	
	splunk.Intersplunk.outputResults(results)
