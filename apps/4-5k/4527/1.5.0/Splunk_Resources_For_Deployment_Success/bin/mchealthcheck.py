from urllib2 import urlopen, Request, HTTPError, URLError
import sys, time, os, re, json, urllib, requests
import logging, logging.handlers
import splunk.rest as rest, splunk.Intersplunk as si


LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "mchealthcheck.log"

def setup_logging():  # setup logging
    global SPLUNK_HOME, LOG_LEVEL, LOG_FILE_NAME
    if 'SPLUNK_HOME' in os.environ:
        SPLUNK_HOME = os.environ['SPLUNK_HOME']

    log_format = "%(asctime)s %(levelname)-s\t%(module)s[%(process)d]:%(lineno)d - %(message)s"
    logger = logging.getLogger('v')
    logger.setLevel(LOG_LEVEL)

    l = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', LOG_FILE_NAME), mode='a', maxBytes=1000000, backupCount=2)
    l.setFormatter(logging.Formatter(log_format))
    logger.addHandler(l)

    # ..and (optionally) output to console
    logH = logging.StreamHandler()
    logH.setFormatter(logging.Formatter(fmt=log_format))
    # logger.addHandler(logH)

    logger.propagate = False
    return logger

def die(msg):
    logger.error(msg)
    exit(msg)

def validate_args(keywords, argvals):
    logger.info('function="validate_args" calling getKeywordsAndOptions keywords="%s" args="%s"' % (str(keywords), str(argvals)))

    # validate args
    ALLOWED_OPTIONS = ['debug', 'mode']
    # # MANDATORY_OPTIONS = ['student_email', 'student_name', 'student_company']
    illegal_args = filter(lambda x: x not in ALLOWED_OPTIONS, argvals)
    if len(illegal_args) != 0:
        die("The argument(s) '%s' is invalid. Supported arguments are: %s" % (illegal_args, ALLOWED_OPTIONS))

    # # mandatory_args = filter(lambda x: x in MANDATORY_OPTIONS, argvals)
    # # if len(mandatory_args) != len(MANDATORY_OPTIONS):
    # #     die("Missing one or more mandatory argument(s): %s" % MANDATORY_OPTIONS)

    # if not arg_on_and_enabled(argvals, "student_email", rex="^[^@]+@.+?\.\w{2,}$"):
    #     die("Email not valid or specified")
    # if not arg_on_and_enabled(argvals, "student_name"):
    #     die("User name not valid or specified")
    # if not arg_on_and_enabled(argvals, "student_company"):
    #     die("Company name not valid or specified")
    if 'mode' in argvals and not arg_on_and_enabled(argvals, "mode", rex="^summary|detail$"):
        die("Specified mode is not valid, supported modes are: %s" % ['summary', 'detail'])

def arg_on_and_enabled(argvals, arg, rex=None, is_bool=False):
    result = False

    if is_bool:
        rex = "^(?:t|true|1|yes)$"

    if (rex is None and arg in argvals) or (arg in argvals and re.match(rex, argvals[arg])):
        result = True
    return result

def do_rest_call(session_key, endpoint, post=None):
    logger.debug('function="do_rest_call" calling endpoint="%s" post="%s"' % (str(endpoint), str(post)))

    response, content = rest.simpleRequest(endpoint, sessionKey=session_key, method='GET', postargs=post, raiseAllErrors=False)

    error_detail = "ok"
    if response.status != 200:
        error_detail = content

    logger.debug('calling endpoint="%s", returned status=%s, detail="%s"' % (str(endpoint), response.status, error_detail))
    # logger.debug('resp="%s"' % server_response)
    return content, response

def severity_level_normalizer(severity_level):
    # * - -1 (N/A)      means: "Not Applicable"
    # * - 0 (ok)       means: "all good"
    # * - 1 (info)     means: "just ignore it if you don't understand"
    # * - 2 (warning)  means: "well, you'd better take a look"
    # * - 3 (error)    means: "FIRE!"
    logger.debug("----> passing %s", severity_level)
    checklist_codes = {
        0: "success",
        1: "info",
        2: "warning",
        3: "error"
    }
    return checklist_codes.get(severity_level, "n/a")

