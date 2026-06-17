#import os,csv,sys,splunk.Intersplunk as si,splunk.mining.dcutils as dcu
import os,csv,sys,splunk.Intersplunk,splunk.mining.dcutils

logger = splunk.mining.dcutils.getLogger()

try:
    keywords,options = splunk.Intersplunk.getKeywordsAndOptions()
    csv_path = options.get('csv')
    field = options.get('field')

    if csv_path is None:
        raise Exception("csv required (path from $SPLUNK_HOME)")
    if field is None:
        raise Exception("field required (field from csv to test against _raw. This is also the field added to events.)")

    f = os.path.normpath( os.sep.join( [os.getenv("SPLUNK_HOME") , csv_path ] ) )

    values = []
    reader = csv.DictReader( open(f, 'rt') )
    for r in reader:
        values.append(r[field])

    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    # for first N result used as training
    for result in results:
        for v in values:
            if result['_raw'].lower().find(v.lower()) > -1:
                if field in result:
                    if type(result[field]) is str:
                        a = []
                        a.append(result[field])
                        result[field] = a
                    result[field].append(v)
                else:
                    result[field] = v

    splunk.Intersplunk.outputResults(results)
except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    splunk.Intersplunk.generateErrorResults("Error '%s'" % e)
    logger.error("%s" % e)
    logger.info("Traceback: %s" % stack)

