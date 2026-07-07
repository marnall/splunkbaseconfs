import os, os.path, sys
import shutil
import fnmatch
import splunk.clilib.bundle_paths as bundle_paths
import splunk.Intersplunk
from logger import setup_logger
from settings import APP_NAME, APP_OWNER, get_app_home, get_platform, get_working_dir, get_upload_dir, get_conf_file, get_csv_dir
from datetime import timedelta, datetime
from summary.ts_searcher import Searcher
from summary.ts_hash import SummaryHash
from summary.ts_bundle import SummaryConfig, SummaryBundle
from summary.optic_client2 import OpticClient
from cred_store import TSCredStoreManager
from ts_config import TSConfigManager
import time
from settings import get_backfill_checkpoint

OWNER = APP_OWNER
SAVED_SEARCHES_DICT={"Generating DEST Summary":"dest_summary:dest",
                     "Generating SRC Summary":"src_summary:src",
                     "Generating Network Summary":"src_dest_summary:src|dest",
                     "Generating Web Summary":"url_summary:src|dest|url",
                     "Generating Filehash Summary":"filehash_summary:src|file_hash|file_name",
                     "Generating Email Summary":"email_summary:sender|receiver"}
logger = setup_logger('ts_backfill_summary')
BACKFILL_CHECKPOINT = get_backfill_checkpoint()
def ensure_dirs_exist(dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

def cleanup(dir):
    for root, dirs, files in os.walk(dir):
        for filename in fnmatch.filter(files, '*summary.csv*'):
            src = os.path.join(root, filename)
            os.remove(src)

def get_sessionKey():
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    logger.debug(settings)
    sessionKey = settings["sessionKey"]
    return sessionKey

def run_searches(sessionKey, earliest, latest):
    searcher = Searcher(sessionKey, app=APP_NAME, owner=OWNER, logger=logger)
    configManager = TSConfigManager(sessionKey=sessionKey, app=APP_NAME, owner=APP_OWNER)
    saved_searches = configManager.get_configured_saved_searches()
    logger.info("start saved searches: %s" % saved_searches)
    enabled_saved_searches = searcher.getEnabledSavedSearchNames(saved_searches)
    jobs = searcher.search(enabled_saved_searches, earliest, latest)
    lookup_fields = []
    one_job = None
    for saved_search in enabled_saved_searches:
        job = jobs[saved_search]
        logger.info(job["messages"])
        if job["dispatchState"] == "FAILED":
            continue
        else:
            lookup_fields.append(SAVED_SEARCHES_DICT.get(saved_search))
            one_job = job
    if not one_job:
        logger.info("All saved searches (%s) failed" % saved_searches)
        return 1
    job = one_job
    search_earliest_time = int (float(job["searchEarliestTime"]))
    search_latest_time = int (float(job["searchLatestTime"]))
    options = {'starttime':search_earliest_time, 'endtime':search_latest_time, "lookup_fields" : ",".join(lookup_fields)}
    config = SummaryConfig(get_conf_file(), logger=logger)
    config.set_options('myclient', options)
    return 0

def _get_hash_conf():
    config = SummaryConfig(get_conf_file(), logger=logger)
    options = config.get_options()
    if not options['error_rate']:
        error_rate = 0.0
    return options['hash'], float(options['error_rate'])

def hash_summaries():
    #move csv files to working directory
    for root, dirs, files in os.walk(get_csv_dir()):
        for filename in files:
            if filename.endswith('summary.csv'):
                src = os.path.join(root, filename)
                shutil.move(src, get_working_dir())
    hash_type, error_rate = _get_hash_conf()
    for root, dirs, files in os.walk(get_working_dir()):
        for filename in files:
            if filename.endswith('summary.csv'):
                src = os.path.join(root, filename)
                if os.path.getsize(src) > 0:
                    hash_file = SummaryHash(src, hash_type, error_rate=error_rate, logger=logger).gen_hash()
                else:
                    logger.info("Skip hashing empty file:%s" % src)

def gen_bundle():
    tar_bundle = SummaryBundle(get_working_dir(), get_upload_dir(), get_conf_file(), logger=logger)
    (file_name, uuid, date_str) = tar_bundle.create_bundle()
    return (file_name, uuid, date_str)

def encrypt(file_name, optic_client):
    from summary.ts_crypto import enc
    key = optic_client.getKey()
    target = file_name + ".enc"
    enc(file_name, target, key)
    return target

def upload_file(sessionKey, file_name, timestamp, date_str):
        credManager = TSCredStoreManager(sessionKey, APP_NAME, APP_OWNER, None)
        username, apikey = credManager.get_raw_creds("ts_optic_cred")
        #logger.debug("username=%s, apikey=%s" % (username, apikey))
        proxy_user, proxy_password = credManager.get_raw_creds("ts_proxy_cred")
        #logger.debug("proxy user=%s, password=%s" % (proxy_user, proxy_password))
        configManager = TSConfigManager(sessionKey=sessionKey, app=APP_NAME, owner=APP_OWNER)
        proxy_host, proxy_port = configManager.get_proxy()
        logger.debug("proxy_host=%s, proxy_port=%s" % (proxy_host, proxy_port))
        root_url = configManager.get_myconfig('url')
        logger.debug("url=%s"% root_url)
        dcid = configManager.get_myconfig('dcid')
        verify = root_url.find("api.threatstream.com") > 0
        upload_cloud = configManager.get_myconfig('upload_to_cloud')
        logger.info("upload to cloud is %s" % upload_cloud)
        client = OpticClient(username, apikey, root_url, verify=verify, proxy_host=proxy_host, proxy_port=proxy_port, proxy_user=proxy_user, proxy_password=proxy_password, upload_to_cloud=(upload_cloud in [1, "1"]))
        target = file_name
        if upload_cloud in [1, '1'] and (root_url.find("threatstream.com") > 0 or root_url.find("anomali.com")>0) and not file_name.endswith(".enc"):
            logger.info("encrypt file_name=%s" % file_name)
            print("encrypt file_name=%s" % file_name)
            target = encrypt(file_name, client)
        client.upload(target, timestamp, date_str, dcid=dcid, logger=logger)
        return target

def is_job_running():
    search_run_file = os.path.join(get_working_dir(), ".search_running")
    if os.path.exists(search_run_file):
        logger.info("File:%s exists" % search_run_file)
        return True
    else:
        return False

def wait_till_job_done():
    total_time = 10 * 60
    wait_time = 0
    interval = 30
    while is_job_running() and wait_time<total_time:
        logger.info("The previous run is not done, wait %d seconds" % interval)
        wait_time = wait_time + interval
        time.sleep(interval)
    if wait_time >= total_time:
        return False
    else:
        return True

def run(sessionKey, earliest, latest):
    logger.info("Ensure there is no other job running")
    if not wait_till_job_done():
        logger.warn("The previous job is still running. Skip this run")
        return
    try:
        logger.info("clean up working directory %s" % get_working_dir())
        cleanup(get_working_dir())
        with open(os.path.join(get_working_dir(), ".search_running"), "wb") as file_handler:
            pass
        logger.info("Start running saved search to generate summaries")
        return_code = run_searches(sessionKey, earliest, latest)
        if return_code == 0:
            logger.info("Start hashing summary files")
            hash_summaries()
            logger.info("Start creating tar ball")
            (file_name, uuid, date_str) = gen_bundle()
            logger.info("Uploading tar ball to Optic")
            if file_name:
                uploaded_filename = upload_file(sessionKey, file_name, uuid, date_str)
                logger.info("Remove the file:%s" % file_name)
                print("Remove the file:%s" % file_name)
                os.remove(file_name)
                if os.path.exists(uploaded_filename):
                    logger.info("Remove the file:%s" % uploaded_filename)
                    print("Remove the file:%s" % uploaded_filename)
                    os.remove(uploaded_filename)
        else:
            logger.error("Failed to run the search")
        logger.info("It's done")
    finally:
        os.remove(os.path.join(get_working_dir(), ".search_running"))

def convert_datetime_to_epoch(relative_time):
    tokens = relative_time.split('@')
    absolute_time = datetime.now()
    round_unit = 1
    for token in tokens:
        token = token.strip()
        if token.lower() == 'now':
            absolute_time = datetime.now()
        elif len(token) == 1:
            if token == 'm':
                round_unit = 60
            elif token == 'h':
                round_unit = 60*60
            elif token == 'd':
                round_unit = 24*60*60
            elif token == 'M':
                round_unit = 365/12*24*60*60
            else:
                raise Exception("Unsupported round unit %s" % relative_time)
        else:
            unit = token[-1]
            value = int(token[0:-1])
            if unit == "m": # minute
                absolute_time += timedelta(minutes=value)
            elif unit == "h": # hour
                absolute_time += timedelta(hours=value)
            elif unit == "d": # day
                absolute_time += timedelta(days=value)
            elif unit == 'M': # month
                absolute_time += timedelta(days=value*365/12)
            else:
                raise Exception("Unsupported time format %s" % relative_time)      
    epoch_time = time.mktime(absolute_time.timetuple())
    epoch_time = long(epoch_time)/round_unit*round_unit
    return long(epoch_time)

def get_span(span):
    unit = span[-1]
    value = int(span[0:-1])
    if unit == "m": # minute
        span_time = value * 60
    elif unit == "h": # hour
        span_time = value * 60 * 60
    return span_time

def save_checkpoint(start, end):
    with open(BACKFILL_CHECKPOINT, "wb") as handler:
        handler.write("earliest=%s\n" % start)
        handler.write("latest=%s\n" %end)

def load_checkpoint():
    if os.path.exists(BACKFILL_CHECKPOINT):
        with open(BACKFILL_CHECKPOINT, "rb") as handler:
            start = handler.readline()
            end = handler.readline()
            start_time = long(start[start.find('=')+1:].strip())
            end_time = long(end[end.find('=')+1:].strip())
            return (start_time, end_time)
    else:
        return (None, None)

def is_backfill_job_running():
    backfill_run_file = os.path.join(get_working_dir(), ".backfill_running")
    if os.path.exists(backfill_run_file):
        logger.info("File:%s exists" % backfill_run_file)
        return True
    else:
        return False

def start():
    sessionKey = get_sessionKey()
    configManager = TSConfigManager(sessionKey=sessionKey, app=APP_NAME, owner=APP_OWNER)
    backfill_enabled = configManager.get_myconfig("backfill_enabled")
    if backfill_enabled:
        if is_backfill_job_running():
            logger.info("The previous backfill job is still running. Skip this run")
            print("The previous backfill job is still running. Skip this run")
            return
        try:
            with open(os.path.join(get_working_dir(), ".backfill_running"), "wb") as file_handler:
                pass
            logger.info("backfill is enabled")
            logger.info("backfill checkpoint is %s" % BACKFILL_CHECKPOINT)
            backfill_span = configManager.get_myconfig("backfill_span")
            (start_time, end_time) = load_checkpoint()
            if not (start_time and end_time):
                backfill_earliest = configManager.get_myconfig("backfill_start_time")
                backfill_latest = configManager.get_myconfig("backfill_end_time")
                logger.info("backfill earliest:%s, backfill latest:%s, span:%s" %(backfill_earliest, backfill_latest, backfill_span))
                start_time = convert_datetime_to_epoch(backfill_earliest)
                end_time = convert_datetime_to_epoch(backfill_latest)
                logger.info("backfill epoch earliest:%d, latest:%d" %(start_time, end_time))
                save_checkpoint(start_time, end_time)
            else:
                logger.info("backfill checkpoint start_time:%s, end_time:%s" % (start_time, end_time))
            span = get_span(backfill_span)
            if end_time <= start_time:
                logger.info("backfill was done and exit the process")
                return
            while end_time > start_time:
                start = end_time - span
                s_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start))
                e_date = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time))
                logger.info("Backfill time earliest:%s, latest:%s, span:%s" % (s_date, e_date, span))
                run(sessionKey, start, end_time)
                save_checkpoint(start_time, start)
                end_time = start
                logger.info('sleep 10 seconds before next run')
                time.sleep(10)
            save_checkpoint(start_time, end_time)
            logger.info("Backfill job is done. Disable Backfill Summaries job")
            configManager.enable_saved_search("Backfill Summaries", 0)
        finally:
            os.remove(os.path.join(get_working_dir(), ".backfill_running"))
    else:
        logger.info("backfill is disabled")
        
if __name__ == '__main__':
    try:
        #logger.debug("sys.path=%s" % sys.path)
        ensure_dirs_exist([get_working_dir(), get_upload_dir()])
        start()
    except Exception as e:
        logger.error("Failed to generate summary bundle: %s" % str(e))
        logger.exception(e)
