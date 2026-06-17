# Copyright (C) 2005-2010 Splunk Inc.  All Rights Reserved.  Version 4.0
import splunk.Intersplunk as si

import time
from tuneup import fields, tags
from splunk.mining import dcutils
import splunk.auth as sa

logger = dcutils.getLogger()


g_discover_types = set(["fields", "tags"])

def usage():
    si.generateErrorResults("Usage: discover [ %s ]" % (" | ".join(g_discover_types)))
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
            discovertype = keywords[0].lower().strip()
            if discovertype not in g_discover_types:
                usage()
            if discovertype == "fields":
                max_trainers = int(args.get('max', '25'))
                showsummary = isTrue(args.get('summary', 'true'))
                fields.suggestFields(results, messages, max_trainers, showsummary)
            elif discovertype == "tags":
                typetags = tags.suggestTags(owner, sessionKey, namespace)
                results = []
                for tagtype,tags in typetags.items():
                    for tag, vals in tags.items():
                        result = {
                            'type': tagtype,
                            'tag':  tag,
                            '_raw': '%s::%s values: %s ...' % (tagtype, tag, ', '.join(list(vals)[:5])),
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
