"""
Written by Kyle Smith for Splunk, Inc.
Copyright (c)2018 Splunk, Inc.

SUPPORTING INFO:
Version: 1.1.2
"""
import splunk.Intersplunk as si
import os
import logging
import logging.handlers
import splunk
import splunk.entity as entity
import splunk.Intersplunk
import json
import hashlib
import functools
import schedule
import threading
import sys
import datetime
from threading import Thread
import time
from splunk.rest import simpleRequest


def setup_logging():
    logger = logging.getLogger('splunk.replay-command')
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = 'replay.log'
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"

    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a', maxBytes=5000000, backupCount=5)
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    logger.setLevel(logging.INFO)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


if __name__ == '__main__':

    logger = setup_logging()
    try:
        keywords, options = si.getKeywordsAndOptions()
        use_schedule = options.get('schedule', 'false')
        # The field that has the initial time of the field
        schedule_field = options.get('schedule_time', 'schedule_time')
        # The time difference to use. 86400 is default (Execute next day at same time)
        time_diff = options.get('time_diff', 86400)
        # The earliest time of the search in unix seconds
        earliest_time = options.get('earliest', 'earliest')
        # The latest time of the search in unix seconds
        latest_time = options.get('latest', 'latest')
        # The field that contains the search to execute
        search_field = options.get("search", "search").replace('"', "")
        # Show the data sent to /services/search/jobs
        show_data = options.get("show_data", "false")
        # Changes the polling interval of the scheduler
        timer = int(options.get("timer", 10))
        # Should I load balance on the SHC?
        shc_lb = options.get("shc_lb", "false")
        # sch_lb requires a user to be sent down.
        shc_lb_user = options.get("shc_lb_user", None)
        if shc_lb == "true" and shc_lb_user is None:
            si.generateErrorResults("A shc_lb_user must be configured if shc_lb is true.")
            sys.exit(2)
        logger.info("action=processing_results")
        # logger.debug("Specified path: %s" % path)
        logger.debug("type=argument schedule={}".format(use_schedule))
        logger.debug("type=argument schedule_time={}".format(schedule_field))
        logger.debug("type=argument earliest_time={}".format(earliest_time))
        logger.debug("type=argument latest_time={}".format(latest_time))
        logger.debug("type=argument search={}".format(search_field))
        logger.debug("type=argument show_data={}".format(show_data))
        logger.debug("type=argument timer={}".format(timer))
        logger.debug("type=argument shc_lb={}".format(shc_lb))
        logger.debug("type=argument shc_lb_user={}".format(shc_lb_user))
        results, dummyresults, settings = si.getOrganizedResults()
        logger.debug(
            "action=getOrganizedResults status=complete typeof_results={} result_len={}".format(type(results),
                                                                                                len(results)))
        if len(results) == 0:
            os._exit(0)
        if search_field not in results[0]:
            si.generateErrorResults("Search field: {} ; Not found.".format(search_field))
            sys.exit(3)
        if earliest_time not in results[0]:
            si.generateErrorResults("Earliest Time field: {} ; Not found.".format(earliest_time))
            sys.exit(4)
        if latest_time not in results[0]:
            si.generateErrorResults("Latest Time field: {} ; Not found.".format(latest_time))
            sys.exit(5)
        if use_schedule == "true" and schedule_field not in results[0]:
            si.generateErrorResults("Using scheduling, but no schedule time field found: {}".format(schedule_field))
            sys.exit(6)

        namespace = owner = sessionKey = parent_sid = None
        try:
            namespace = settings['namespace']
            owner = settings['owner']
            sessionKey = settings['sessionKey']
            parent_sid = settings['sid']
            logger.debug("action=got_settings")
        except KeyError, e:
            logger.error("settings={}".format(json.dumps(settings)))
            logger.error("key_not_found={}".format(e))

        job_endpoint = entity.buildEndpoint(['search',
                                             'jobs'])

        logger.debug("action=start object=job_endpoints_definition")


        def get_credential(cuser, sessionKey):
            """
            :param realm:
            :param cuser:
            :return:
            """
            try:
                realm = "spl_replay"
                logger.info("realm={} cuser={}".format(realm, cuser))
                entities = entity.getEntities(['storage', 'passwords'], namespace="search", owner='nobody',
                                              sessionKey=sessionKey, search="{0}:{1}".format(realm, cuser))
                key = "{0}:{1}:".format(realm, cuser)
                if key not in entities:
                    si.generateErrorResults(
                        "User {} not found in encrypted store with realm 'spl_replay'".format(cuser))
                else:
                    import urllib
                    return urllib.unquote(entities[key]["clear_password"])
            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                jsondump = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\"".format(
                    str(e), type(e).__name__, e, fname, exc_tb.tb_lineno)
                logger.error(jsondump)
                raise Exception(jsondump)


        def get_session_key_shc(host=None):
            try:
                pw = get_credential(shc_lb_user, sessionKey)
                rH, rB = simpleRequest(entity.buildEndpoint(['auth', 'login'], hostPath=host), method="POST",
                                       postargs={"username": shc_lb_user, "password": pw, "output_mode": "json"})
                rSp = json.loads(rB)
                if "sessionKey" in rSp:
                    logger.debug("host={} sessionKey_len={}".format(host, len(rSp["sessionKey"])))
                    return rSp["sessionKey"]
            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                myJson = "message={} exception_type={} exception_arguments={} filename={} line={}".format(
                    str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, )
                logger.warn("action=error function=get_session_key_shc {}".format(myJson))
                logger.warn("action=error response_body={}".format(responseBody))
                return "has_no_session_key"


        def job_endpoints():
            """ Get a list of SH Peers"""
            try:
                responseHeaders, responseBody = simpleRequest(entity.buildEndpoint(["shcluster", "status"]),
                                                              method="GET",
                                                              sessionKey=sessionKey, getargs={"output_mode": "json"})
                retItem = json.loads(responseBody)
                # item is "hostPath" in BuildEntities
                if len(retItem["messages"]) > 0:
                    if retItem["messages"][0]["type"] == "ERROR":
                        logger.info("action=spl_replay_endpoint_build shcluster='not_enabled' message='{}'".format(
                            retItem["messages"][0]["text"]))
                        return [{"endpoint": entity.buildEndpoint(['search', 'jobs']), "sessionKey": sessionKey}]
                    else:
                        logger.error("action=spl_replay_endpoint_build shcluster='status_unknown' message='{}'".format(
                            retItem["messages"][0]["text"]))
                        raise Exception(retItem["messages"][0]["text"])

                if "entry" in retItem and shc_lb == "true":
                    myEntry = retItem["entry"][0]
                    if "content" in myEntry:
                        myContent = myEntry["content"]
                        if "peers" in myContent:
                            p = myContent["peers"]
                            logger.debug("peers={}".format(json.dumps(p)))
                            logger.debug("keys={}".format(p.keys()))
                            peers_up = ["{}".format(x) for x in p.keys() if p[x]["status"] == "Up"]
                            logger.debug("up_peers={}".format(peers_up))

                            return [{"endpoint": entity.buildEndpoint(["search", "jobs"], hostPath=p[x]["mgmt_uri"]),
                                     "sessionKey": get_session_key_shc(p[x]["mgmt_uri"])} for x in
                                    peers_up]
                        else:
                            logger.error("action=spl_replay_endpoint_build failure=no_peers_in_content")
                            logger.debug("{}".format(json.dumps(myContent)))
                    else:
                        logger.error("action=spl_replay_endpoint_build failure=no_content_in_entry")
                        logger.debug("{}".format(json.dumps(myEntry)))
                elif shc_lb == "false":
                    logger.debug("message=\"search head cluster load balancing not enabled via config\"")
                    return [{"endpoint": entity.buildEndpoint(['search', 'jobs']), "sessionKey": sessionKey}]
                else:
                    logger.error("action=spl_replay_endpoint_build failure=no_entry in retItem")
                    logger.debug("{}".format(json.dumps(retItem)))

            except Exception, e:
                exc_type, exc_obj, exc_tb = sys.exc_info()
                fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                myJson = "msg={} exception_type={} exception_arguments={} filename={} line={} input_name=spl_replay".format(
                    str(e), type(e).__name__, e, fname, exc_tb.tb_lineno, )
                logger.error("job_endpoints_error={}".format(myJson))
                logger.error("responseBody={}".format(responseBody))


        logger.debug("action=start object=job_endpoints")
        peers = [x for x in job_endpoints() if x["sessionKey"] != "has_no_session_key"]
        peer_counter = 0
        parent_endpoint = entity.buildEndpoint(['search', 'jobs'])
        parent_session = sessionKey
        # peers[peer_counter % len(peers) << this will pick the next item in the list for dispatch
        logger.debug("endpoints={}".format([x["endpoint"] for x in peers]))
        logger.debug("len_results={}  endpoint={}".format(len(results), job_endpoint))
        try:
            # This decorator can be applied to
            def with_logging(func):
                @functools.wraps(func)
                def wrapper(*args, **kwargs):
                    my_md5 = hashlib.md5("{}".format(args)).hexdigest()
                    logger.info("action=job_thread status=started md5_tracker={}".format(my_md5))
                    logger.debug('running_job="{}" md5_tracker={}'.format(args, my_md5))
                    kwargs["md5_tracker"] = my_md5
                    wresult = func(*args, **kwargs)
                    logger.debug('completed_job="{} md5_tracker={}"'.format(args, my_md5))
                    logger.info("action=job_thread status=complete md5_tracker={}".format(my_md5))
                    return wresult

                return wrapper


            class ThreadWithReturnValue(Thread):
                def __init__(self, group=None, target=None, name=None,
                             args=(), kwargs={}, Verbose=None):
                    Thread.__init__(self, group, target, name, args, kwargs, Verbose)
                    self._return = None

                def run(self):
                    if self._Thread__target is not None:
                        self._return = self._Thread__target(*self._Thread__args,
                                                            **self._Thread__kwargs)

                def join(self):
                    Thread.join(self)
                    return self._return


            @with_logging
            def job(psid, et, lt, sf, r, p, pc, md5_tracker=None):
                tdata = {'output_mode': 'json',
                         'earliest_time': et,
                         'latest_time': lt,
                         'search': sf}

                logger.debug("peers={} peer_counter={}".format(p, pc))
                job_endpoint = p[pc % len(peers)]["endpoint"]
                localSession = p[pc % len(peers)]["sessionKey"]
                logger.debug("endpoint={} peer_counter={}".format(job_endpoint, pc))
                try:
                    tresponseHeaders, tresponseBody = simpleRequest(job_endpoint,
                                                                    method='POST',
                                                                    postargs=tdata,

                                                                    sessionKey=localSession)
                    tsid_return = json.loads(tresponseBody)
                except Exception, e:
                    logger.error("action=dispatch_error message={}".format(e))
                    r["error_message"] = "{}".format(e)
                    return schedule.CancelJob
                logger.debug("response={}".format(json.dumps(tresponseBody)))
                if "messages" in tsid_return:
                    logger.debug("action=found_message type={} md5_tracker={}".format(tsid_return["messages"][0]["type"],
                                                                                 md5_tracker))
                    if tsid_return["messages"][0]["type"] == "FATAL":
                        logger.debug("action=FATAL md5_tracker={}".format(md5_tracker))
                        r["error"] = "FATAL: {}".format(tsid_return["messages"][0]["text"])
                        return schedule.CancelJob
                pc += 1

                mythread = threading.currentThread()
                tid = mythread.name
                iid = mythread.ident
                logger.info(
                    "parent_sid={} sid={} thread={} thread_ident={} md5_tracker={}".format(psid, tsid_return["sid"],
                                                                                           tid, iid, md5_tracker))
                r["thread_name"] = tid
                r["thread_sid"] = tsid_return["sid"]
                r["thread_ident"] = iid
                r["md5_tracker"] = md5_tracker
                r["endpoint"] = job_endpoint
                return schedule.CancelJob


            def run_threaded(job_func, psid, et, lt, sf, r, p, pc):
                job_thread = ThreadWithReturnValue(target=job_func, args=[psid, et, lt, sf, r, p, pc])
                job_thread.start()
                return job_thread.join()


            for result in results:
                try:
                    logger.debug("event_data={}".format(result))
                    result["md5_tracker"] = hashlib.md5(
                        "{}_{}_{}".format(result[earliest_time], result[latest_time], result[search_field])).hexdigest()
                    if use_schedule == "false":
                        data = {'output_mode': 'json',
                                'earliest_time': result[earliest_time],
                                'latest_time': result[latest_time],
                                'search': result[search_field]}
                        job_endpoint = peers[peer_counter % len(peers)]["endpoint"]
                        localSession = peers[peer_counter % len(peers)]["sessionKey"]
                        logger.debug("endpoint={} peer_counter={}".format(job_endpoint, peer_counter))
                        logger.info("action=dispatch_search md5_tracker={}".format(result["md5_tracker"]))
                        responseHeaders, responseBody = simpleRequest(job_endpoint,
                                                                      method='POST',
                                                                      postargs=data,
                                                                      sessionKey=localSession)
                        peer_counter += 1
                        sid_return = json.loads(responseBody)
                        try:
                            if "messages" in sid_return:
                                logger.debug(
                                    "action=found_message type={} ".format(sid_return["messages"][0]["type"]))
                                if sid_return["messages"][0]["type"] == "FATAL":
                                    result["error"] = "FATAL: {}".format(sid_return["messages"][0]["text"])
                                    continue
                            result["spawned_sid"] = sid_return["sid"]
                            result["endpoint"] = job_endpoint
                            if show_data == "true":
                                logger.debug("action=show_data data_executed={}".format(data))
                                result["data"] = data
                            logger.info("action=dispatch_search status=complete md5_tracker={} sid={} full_search=\"{}\"".format(result["md5_tracker"], sid_return["sid"], result[search_field]))
                        except KeyError, e:
                            result["error"] = responseBody
                            logger.error("action=key_error {}={}".format(e, responseBody))
                    # Use the Scheduler
                    else:
                        logger.info("action=using_schedules")
                        try:
                            schd_time = result[schedule_field]
                            new_time = float(schd_time) + float(time_diff)
                            time_str = datetime.datetime.fromtimestamp(float(new_time)).strftime("%H:%M:%S")
                            logger.info(
                                "action=setting_scheduled_search md5_tracker={}  original_time=\"{}\" scheduled_time=\"{}\" full_scheduled_time=\"{}\"".format(
                                    result["md5_tracker"],
                                    datetime.datetime.fromtimestamp(float(schd_time)).strftime("%m-%d-%Y %H:%M:%S"),
                                    time_str,
                                    datetime.datetime.fromtimestamp(float(new_time)).strftime("%m-%d-%Y %H:%M:%S")))

                            schedule.every().day.at(time_str).do(run_threaded, job, parent_sid, result[earliest_time],
                                                                 result[latest_time], result[search_field],
                                                                 result, peers, peer_counter).tag("spl_replay")
                            peer_counter += 1
                            result["scheduled_for"] = datetime.datetime.fromtimestamp(float(new_time)).strftime(
                                "%m-%d-%Y %H:%M:%S")
                            result["parent_sid"] = parent_sid
                        except Exception, e:
                            logger.error("action=schedule_error message={}".format(e))
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    jsondump = "action=result_error message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\"".format(
                        str(e), type(e).__name__, e, fname, exc_tb.tb_lineno)
                    logger.error(jsondump)
                    result["error"] = "{}".format(jsondump)

            # SET TTL TO ACCOUNT FOR TIME DIFF TO ENSURE SEARCH WON'T TIMEOUT BEFORE COMPLETION
            ttl = time_diff
            # Always have a 10 minute minimum ttl to allow for debugging on searches.
            if time_diff < 600:
                ttl = 600
            responseHeaders, responseBody = simpleRequest("{}/{}/control".format(parent_endpoint, parent_sid),
                                                          method='POST',
                                                          postargs={"output_mode": "json",
                                                                    "action": "setttl",
                                                                    "ttl": ttl},
                                                          sessionKey=parent_session)
            parent_sid_status = json.loads(responseBody)
            dispatchState = parent_sid_status["messages"][0]["text"]
            logger.info("action=set_ttl_api sid={} message=\"{}\" ttl={}".format(parent_sid, dispatchState, ttl))

            # TICKLE ME ELMO
            responseHeaders, responseBody = simpleRequest("{}/{}/control".format(parent_endpoint, parent_sid),
                                                          method='POST',
                                                          postargs={"output_mode": "json",
                                                                    "action": "touch"},
                                                          sessionKey=parent_session)
            parent_sid_status = json.loads(responseBody)
            dispatchState = parent_sid_status["messages"][0]["text"]
            logger.info("action=touch_api sid={} message=\"{}\"".format(parent_sid, dispatchState))
            # PAUSE THE SEARCH TO KEEP IT FROM AUTO-PRUNE
            responseHeaders, responseBody = simpleRequest("{}/{}/control".format(parent_endpoint, parent_sid),
                                                          method='POST',
                                                          postargs={"output_mode": "json",
                                                                    "action": "pause"},
                                                          sessionKey=parent_session)
            parent_sid_status = json.loads(responseBody)
            dispatchState = parent_sid_status["messages"][0]["text"]
            logger.info("action=pause_api sid={} message=\"{}\"".format(parent_sid, dispatchState))
            # RUN THE SCHEDULES
            while schedule.has_jobs():
                logger.info("action=running_scheduled_jobs jobs_remaining={} sid={}".format(schedule.remaining_jobs(),
                                                                                            parent_sid))
                responseHeaders, responseBody = simpleRequest("{}/{}".format(parent_endpoint, parent_sid),
                                                              method='GET',
                                                              getargs={"output_mode": "json"},
                                                              sessionKey=parent_session)
                parent_sid_status = json.loads(responseBody)
                dispatchState = parent_sid_status["entry"][0]["content"]["isPaused"]
                logger.debug("sid={} isPaused={}".format(parent_sid, dispatchState))
                should_continue = True
                if not dispatchState:
                    logger.warn(
                        "action=clearing_state sid={} reason=\"not in paused state\"".format(parent_sid))
                    logger.warn(
                        "action=clearing_state message=\"This is as a safety check to make sure long running replay searches don't orphan themselves.\"")
                    schedule.clear("spl_replay")
                    should_continue = False
                schedule.run_pending()
                if should_continue:
                    time.sleep(timer)
            else:
                logger.info("action=completed_processing sid={}".format(parent_sid))
                si.outputResults(results)

        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            jsondump = "message=\"{}\" exception_type=\"{}\" exception_arguments=\"{}\" filename=\"{}\" line=\"{}\"".format(
                str(e), type(e).__name__, e, fname, exc_tb.tb_lineno)
            logger.error(jsondump)
            result["error"] = "{}".format(jsondump)

    except Exception, e:
        import traceback
        stack = traceback.format_exec()
        logger.error("action=general_error message='{}' stack={}".format(e, stack))
        si.generateErrorResults("action=general_error message='{}' stack={}".format(e, stack))
