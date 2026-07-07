###############################################################################
###############################################################################
##
##  Propinator - Opinionated Splunk parsing configurations for events
##
##  Discovered Intelligence
##  https://discoveredintelligence.ca
##
##  For support contact:
##  support@discoveredintelligence.ca
##
###############################################################################
###############################################################################

import sys
import re
import os
import time
import splunk
import splunk.Intersplunk
import splunk.search
import logging, logging.handlers

######################################################
######################################################
# Helper functions
#

def unquote(val):
    if val is not None and len(val) > 1 and val.startswith('"') and val.endswith('"'):
        return val[1:-1]
    return val

def toBool(strVal):
   if strVal == None:
       return False

   lStrVal = strVal.lower()
   if lStrVal == "true" or lStrVal == "t" or lStrVal == "1" or lStrVal == "yes" or lStrVal == "y" :
       return True
   return False

def getarg(argvals, name, defaultVal=None):
    return unquote(argvals.get(name, defaultVal))

def most_frequent(List):
    counter = 0
    num = List[0]

    for i in List:
        curr_frequency = List.count(i)
        if(curr_frequency> counter):
            counter = curr_frequency
            num = i

    return num

def setup_logging():
    logger = logging.getLogger('splunk.propinator')

    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "propinator.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    LOG_FILE_PATH = os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME)
    splunk_log_handler = logging.handlers.RotatingFileHandler(LOG_FILE_PATH, mode='a',maxBytes=20971520, backupCount=4)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)

    return logger

def calculate_regex(sample_text):
    regex_output=''

    for ch in sample_text:
        logger.debug("For char %s in prefix string" % ch)
        if ch.isdigit():
            if regex_output:
                if r'\d+' in regex_output:
                    if regex_output[-3:]==r'\d+':
                        pass
                    else:
                        regex_output = regex_output + r'\d+'
                else:
                    regex_output = regex_output + r'\d+'
            else:
                regex_output = r'\d+'

        elif ch.isalpha():
            if regex_output:
                if regex_output[-2:]== r'\w':
                    regex_output = regex_output + '+'
                elif not regex_output[-3:]==r'\w+':
                    regex_output = regex_output + r'\w'
            else:
                regex_output = r'\w'
        elif ch == " ":
            if regex_output:
                if regex_output[-2:]== r'\s':
                    regex_output = regex_output + '+'
                elif not regex_output[-3:]==r'\s+':
                    regex_output = regex_output + r'\s'
            else:
                regex_output = r'\s'
        elif ch == "$":
            regex_output+=r'\$'
        elif ch == "^":
            regex_output+=r'\^'
        elif ch == "*":
            regex_output+=r'\*'
        elif ch == "(":
            regex_output+=r'\('
        elif ch == ")":
            regex_output+=r'\)'
        elif ch == "+":
            regex_output+=r'\+'
        elif ch == "[":
            regex_output+=r'\['
        elif ch == "\\":
            regex_output+=r'\\'
        elif ch == "|":
            regex_output+=r'\|'
        elif ch == ".":
            regex_output+=r'\.'
        elif ch == "/":
            regex_output+=r'\/'
        elif ch == "?":
            regex_output+=r'\?'
        else:
            regex_output+=ch
        logger.debug("Calculated regex so far is %s" % regex_output)
    return regex_output

######################################################
######################################################
#
# Main
#
logger = setup_logging()

logger.info('py_version=%s' % str(sys.version_info))

## read results from Splunk
logger.info("Reading command arguments from Splunk")
keywords, argvals  = splunk.Intersplunk.getKeywordsAndOptions()

## Determine what mode and output we want to run the command with
mode = getarg(argvals, "mode", "")
output = getarg(argvals, "output", "summary")

## Get all of the command arguments
line_breaker = getarg(argvals, "line_breaker", r'([\r\n]+)(\s+)?')
truncate = int(getarg(argvals, "truncate", "10000"))
log_level = getarg(argvals, "log_level", "INFO")

## Adjust the log level if necessary
logger.setLevel(log_level)

