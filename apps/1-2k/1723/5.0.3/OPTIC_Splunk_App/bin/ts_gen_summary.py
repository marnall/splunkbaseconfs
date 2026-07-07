import os, os.path, sys, traceback, time
import shutil
import fnmatch
import splunk.clilib.bundle_paths as bundle_paths
import splunk.Intersplunk
from logger import setup_logger
from settings import APP_NAME, APP_OWNER, get_app_home, get_platform, get_working_dir, get_upload_dir, get_conf_file, get_csv_dir, get_mgmt_port, get_splunk_home
from summary.ts_searcher import Searcher
from summary.ts_hash import SummaryHash
from summary.ts_bundle import SummaryConfig, SummaryBundle
from summary.optic_client2 import OpticClient
from cred_store import TSCredStoreManager
from ts_config import TSConfigManager

OWNER = APP_OWNER
SAVED_SEARCHES_DICT={"Generating DEST Summary":"dest_summary:dest",
                     "Generating SRC Summary":"src_summary:src",
                     "Generating Network Summary":"src_dest_summary:src|dest",
                     "Generating Web Summary":"url_summary:src|dest|url",
                     "Generating Filehash Summary":"filehash_summary:src|file_hash|file_name",
                     "Generating Email Summary":"email_summary:sender|receiver"}
logger = setup_logger('ts_summary')

def ensure_dirs_exist(dirs):
    for dir in dirs:
        if not os.path.exists(dir):
            os.mkdir(dir)

def cleanup(dir, file_pattern):
    for root, dirs, files in os.walk(dir):
        for filename in fnmatch.filter(files, file_pattern):
            src = os.path.join(root, filename)
            os.remove(src)

def get_sessionKey():
    results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    logger.debug(settings)
    sessionKey = settings["sessionKey"]
    return sessionKey

def run_searches(sessionKey):
    searcher = Searcher(sessionKey, app=APP_NAME, owner=OWNER, port=get_mgmt_port(), logger=logger)
    configManager = TSConfigManager(sessionKey=sessionKey, app=APP_NAME, owner=APP_OWNER, port=get_mgmt_port())
    saved_searches = configManager.get_configured_saved_searches()
    logger.info("start saved searches: %s" % saved_searches)
    print("start saved searches: %s" % saved_searches)
    enabled_saved_searches = searcher.getEnabledSavedSearchNames(saved_searches)
    jobs = searcher.run(enabled_saved_searches)
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
        print("All saved searches (%s) failed" % saved_searches)
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
                if os.path.exists(src):
                    shutil.move(src, get_working_dir())
                else:
                    logger.warn("Search Results: %s does not exist" % src)
    hash_type, error_rate = _get_hash_conf()
    for root, dirs, files in os.walk(get_working_dir()):
        for filename in files:
            if filename.endswith('summary.csv'):
                src = os.path.join(root, filename)
                if os.path.getsize(src) > 0:
                    hash_file = SummaryHash(src, hash_type, error_rate=error_rate, logger=logger).gen_hash()
                else:
                    logger.info("Skip hashing empty file:%s" % src)
                    print("Skip hashing empty file:%s" % src)

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
        configManager = TSConfigManager(sessionKey=sessionKey, app=APP_NAME, owner=APP_OWNER, port=get_mgmt_port())
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

def upload_files_from_previous_runs(sessionKey):
    for root, dirs, files in os.walk(get_upload_dir()):
        for filename in files:
            try:
                logger.info("Re-send file: %s" % filename)
                print("Re-send file: %s" % filename)
                if filename.startswith("ts_summary_") and filename.endswith("tar.gz"):
                    s = len("ts_summary_")
                    e = len(".tar.gz")
                    uuid_date = filename[s:-e]
                    tokens = uuid_date.split("_")
                    timestamp = tokens[0]
                    date_str = tokens[1]
                    uploaded_filename = upload_file(sessionKey, os.path.join(root, filename), timestamp, date_str)
                    os.remove(os.path.join(root, filename))
                    if os.path.exists(uploaded_filename):
                        os.remove(uploaded_filename)
            except Exception as e:
                logger.info("Failed to upload file: %s" % filename)
                print("Failed to upload file: %s" % filename)
                logger.exception(e)
                print(traceback.format_exc())

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
    interval = 10
    while is_job_running() and wait_time<total_time:
        logger.info("The previous run is not done, wait %d seconds" % interval)
        wait_time = wait_time + interval
        time.sleep(interval)
    if wait_time >= total_time:
        return False
    else:
        return True

def start():
    try:
        with open(os.path.join(get_working_dir(), ".search_running"), "wb") as file_handler:
            pass
        sessionKey = get_sessionKey()
        logger.info("Start running saved search to generate summaries")
        print("Start running saved search to generate summaries")
        return_code = run_searches(sessionKey)
        if return_code == 0:
            logger.info("Start hashing summary files")
            print("Start hashing summary files")
            hash_summaries()
            logger.info("Start creating tar ball")
            print("Start creating tar ball")
            (file_name, uuid, date_str) = gen_bundle()
            logger.info("Uploading tar ball to Optic")
            print("Uploading tar ball to Optic")
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
            print("Failed to run the search")
        upload_files_from_previous_runs(sessionKey)
        logger.info("It's done")
        print("It's done")
    finally:
        os.remove(os.path.join(get_working_dir(), ".search_running"))
        cleanup(get_upload_dir(), '*.enc')

if __name__ == '__main__':
    try:
        logger.debug("sys.path=%s" % sys.path)
        print("sys.path=%s" % ":".join(sys.path))
        logger.info("SPLUNK_HOME: %s, APP_HOME: %s" % (get_splunk_home(), get_app_home()))
        print("SPLUNK_HOME: %s, APP_HOME: %s" % (get_splunk_home(), get_app_home()))
        ensure_dirs_exist([get_working_dir(), get_upload_dir()])
        logger.info("Ensure previous run is done")
        print("Ensure previous run is done")
        if not wait_till_job_done():
            logger.warn("The previous job is still running. Skip this run")
            print("The previous job is still running. Skip this run")
            sys.exit()
        logger.info("clean up working directory %s" % get_working_dir())
        print("clean up working directory %s" % get_working_dir())
        cleanup(get_working_dir(), '*summary.csv*')
        start()
    except Exception as e:
        logger.error("Failed to generate summary bundle: %s" % str(e))
        logger.exception(e)
        print(traceback.format_exc())
