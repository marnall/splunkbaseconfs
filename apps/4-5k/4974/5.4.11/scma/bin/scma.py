import sys
import requests
import uuid

if sys.version_info >= (3, 0):
    from requests.packages.urllib3.exceptions import InsecureRequestWarning
    requests.packages.urllib3.disable_warnings(InsecureRequestWarning)
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError, URLError
    import time, os, re, json, urllib.request, urllib.parse, urllib.error, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si
    import urllib3
    urllib3.disable_warnings()
else:
    from urllib2 import urlopen, Request, HTTPError, URLError
    import sys, time, os, re, json, urllib, requests
    import logging, logging.handlers
    import splunk.rest as rest, splunk.Intersplunk as si


# Uncomment this block before debugging with VS Code

'''
# !!!!! DEBUG !!!!
sys.path.append(os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','SA-VSCode','bin'))
import splunk_debug as dbg
dbg.enable_debugging(timeout=25)
#################
'''

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "scma.log"

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

def validate_args(args):
    logger.info('function="validate_args" calling validate_args args="%s"' % (str(args)))
    ALLOWED_OPTIONS = ['checks', 'order', 'log', 'timeout', 'taskid', 'taskstatus']
    illegal_args = [option for option in args if option not in ALLOWED_OPTIONS]
    if illegal_args:
        die("The argument(s) '%s' is invalid. Supported arguments are: %s" % (illegal_args, ALLOWED_OPTIONS))
    else:
        logger.info('Arguments validated')

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


def get_order(arg_orders):
    ''' Produce the list of saved searches to be run and their order.
    Note that the order in the arguments takes preference over the "search_order", so order=("2,1")
    runs 2 then 1.
    '''
    order = []
    if not arg_orders:
        return order
    order_components = arg_orders.split(',')
    for order_component in order_components:
        range_partition = order_component.partition('-')
        try:
            if not range_partition[1]:
                order.append(int(order_component))
            else:
                order += range(
                    int(range_partition[0]),
                    int(range_partition[2]) + 1
                )
        except ValueError:
            die("The orger range '%s' is invalid. ranges should be in the form 1-2"
                % (order_component))
    # logger.info('task_id="%s" task_status="Not started" search_order: "%s"' % (order))
    return order


def get_searches_to_run(order, saved_searches):
    ''' Given a list of search_orders and a list of saved_sarches, pull all the saved_searches
    in the list of search_orders '''
    searches_to_run = []
    for i in order:
        found = False
        for search in saved_searches:
            if search['content'].get('search_order', None) == str(i):
                searches_to_run.append(search)
                found = True
                continue
        if not found:
            # TENG-242 log warning but continue if search_order not in list
            logger.warning('Search_order "%d" not found. Skipping.' % (i))
    return searches_to_run