try:
    ## get results from splunk
    logger.info("Reading results from Splunk")
    results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()
    logger.info("Finished reading %s events from Splunk" % len(results))

    ## We need info about the current seesion in order to get the regex lookup via search
    kwargs = {}
    for f in ['owner','namespace','sessionKey','hostPath']:
        if f in settings:
            kwargs[f] = settings[f]

    ## Run the necessary path depending on the mode selected
    if(mode == "suggest"):
        ## Suggest mode is for suggesting the various prop configurations
        logger.info("mode=suggest")

        ## Run a search to get the regex list from the lookup with the app
        search = "| inputlookup propinator_data.csv | fillnull value=\"\" tf | fillnull value=0 ignore | search ignore!=1"
        lookup_regexes = splunk.search.searchAll(search, **kwargs)

        summary_lb = []
        summary_tp = []
        summary_tf = []
        summary_mtl = []
        summary_tr = []

        ## Loop through all of the passed in events
        for result in results:
            rex_re = ""
            rex_tf = ""
            rex_start = -1
            rex_len = -1
            evt = result["_raw"]

            for rex in lookup_regexes:
                r = str(rex['re'])
                tf = str(rex['tf'])
                logger.debug("Checking rex: %s" % r)

                pattern=re.compile(r)
                rexmatch = pattern.search(evt)
                if(rexmatch):
                    logger.info("Matched rex: %s" % r)
                    if(rex_re == ""):
                        rex_re = r
                        rex_tf = tf
                        rex_start = rexmatch.start()
                        rex_len = len(rexmatch.group())
                    else:
                        if(rexmatch.start() <= rex_start and len(rexmatch.group()) > rex_len):
                            rex_re = r
                            rex_tf = tf
                            rex_start = rexmatch.start()
                            rex_len = len(rexmatch.group())

            if(rex_re != ""):
                logger.debug("Matched rex_start: %s" % rex_start)
                if(rex_start == 0):
                    result["time_prefix"] = "^"
                    result["line_breaker"] = r'([\r\n]+)(\s+)?'+rex_re
                else:
                    preamble = evt[0:rex_start]
                    if(rex_start >= 10):
                        result["line_breaker"] = r'([\r\n]+)(\s+)?' + calculate_regex(preamble[0:10])
                        result["time_prefix"] = calculate_regex(preamble[-10:])
                    else:
                        result["line_breaker"] = r'([\r\n]+)(\s+)?' + calculate_regex(preamble)
                        result["time_prefix"] = calculate_regex(preamble)

                result["time_format"] = rex_tf

                if(len(evt) > 9999):
                    result["truncate"] = 100000
                else:
                    result["truncate"] = 10000

                result["max_ts_lookahead"] = rex_len

                summary_lb.append(result["line_breaker"])
                summary_tp.append(result["time_prefix"])
                summary_tf.append(result["time_format"])
                summary_mtl.append(result["max_ts_lookahead"])
                summary_tr.append(result["truncate"])

        ## if the output is a summary then emit a single event with the settings to be read by the Suggest operation
        if(output == "summary"):
            result = {}
            result["_time"] = int(time.time())
            if(len(summary_lb)):
                result["LINE_BREAKER"] = most_frequent(summary_lb)
                result["TIME_PREFIX"] = most_frequent(summary_tp)
                result["TIME_FORMAT"] = most_frequent(summary_tf)
                result["MAX_TIMESTAMP_LOOKAHEAD"] = most_frequent(summary_mtl)
                result["TRUNCATE"] = most_frequent(summary_tr)
                result["PARSE_STATUS"] = "OK"
            else:
                result["LINE_BREAKER"] = ""
                result["TIME_PREFIX"] = ""
                result["TIME_FORMAT"] = ""
                result["MAX_TIMESTAMP_LOOKAHEAD"] = ""
                result["TRUNCATE"] = ""
                result["PARSE_STATUS"] = "UNKNOWN"

            results = []
            results.append(result)

    elif (mode == "break"):
        ## Break mode is for testing the various prop configurations
        logger.info("mode=break")

        event_breaker = re.compile(line_breaker)
        events = []
        rawEvents = []

        ## Smush all of the events together by joining them on a newline
        logger.info("Converting events into a rawdata blob with each events preserving newlines")
        for result in results:
            rawEvents.append(result["_raw"])
        rawdata = "\n".join(rawEvents)

        ## treat the smushed blob of events as a sorta stream, find the match, then break using where the match starts.
        ## Also factors in the truncate (not perfect).
        logger.info("Breaking events based on event breaker %s" % event_breaker)
        while True:
            m = event_breaker.search(rawdata)
            if(m):
                logger.debug("Breaking match")
                if(len(rawdata[0:m.start(1)]) > truncate):
                    e = rawdata[0:truncate]
                    events.append(e)
                    rawdata = rawdata[truncate:]
                else:
                    logger.debug("Breaking start %s" % m.start(1))
                    e = rawdata[0:m.start(1)]
                    events.append(e)
                    rawdata = rawdata[m.start(1)+1:]
            else:
                if(len(rawdata) > truncate):
                    e = rawdata[0:truncate]
                    events.append(e)
                    rawdata = rawdata[truncate:]
                else:
                    e = rawdata
                    events.append(e)
                    break

        results = []
        for event in events:
            result = {}
            result["_raw"] = event
            results.append(result)
            logger.debug(result)

# catch any error in reading from splunk
except:
    import traceback
    stack = traceback.format_exc()
    logger.error("Error : Traceback: " + str(stack))
    results = splunk.Intersplunk.generateErrorResults("Error : Traceback: " + str(stack))

# write the results enriched with new fields
logger.info("Writing results back to Splunk")
splunk.Intersplunk.outputResults(results)