if __name__ == '__main__':
    logger = setup_logging()
    logger.info('starting..')
    eStart = time.time()
    try:
        keywords = filter(lambda x: not re.findall("^\w+=|mchealthcheck.py$", x), sys.argv)
        argvals = dict(u.split("=", 1) for u in filter(lambda x: re.findall("^\w+=", x), sys.argv))
        if arg_on_and_enabled(argvals, "debug", is_bool=True):
            logger.setLevel(logging.DEBUG)

        results,dummy,settings = si.getOrganizedResults()
        sessionKey = settings.get("sessionKey")
        # logger.debug('getting session_key=%s' % sessionKey)
        
        # rest_uri = "/services/grademe/student?output_mode=json"
        # confsettings = json.loads(do_rest_call(sessionKey, rest_uri))['entry'][0]['content']
        # logger.debug("conf settings are: {settings}".format(settings=confsettings))
        
        # for setting in confsettings:
        #     if not arg_on_and_enabled(argvals, setting) and confsettings.get(setting) not in [None, '']:
        #         logger.debug("found .conf setting='{setting}', and no argval; performing substitution to value='{value}'".format(setting=setting, value=confsettings[setting]))
        #         argvals[setting] = confsettings[setting]
        validate_args(keywords, argvals)

        # gather data of interest by executing pre-defined saved searches
        # search must begin with "Gather:"
        check_bundle = []
       
        rest_uri = "/servicesNS/-/-/configs/conf-checklist?output_mode=json&count=-1&search=disabled%3Dfalse"
        checklist_content, checklist_response = do_rest_call(sessionKey, rest_uri)
        ss = json.loads(checklist_content)
        for search in ss['entry']:
            # logger.debug(search)
            logger.info('running check="%s"' % search['name'])
            post = {}
            post['exec_mode'] = "oneshot"
            post['output_mode'] = "json"

            # build necessary search, and sub for $rest_scope$ and $hist_scope$
            check_search = ""
            search_prefix = "search "
            if re.findall("^\s*\|", search['content']['search']):
                search_prefix = ""
            
            check_search = "{prefix}{search}".format(
                prefix = search_prefix, 
                search = search['content']['search'].replace("$rest_scope$", "splunk_server_group=*").replace("$hist_scope$", "search_group=*")
            )
            post['search'] = check_search
            rest_uri = "/servicesNS/-/{app}/search/jobs/".format(app=search['content']['eai:appName'])
            
            check_output = {
                '_time': time.time(),
                'check_name': search['name'],
                'check_app': search['content']['eai:appName'],
                'check_category': search['content']['category'],
                'check_tags': search['content']['tags']
            }

            check_content, check_response = do_rest_call(sessionKey, rest_uri, post)
            try:
                tmp_map=json.loads(check_content)
                
                rc = 0
                check_status = -1
                issue_instances = []
                check_status_out = {"n/a": 0, "success": 0, "info": 0, "warning": 0, "error": 0}
                if tmp_map['results']:
                    rc = len(tmp_map['results'])
                    check_status = int(max(map(lambda x : x['severity_level'], tmp_map['results'])))
                    for i in tmp_map['results']:
                        check_status_out[severity_level_normalizer(i['severity_level'])] += 1
                        if i.has_key('instance') and int(i['severity_level']) > 0:
                            issue_instances.append(str(i['instance']))
                    
                check_output['check_result_count'] = rc 
                check_output['check_status'] = severity_level_normalizer(check_status)
                check_output['check_issue_instances'] = issue_instances

                if arg_on_and_enabled(argvals, "mode", rex="^detail$"):
                    check_output['check_result_detail'] = json.dumps(tmp_map['results'])
                    check_output['check_status_detail'] = json.dumps(check_status_out)
            except Exception, e:
                logger.error('error processing check="%s", skipping it' % search['name'])
                
                check_output['check_status'] = "fatal"
                check_output['msg'] = check_content
                continue
            finally:
                check_bundle.append(check_output)

        si.outputResults(check_bundle) 
    except Exception, e:
        logger.error('error while processing submit, exception="%s"' % e)
        si.generateErrorResults(e)
        raise Exception(e)
    finally:
        logger.info('exiting, execution duration=%s seconds' % (time.time() - eStart))
