import os, sys, tarfile
from settings import get_working_dir, get_app_home, get_iocdata_dir, APP_NAME, APP_OWNER
from logger import setup_logger
from cred_store import TSCredStoreManager
import splunk.Intersplunk
from ts_splunk_config import TSSplunkConfigManager
import util.splunk_access
from ae_client import AeClient

logger = setup_logger('ts_download_reports')
splunka = util.splunk_access.Splunk_access(logger)

class AeDownloadMgr(object):
    def __init__(self, username, apikey, **kwargs):
        self.username = username
        self.apikey = apikey
        self.kwargs = kwargs

    def download_reports(self):
        client = AeClient(splunka, self.username, self.apikey, 'reports', **self.kwargs)
        client.download_reports()
        
    def load_sample_reports(self):
        client = AeClient(splunka, self.username, self.apikey, 'reports', **self.kwargs)
        client.load_sample_reports()

if __name__ == '__main__':
    try:
        print('Start running ts_download_reports...')
        logger.info("Start running ts_download_reports")
        splunka.audit_log(type='download_tm_data', event='message:=Start running ts_download_reports.py')
        if not os.path.exists(get_working_dir()):
            logger.info("create the working directory %s" % (get_working_dir()))
            os.mkdir(get_working_dir())
        #get sessionKey
#         results, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
        settings = splunka.get_settings()
        
        #logger.debug(settings)
        sessionKey = settings["sessionKey"]
        
        #get optic credential
        credManager = TSCredStoreManager(sessionKey, APP_NAME, APP_OWNER, None)
        username, apikey = credManager.get_raw_creds("ts_optic_cred")
        #logger.debug("username=%s, apikey=%s" % (username, apikey))
        #download intels
        proxy_user, proxy_password = credManager.get_raw_creds("ts_proxy_cred")
        #logger.debug("proxy user=%s, password=%s" % (proxy_user, proxy_password))
        configManager = TSSplunkConfigManager(sessionKey=sessionKey, app=APP_NAME, owner=APP_OWNER, logger=logger, service=splunka.get_service())
        root_url = configManager.get_myconfig('url')
        logger.debug("url=%s"% root_url)
        proxy_host, proxy_port = configManager.get_proxy()
        logger.debug("proxy_host=%s, proxy_port=%s" % (proxy_host, proxy_port))

        logger.info("Start downloading reports")
        #hard code for now
        intelMgr = AeDownloadMgr(username, apikey, root_url=root_url, proxy_host=proxy_host, proxy_port=proxy_port, proxy_user=proxy_user, proxy_password=proxy_password, logger=logger)
        keywords = splunka.get_keywords()
        if 'sample' in keywords:
            logger.info("loading sample reports...")
            intelMgr.load_sample_reports()
        else:
            intelMgr.download_reports()
            
        print('The job is done.')
        logger.info("Finish downloading reports")
        splunka.audit_log(type='download_tm_data', event='message:=End running ts_download_reports.py')
                
    except Exception as e:
        logger.error("Failed to download reports: %s" % str(e))
        logger.exception(e)
