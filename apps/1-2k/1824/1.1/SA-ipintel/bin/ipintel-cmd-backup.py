#!/usr/bin/env python

import splunk.Intersplunk
import sys
import time

def debug(what):
    sys.stderr.write("{}\n".format(what))

try:
    import os
    #execfile(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "bin", "PythonLibs.py")))

    from ipintel import is_ip_addr,make_splunk_event

    from ipintel.blacklist import get_data as get_blacklist_data
    from ipintel.cins import get_data as get_cins_data
    from ipintel.iprep import get_data as get_iprep_data
    from ipintel.maxmind import get_data as get_location_data
    from ipintel.safebrowsing import get_data as get_safebrowsing_data
    from ipintel.shodan import get_data as get_shodan_data
    from ipintel.virustotal import get_data as get_virustotal_data
    from ipintel.whois import get_data as get_whois_data

    ip = sys.argv[1]

    events = list()
    events.append( (get_location_data(ip), "location") )

    for bl in get_blacklist_data(ip):
        if bl["listed"]:
            events.append( (bl, "blacklist") )

    for banner in get_shodan_data(ip):
        events.append( (banner, "shodan") )

    events.append( (get_whois_data(ip), "whois") )

    for (k,v) in get_virustotal_data(ip).items():
        for e in v:
            events.append( (e, "virustotal_{}".format(k)) )

    events.append( (get_iprep_data(ip), "iprep") )
    events.append( (get_cins_data(ip), "cins") )

    events.append( (get_safebrowsing_data(ip), "safebrowsing") )

    events = [ e for e in events if e[0] is not None ]
    events = [ make_splunk_event(data, sourcetype) for (data,sourcetype) in events ]
except:
    import traceback
    events = splunk.Intersplunk.generateErrorResults("Traceback: {}".format(traceback.format_exc()))
splunk.Intersplunk.outputResults(events)
