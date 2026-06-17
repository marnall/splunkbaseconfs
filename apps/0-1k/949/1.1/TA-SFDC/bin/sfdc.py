#!/usr/bin/env python

import csv
import logging
import logging.handlers
import os
import sys
import time
import calendar
import splunk.clilib.cli_common

from sforce.enterprise import SforceEnterpriseClient
from xml.etree.ElementTree import ElementTree

class ResultsParser(object):
    def __init__(self):
        self.messages = []
        self.timeseed = None

    def parse(self,results):
        if results.size == 0:
            return None
        for record in results.records:
            message = []
            ts = None
            description = None
            for r in record:
                if r[0].startswith(settings["timestamp"]):
                    ts = str(r[1])
                    message.insert(0,ts)
                    seed = soql_format('g2etime', str(r[1]), '%Y-%m-%d %H:%M:%S')

                    if not self.timeseed:
                        self.timeseed = seed
                    else:
                        if self.timeseed < seed:
                            self.timeseed = seed
		elif r[0].startswith("Id"):
		    message.append('='.join([unicode(r[0]), unicode(r[1])]))
                else:
		    edits = [('\n', ' '), ('\r', ' '), ('=', '--'), ('"', '\'')]

		    val = unicode(r[1])

		    for search, replace in edits:
			val = val.replace(search, replace)

		    if val.find(' ') > -1:
			val = '"' + val + '"'
			
                    message.append('='.join([unicode(r[0]), val]))

            self.messages.append(" ".join(message))

	self.timeseed += 1

        return self.timeseed

def soql_format(type=None,value=None,format=None):
    '''convenience method to convert to/from SOQL formats'''
    if not type or not value:
        raise
    try:
        if type.startswith('e2gtime'):
            t = time.gmtime(float(value))
            u = []
            u.append(str(t[0]))
            for x in range(1,6):
                if t[x]>=0 and t[x]<10:
                    u.append('0' + str(t[x]))
                else:
                    u.append(str(t[x]))
            return u[0] + '-' + u[1] + '-' + u[2] + 'T' + u[3] + ':' + u[4] + ':' + u[5] + '-08:00'
        elif type.startswith('g2etime'):
            if not format:
                format = '%Y-%m-%dT%H:%M:%S'
            return calendar.timegm(time.strptime(value,format))
        else:
            raise NotImplementedError
    except:
        raise

if __name__ == '__main__':
    settings = splunk.clilib.cli_common.getConfStanza(os.path.join(sys.path[0], "..", "local", "sfdc"), "sfdc")
    lastTime = {}
    seedFile = os.path.join(sys.path[0], '.sfdc2df.seed')

    if not os.path.exists(settings["log_path"]):
	os.makedirs(settings["log_path"])

    flogger = logging.getLogger('splunkx_sfdc')
    flogger.setLevel(logging.DEBUG)
    handler = logging.handlers.RotatingFileHandler("/".join([settings["log_path"], 'splunkx_sfdc']), maxBytes=52428800, backupCount=5)
    g = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    handler.setFormatter(g)
    handler.setLevel(logging.INFO)
    flogger.addHandler(handler)

    i = 0
    j = 0
    k = 0

    stables = []
    goodtypes = []
    query = []
    tables = []

    while True:
	try:
	    objkey = "sfdc_object." + str(i)
	    stables.append(settings[objkey])
	except:
	    break

	i += 1

    while True:
	try:
	    typkey = "sfdc_types." + str(j)
	    goodtypes.append(settings[typkey])
	except:
	    break

	j += 1

    try:
	sf = csv.reader(open(seedFile,'rb'))

	for row in sf:
		lastTime[row[0]] = row[1]

    except IOError:
	for row in stables:
		lastTime[row] = 864000

	flogger.info("Error opening seedfile.  Might be first time run.")

    xml = open(os.path.join(sys.path[0], "..", "local", settings["wsdl"]),"r")
    tree = ElementTree()

    try:
	tree.parse(xml)
    except:
	raise

    xml.close()
    t = tree.getroot()

    types = tree.find("{http://schemas.xmlsoap.org/wsdl/}types")

    for s in types:
	if s.get("targetNamespace") == "urn:sobject.enterprise.soap.sforce.com":
	    elements = s.findall("{http://www.w3.org/2001/XMLSchema}complexType")

	    for o in elements:
		if o.get("name") in stables:
		    sequence = o.find("{http://www.w3.org/2001/XMLSchema}complexContent/{http://www.w3.org/2001/XMLSchema}extension/{http://www.w3.org/2001/XMLSchema}sequence")
		    fields = sequence.findall("{http://www.w3.org/2001/XMLSchema}element")

		    tmpcol = ["Id"]
		    collist = ""

		    for f in fields:
			if f.get("type") in goodtypes:
			    tmpcol.append(f.get("name"))

		    collist = ", ".join(tmpcol)

		    if not o.get("name") in lastTime:
			lastTime[o.get("name")] = 864000

		    qry = "SELECT " + collist + " FROM " + o.get("name") + " WHERE " + settings["timestamp"] + " >= " + soql_format('e2gtime', lastTime[o.get("name")] ) + " ORDER BY " + settings["timestamp"]

                    query.insert(k, qry)
		    tables.insert(k, o.get("name") )

		    k += 1

    flogger.info("Instantiating connection to SFDC API")

    h = SforceEnterpriseClient(os.path.join(sys.path[0], '..', 'local', settings["wsdl"] ))
    h.login(settings["username"], settings["password"], settings["token"])

    flogger.info("Instantiating per-object log files")

    f = {}

    for q in tables:
        f[q] = logging.getLogger(q)
        f[q].setLevel(logging.DEBUG)
        handler = logging.handlers.RotatingFileHandler("/".join([settings["log_path"], q]), maxBytes=52428800, backupCount=20)
        g = logging.Formatter("%(message)s")
        handler.setFormatter(g)
        handler.setLevel(logging.INFO)
        f[q].addHandler(handler)

    try:
        for id, q in enumerate(tables):
            m_size = 0
            results = ResultsParser()
            flogger.info("Submitting query for object %s at time %s",
                          q, soql_format('e2gtime', lastTime[q] ) )
            flogger.debug("Query: %s", query[id])
            qr = h.queryAll(query[id])
            tsd = results.parse(qr)
            if not tsd:
                flogger.info("Received no results from query for object %s", q)
            else:
                for m in results.messages:
                    f[q].info(m)
                    m_size = m_size + len(m)

                flogger.info("Processed %s results from SFDC for object %s, size %d bytes", q, qr.size, m_size)

		lastTime[q] = tsd
    except:
        raise

    sf = csv.writer(open(seedFile,'wb'))

    for k,v in lastTime.iteritems():
	sf.writerow([k,v])