if __name__ == '__main__':

    logger = setup_logging()
    eStart = time.time()

    # Attaching to VS Code Debugger
    # dbg.set_breakpoint()

    try:

        keywords = []
        argvals = dict()
        if sys.version_info >= (3, 0):
            keywords = [x for x in sys.argv if not re.findall("^\w+=|scma.py$", x)]
            argvals = dict(u.split("=", 1) for u in [x for x in sys.argv if re.findall("^\w+=", x)])
        else :
            keywords = filter(lambda x: not re.findall("^\w+=|scma.py$", x), sys.argv)
            argvals = dict(u.split("=", 1) for u in filter(lambda x: re.findall("^\w+=", x), sys.argv))


        if arg_on_and_enabled(argvals, "debug", is_bool=True):
            logger.setLevel(logging.DEBUG)

        args = dict(order=[],
                    log="",
                    checks=[],
                    timeout=0,
                    taskid=str(uuid.uuid4()),
                    taskstatus="STARTING")
        rerun_mode = False
        task_id = args['taskid']
        task_status = args['taskstatus']
        for opt in sys.argv[1:]:
            key, value = opt.split("=")
            if key == "order":
                # Multiple repeated options allowed
                args[key].append(value)
            else:
                # Take the last option as the only item
                args[key] = value
            if key == "taskid":
                rerun_mode = True
        validate_args(args)

        if args['log']:
            logger.info(args['log'])
        logger.info('task_status='+ task_status+' task_id='+task_id)

        results,dummy,settings = si.getOrganizedResults()
        sessionKey = settings.get("sessionKey")
        # logger.debug('getting session_key=%s' % sessionKey)


        # get mgm port information
        # default to 8089
        mgmtHostPort = '8089'
        try :
            rest_uri = "/services/server/settings?output_mode=json"
            mgmtport_content, mgmtport_response = do_rest_call(sessionKey, rest_uri)
            ss = json.loads(mgmtport_content)
            mgmtHostPort = str(ss['entry'][0]["content"]['mgmtHostPort'])

        except Exception as e:
            logger.error('task_id="%s" task_status="%s" error while trying to get splunk mgmt port ... using default port 8089' % (task_id, task_status))

        # gather data of interest by executing pre-defined saved searches
        # search must begin with "Gather:"
        check_bundle = []

        # rest_uri = "/servicesNS/nobody/scma/configs/conf-checklist?output_mode=json&count=-1&search=disabled%3Dfalse&sort_key=check_order&search=eai%3Aacl.app%3Dscma"
        # rest_uri = "/servicesNS/nobody/scma/saved/searches?output_mode=json&search=eai%3Aacl.app%3Dscma&sort_key=search_order&count=91"
        rest_uri = "/servicesNS/nobody/scma/saved/searches?output_mode=json&search=eai%3Aacl.app%3Dscma&sort_key=search_order&f=search_order&f=sleep_after&f=sub_category&f=search&count=300"
        checklist_content, checklist_response = do_rest_call(sessionKey, rest_uri)
        ss = json.loads(checklist_content)
        checks_count = str(len(ss['entry']))

        # execute checks in a specific order
        if "order" in args:
            order = get_order(args.get('order', None)[0])
            saved_searches = get_searches_to_run(order, ss['entry'])
            checks_count = str(len(saved_searches))

            for search in saved_searches:
                if not rerun_mode :
                    task_status = "RUNNING"

                #add a delay before running the next check if it's defined in | SCMA parameters
                if "timeout" in args :
                    time.sleep(int(args["timeout"]))

                post = {}
                post['exec_mode'] = "normal"
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
                # rest_uri = "/servicesNS/nobody/scma/search/jobs/".format(app=scma['content']['eai:appName'])
                #rest_uri = "/servicesNS/nobody/scma/search/jobs/".format(app=search['content']['eai:appName'])
                rest_uri = "/servicesNS/nobody/scma/search/jobs/".format(app=search["acl"]["app"])


                check_output = {
                    '_time': time.time(),
                    'check_name': search['name'],
                    'check_app': search["acl"]["app"],
                    'check_category': search['content']['sub_category']
                    # 'check_tags': search['content']['tags']
                }

                if not rerun_mode :
                    logger.info('task_id="%s" task_status="RUNNING" running check="%s" status="starting" sub_category="%s" total="%s"  job_status="RUNNING" search_order="%s" ' % (task_id, search['name'], check_output['check_category'],checks_count,search["content"]["search_order"]))
                else :
                    logger.info('task_id="%s" task_status="%s" running check="%s" status="starting" sub_category="%s" total="%s"  job_status="RUNNING" search_order="%s" ' % (task_id, task_status, search['name'], check_output['check_category'],checks_count,search["content"]["search_order"]))

                try:
                    check_content, check_response = do_rest_call(sessionKey, rest_uri, post)
                    sid=json.loads(check_content)["sid"]

                    job_status = "STARTING"
                    # get job sid and verify job status before checking results
                    check_output['check_status'] = "fatal"

                    while ("DONE" not in job_status) and ("FAILED" not in job_status):
                        check_content, check_response = do_rest_call(sessionKey, "/servicesNS/nobody/scma/search/jobs/"+sid)
                        if '<s:key name="dispatchState">' in check_content.decode() :
                            job_status = check_content.decode().split('<s:key name="dispatchState">')[1].split('</s:key>')[0]
                        if "DONE" not in job_status:
                            if "FAILED" not in job_status:
                                time.sleep(5)

                        # verify skip option
                        skip_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','checks_skip.csv')
                        if os.path.exists(skip_file):
                            f=open(skip_file, "r")
                            lines = f.readlines()
                            newlines=[]
                            for idx,line in enumerate(lines) :
                                values = line.split(",")
                                if search['name'] in values[1] and task_id in values[0]:
                                    # skip current check
                                    job_status = "FAILED"
                                    check_output['check_status'] = "skipped"
                                else :
                                    newlines.append(line)
                            f.close()
                            f=open(skip_file, "w")
                            f.writelines(newlines)
                            f.close()

                    #if job terminated correctly  check results
                    if "DONE" in job_status :

                        url = "https://localhost:"+mgmtHostPort+"/servicesNS/nobody/scma/search/jobs/"+sid+"/results?output_mode=json&count=0"

                        payload='output_mode=json'
                        headers = {
                        'Authorization': 'Splunk '+sessionKey,
                        'Content-Type': 'application/x-www-form-urlencoded'
                        }

                        response = requests.request("GET", url, headers=headers, data=payload,verify=False)  # nosemgrep

                        rc = 0
                        check_status = -1
                        issue_instances = []
                        check_status_out = {"n/a": 0, "success": 0, "info": 0, "warning": 0, "error": 0}
                        tmp_map = json.loads(response.text)
                        if tmp_map['results']:

                            if sys.version_info >= (3, 0):
                                tmp_map['results'] = list(filter(lambda x: x['severity_level'].lstrip('-').isdigit(),tmp_map['results']))
                            else :
                                tmp_map['results'] = filter(lambda x: x['severity_level'].lstrip('-').isdigit(),tmp_map['results'])

                            rc = len(tmp_map['results'])
                            check_status = int(max([x['severity_level'] for x in tmp_map['results']]))
                            for i in tmp_map['results']:
                                check_status_out[severity_level_normalizer(i['severity_level'])] += 1
                                if 'instance' in i and int(i['severity_level']) > 0:
                                    issue_instances.append(str(i['instance']))

                        check_output['check_result_count'] = rc
                        check_output['check_status'] = severity_level_normalizer(check_status)
                        check_output['check_issue_instances'] = issue_instances

                        if arg_on_and_enabled(argvals, "mode", rex="^detail$"):
                            check_output['check_result_detail'] = json.dumps(tmp_map['results'])
                            check_output['check_status_detail'] = json.dumps(check_status_out)

                except Exception as e:
                    logger.error('task_id="%s" task_status="%s" error processing check="%s", skipping it' % (task_id, task_status, search['name']))

                    check_output['check_status'] = "fatal"
                    check_output['msg'] = check_content
                    continue
                finally:
                    if search == saved_searches[-1]:
                        task_status = "COMPLETED"
                    logger.info('task_id="%s" task_status="%s" finish check="%s" status="%s" sub_category="%s" total="%s" job_status="%s" search_order="%s"' % (task_id, task_status, search['name'],check_output['check_status'], check_output['check_category'],checks_count,job_status,search["content"]["search_order"]))
                    # this needs to output the data to UI and after that  si.outputResults is no longer required
                    check_bundle.append(check_output)

                    if "sleep_after" in search['content'] :
                        time.sleep(int(search['content']['sleep_after']))

            task_status = "COMPLETED"
        else :
            # run all lookup generating checks in the first step
            processLookupGenerating = True
            idx=0
            while True :
                for search in ss['entry']:
                    # logger.debug(search)

                    if processLookupGenerating :
                        if not "| outputlookup" in search['content']['search'] :
                            continue

                    else :
                        if "| outputlookup" in search['content']['search'] :
                            continue

                    if "checks" in args:
                        logger.debug('checks are set')
                        checks_count = str(len(args["checks"].split(",")))
                        if not (search['name'] in args["checks"].split(",")) :
                            continue


                    #add a delay before running the next check if it's defined in scma parameters
                    if "timeout" in args :
                        time.sleep(int(args["timeout"]))

                    # print("*** Check if a process is running or not ***")
                    # Check if any chrome process was running or not.
                    # if checkIfProcessRunning('scma.py'):
                    #     logger.debug('Yes a chrome process was running')
                    # else:
                    #     logger.debug('No chrome process was running')

                    # check if the check arg is set
                    # split the comma separated list of checks
                    # if check_name is not in array, skip and try the next one
                    len_checks = len(ss['entry'])-1
                    if "checks" in args:
                        len_checks = len(args['checks'].split(","))-1

                    if not rerun_mode :
                        task_status = "RUNNING"
                        if idx==len_checks :
                            task_status = "COMPLETED"

                    idx=idx+1

                    post = {}
                    post['exec_mode'] = "normal"
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
                    # rest_uri = "/servicesNS/nobody/scma/search/jobs/".format(app=scma['content']['eai:appName'])
                    rest_uri = "/servicesNS/nobody/scma/search/jobs/".format(app=search["acl"]["app"])

                    check_output = {
                        '_time': time.time(),
                        'check_name': search['name'],
                        'check_app': search["acl"]["app"],
                        'check_category': search['content']['sub_category']
                        # 'check_tags': search['content']['tags']
                    }

                    if not rerun_mode :
                        logger.info('task_id="%s" task_status="RUNNING" running check="%s" status="starting" sub_category="%s" total="%s"  job_status="RUNNING" search_order="%s" ' % (task_id, search['name'], check_output['check_category'],checks_count,search["content"]["search_order"]))
                    else :
                        logger.info('task_id="%s" task_status="%s" running check="%s" status="starting" sub_category="%s" total="%s"  job_status="RUNNING" search_order="%s" ' % (task_id, task_status, search['name'], check_output['check_category'],checks_count,search["content"]["search_order"]))

                    try:
                        check_content, check_response = do_rest_call(sessionKey, rest_uri, post)
                        sid=json.loads(check_content)["sid"]

                        job_status = "STARTING"
                        # get job sid and verify job status before checking results
                        check_output['check_status'] = "fatal"

                        while ("DONE" not in job_status) and ("FAILED" not in job_status):
                            check_content, check_response = do_rest_call(sessionKey, "/servicesNS/nobody/scma/search/jobs/"+sid)
                            if '<s:key name="dispatchState">' in check_content.decode() :
                                job_status = check_content.decode().split('<s:key name="dispatchState">')[1].split('</s:key>')[0]
                            if "DONE" not in job_status:
                                if "FAILED" not in job_status:
                                    time.sleep(5)

                            # verify skip option
                            skip_file = os.path.join(os.environ['SPLUNK_HOME'],'etc','apps','scma','lookups','checks_skip.csv')
                            if os.path.exists(skip_file):
                                f=open(skip_file, "r")
                                lines = f.readlines()
                                newlines=[]
                                for idx,line in enumerate(lines) :
                                    values = line.split(",")
                                    if search['name'] in values[1] and task_id in values[0]:
                                        # skip current check
                                        job_status = "FAILED"
                                        check_output['check_status'] = "skipped"
                                    else :
                                        newlines.append(line)
                                f.close()
                                f=open(skip_file, "w")
                                f.writelines(newlines)
                                f.close()

                        #if job terminated correctly  check results
                        if "DONE" in job_status :

                            url = "https://localhost:"+mgmtHostPort+"/servicesNS/nobody/scma/search/jobs/"+sid+"/results?output_mode=json"

                            payload='output_mode=json'
                            headers = {
                            'Authorization': 'Splunk '+sessionKey,
                            'Content-Type': 'application/x-www-form-urlencoded'
                            }

                            response = requests.request("GET", url, headers=headers, data=payload,verify=False)  # nosemgrep

                            rc = 0
                            check_status = -1
                            issue_instances = []
                            check_status_out = {"n/a": 0, "success": 0, "info": 0, "warning": 0, "error": 0}
                            tmp_map=json.loads(response.text)
                            if tmp_map['results']:

                                if sys.version_info >= (3, 0):
                                    tmp_map['results'] = list(filter(lambda x: x['severity_level'].lstrip('-').isdigit(),tmp_map['results']))
                                else :
                                    tmp_map['results'] = filter(lambda x: x['severity_level'].lstrip('-').isdigit(),tmp_map['results'])

                                rc = len(tmp_map['results'])
                                check_status = int(max([x['severity_level'] for x in tmp_map['results']]))
                                for i in tmp_map['results']:
                                    check_status_out[severity_level_normalizer(i['severity_level'])] += 1
                                    if 'instance' in i and int(i['severity_level']) > 0:
                                        issue_instances.append(str(i['instance']))

                            check_output['check_result_count'] = rc
                            check_output['check_status'] = severity_level_normalizer(check_status)
                            check_output['check_issue_instances'] = issue_instances

                            if arg_on_and_enabled(argvals, "mode", rex="^detail$"):
                                check_output['check_result_detail'] = json.dumps(tmp_map['results'])
                                check_output['check_status_detail'] = json.dumps(check_status_out)
                    except Exception as e:
                        logger.error('task_id="%s" task_status="%s" error processing check="%s", skipping it' % (task_id,task_status, search['name']))

                        check_output['check_status'] = "fatal"
                        check_output['msg'] = check_content
                        continue
                    finally:
                        logger.info('task_id="%s" task_status="%s" finish check="%s" status="%s" sub_category="%s" total="%s" job_status="%s" search_order="%s"' % (task_id, task_status, search['name'],check_output['check_status'], check_output['check_sub_category'],checks_count,job_status,search["content"]["search_order"]))
                        # this needs to output the data to UI and after that  si.outputResults is no longer required
                        check_bundle.append(check_output)

                        if "sleep_after" in search['content'] :
                            time.sleep(int(search['content']['sleep_after']))

                if not processLookupGenerating :
                    break
                processLookupGenerating = False

        # replace si.output... with the streaming equivlant of it
        si.outputResults(check_bundle)
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        if not rerun_mode :
            logger.error('task_id="%s" task_status="ERROR" error while processing submit, exception="%s" line="%s"' % (task_id, e, exc_tb.tb_lineno))
        else :
            logger.error('task_id="%s" task_status="%s" error while processing submit, exception="%s" line="%s"' % (task_id,task_status, e, exc_tb.tb_lineno))

        si.generateErrorResults(e)
        raise Exception(e)
    finally:
        if not rerun_mode :
            logger.info('task_id="%s" task_status="COMPLETED" exiting, execution duration=%s seconds' % (task_id, time.time() - eStart))
        else :
            logger.info('task_id="%s" task_status="%s" exiting, execution duration=%s seconds' % (task_id,task_status, time.time() - eStart))
