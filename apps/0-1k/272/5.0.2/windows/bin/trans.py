'''
Copyright (C) 2005-2011 Splunk Inc. All Rights Reserved.
'''
import re,sys
import splunk.Intersplunk as inter
import logging as logger

log_f = None
# log_f = open("c:\\logs\\trans.log", "w+")

def log(msg):
    if log_f != None:
        log_f.write("%s\n" % msg)

def getArgValues():
    argvals = dict()
    if len(sys.argv) >= 1:
        args = sys.argv[1:]
    for arg in args:
        pieces = arg.split( "=", 1 )
        if len(pieces) > 1:
            argvals[pieces[0].lower()] = pieces[1]
    return argvals

results = []
try:
    results,dummyresults,settings = inter.getOrganizedResults()
    argvals = getArgValues()

    to_arg = argvals.get("to", "guid_to_trans")
    with_arg = argvals.get("with", "guid_dcname")

    log("to=(%s); with=(%s)\n" % (to_arg, with_arg))

    for result in results:
        
        raw = result.get("_raw","")
        
        to_key = result.get(to_arg,"NONE")
        with_val = result.get(with_arg,"NONE")

        if isinstance(to_key, list):

            to_with_map = map(None, to_key, with_val)
            for to_with in to_with_map:
                if to_with[0] != "NONE":
                    log("guid=%s - (%s)" % (to_with[0], to_with[1]))
                    if to_with[1] != "NONE":
                        raw = raw.replace("{"+to_with[0]+"}", "{%s} (%s) " % (to_with[0], to_with[1]))
        else:
            if to_key != "NONE":
                log("guid_not_list=%s - (%s)" % (to_key, with_val))
                if with_val != "NONE":
                    raw = raw.replace("{"+to_key+"}", "{%s} (%s) " % (to_key, with_val))

        result["_raw"] = raw
        
except Exception, e:
    import traceback
    stack =  traceback.format_exc()
    log(str(e) + ". Traceback: " + str(stack))
    results = splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack))

inter.outputResults(results)

if log_f != None:
    log_f.close()

