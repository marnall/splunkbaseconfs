# Copyright (C) 2005-2010 Splunk Inc.  All Rights Reserved.  Version 4.0
import splunk.Intersplunk as si

import time
from tuneup import eventtypes, macros, rexextractions, savedsearches
from splunk.mining import dcutils
import splunk.auth as sa

logger = dcutils.getLogger()

g_tune_types = set(["eventtypes", "macros", "rexes", "savedsearches"])

def usage():
    si.generateErrorResults("Usage: tune [ %s ]" % (" | ".join(g_tune_types)))
    exit(0)

def isTrue(s):
    s = s.lower().strip()
    if s == '': return False
    return s[0] in 't1y'

if __name__ == '__main__':
    try:

        results,dummyresults,settings = si.getOrganizedResults()

        # default values
        args = { 'namespace':'search'}
        # get commandline args
        keywords, options = si.getKeywordsAndOptions()
        # override default args with settings from search kernel 
        args.update(settings)
        # override default args with commandline args
        args.update(options)
        
        sessionKey = args.get("sessionKey", None)
        owner      = args.get("owner", 'admin')
        namespace  = args.get("namespace", None)
        if namespace.lower() == "none":
            namespace = None

        messages = {}

        if sessionKey == None:
            # this shouldn't happen, but it's useful for testing.
            try:
                sessionKey = sa.getSessionKey('admin', 'changeme')
                si.addWarnMessage(messages,  "No session given to 'tune' command. Using default admin account and password.")
            except splunk.AuthenticationFailed, e:
                si.addErrorMessage(messages, "No session given to 'tune' command.")
                exit(0)
        
        if len(keywords) > 0:
            tunetype = keywords[0].lower().strip()
            if tunetype not in g_tune_types:
                usage()
            if tunetype == "eventtypes":
                vals = eventtypes.suggestEventtypes(owner, sessionKey, namespace, 2)
                results = []
                for search in vals:
                    eventtype = {
                        'eventtype':'discovered_eventtype',
                        'search': search,
                        '_raw':  search,
                        '_time': int(time.time())
                        }
                    results.append(eventtype)
            elif tunetype == "macros":
                vals = macros.suggestMacros(owner, sessionKey, namespace, 1000, 2)
                results = []
                for snippet,count in vals:
                    macro = {
                        'macro': snippet,
                        '_raw':  snippet,
                        '_time': int(time.time()),
                        'count': count
                        }
                    results.append(macro)
            elif tunetype == "rexes":
                rexes = rexextractions.suggestExtractions(owner, sessionKey, namespace, 2)
                results = []
                for rex in rexes:
                    result = {
                        'rex': rex,
                        '_raw':  rex,
                        '_time': int(time.time()),
                        }
                    results.append(result)
            elif tunetype == "savedsearches":
                searches = savedsearches.suggestSavedSearches(owner, sessionKey, namespace, 2)
                results = []
                for search in searches:
                    result = {
                        'search': search,
                        '_raw':  search,
                        '_time': int(time.time()),
                        }
                    results.append(result)

        else:
            usage()

        si.outputResults(results, messages)
    except Exception, e:
        import traceback
        stack =  traceback.format_exc()
        si.generateErrorResults("Error '%s'" % e)
        logger.error("%s" % e)
        logger.info("Traceback: %s" % stack)
