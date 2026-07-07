#!/usr/bin/env python

import csv
import sys
import os
import urllib2
import time
import json
from splunk.clilib import cli_common as cli

#setup logging
current_script_dir = os.path.dirname(os.path.realpath(__file__))
current_app_dir = os.path.dirname(current_script_dir)

def getSelfConfStanza(stanza):
    current_script_dir = os.path.dirname(os.path.realpath(__file__))
    appdir = os.path.dirname(current_script_dir)
    apikeyconfpath = os.path.join(appdir, "default", "ziften.conf")
    apikeyconf = cli.readConfFile(apikeyconfpath)
    localconfpath = os.path.join(appdir, "local", "ziften.conf")
    if os.path.exists(localconfpath):
        localconf = cli.readConfFile(localconfpath)
        for name, content in localconf.items():
            if name in apikeyconf:
                apikeyconf[name].update(content)
            else:
                apikeyconf[name] = content
    return apikeyconf[stanza]

stanza = getSelfConfStanza("setupentity")
vtkey = stanza['vtkey']
if not vtkey:
    sys.exit(1)

def lookup(md5):
    try:
        log_msg = "message=%s, md5=%s" % ("sending_md5", md5)
        then = time.time()
        baseurl = "https://www.virustotal.com/vtapi/v2/file/report"
        query = "apikey=%s&resource=%s" % (vtkey, md5)
        response = urllib2.urlopen(baseurl, query)
        delta = time.time() - then
        log_msg = "message=%s, md5=%s, seconds=%f" % ("lookup_time", md5, delta)
        data = response.read()
        result = json.loads(data)
    except Exception, ex:
        log_msg = 'message=%s, error="%s"' % ("post_error", str(ex))
        result = {}
    return result

def main():
    if len(sys.argv) != 7:
        print len(sys.argv)
        print "python vt.py md5 vt_details vt_score vt_hits vt_sources lookup_time"
        sys.exit(1)

    md5_field = sys.argv[1]
    vt_details = sys.argv[2]
    vt_score = sys.argv[3]
    vt_hits = sys.argv[4]
    vt_sources = sys.argv[5]
    lookup_time = sys.argv[6]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    history_file = os.path.join(current_app_dir, "lookups", "vthistory.csv")
    hist_exists = os.path.exists(history_file)

    if hist_exists:
        log_msg = 'message=%s' % ("append_history_file")
        history_file_handler = open(history_file, 'a')
        history_csv = csv.DictWriter(history_file_handler, fieldnames=r.fieldnames)
    else:
        log_msg = 'message=%s' % ("new_history_file")
        history_file_handler = open(history_file, 'w')
        history_csv = csv.DictWriter(history_file_handler, fieldnames=r.fieldnames)
        history_csv.writeheader()

    for line in r:
        if line[md5_field]:
            result = lookup(line[md5_field])
            if not result:
                sleep_time=61
                log_msg = 'message=%s, sleep_time=%i' % ("quota_hit", sleep_time)
                time.sleep(sleep_time)
                result = lookup(line[md5_field])
            line[vt_hits] = result.get("positives", 0)
            line[vt_sources] = result.get("total", 0)
            line[vt_score] = "%s/%s" % (line[vt_hits], line[vt_sources])
            scans = result.get("scans", {})
            scan_details = []
            for k, v in scans.iteritems():
                detected = v.get("detected", None)
                if detected:
                    scan_details.append("[%s] %s" % (k, v.get("result", "")))
            line[vt_details] = ','.join(scan_details)
            line[lookup_time] = time.time()
            w.writerow(line)
            history_csv.writerow(line)
try:
    main()
except Exception, ex:
    log_msg = 'message=%s, error="%s"' % ("unknown_error", str(ex))
