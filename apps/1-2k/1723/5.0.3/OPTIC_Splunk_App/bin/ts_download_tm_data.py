import os, sys, tarfile
from settings import get_working_dir, get_app_home, get_iocdata_dir, APP_NAME, APP_OWNER
from logger import setup_logger
from cred_store import TSCredStoreManager
import splunk.Intersplunk
from ts_splunk_config import TSSplunkConfigManager
import util.splunk_access
from ae_client import AeClient, IOC_TYPES
import ts.lookup_iocs

logger = setup_logger('ts_download_tm_data')
DEST_TAR_FILE = 'ts_optic_iocs.tar'
splunka = util.splunk_access.Splunk_access(logger)
kvsm = splunka.get_kvsm()

def load_iocs_from_lookup():
    logger.debug('loading iocs from lookup ...')
    ioc_actor_map = {}
    count = 0
    for t in IOC_TYPES:
        iocs = ts.lookup_iocs.Iocs(t, kvsm, logger, False).load_iocs()
        count += len(iocs)
        for ioc in iocs:
            actor = ioc.get('actor')
            if actor:
                ioc_actor_map[ioc.get('id')] = actor
    logger.debug('%s iocs loaded from lookup' % count)
    return count, ioc_actor_map

class AeDownloadMgr(object):
    def __init__(self, username, apikey, **kwargs):
        self.tar_url = os.path.join(get_working_dir(), DEST_TAR_FILE)
        self.username = username
        self.apikey = apikey
        self.kwargs = kwargs

    def download_tm_data(self, ioc_actor_map=None):
        client = AeClient(splunka, self.username, self.apikey, **self.kwargs)
        client.download_tm_data(ioc_actor_map)
        
    def load_sample_tm_data(self, ioc_actor_map=None):
        client = AeClient(splunka, self.username, self.apikey, **self.kwargs)
        client.load_sample_tm_data(ioc_actor_map)

if __name__ == '__main__':
    try:
        print('Start running ts_download_tm_data...')
        logger.info("Start running ts_download_tm_data")
        
        splunka.audit_log(type='download_tm_data', event='message:=Start running ts_download_tm_data.py')
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

        logger.info("Start downloading thread model data")
        #hard code for now
        intelMgr = AeDownloadMgr(username, apikey, root_url=root_url, proxy_host=proxy_host, proxy_port=proxy_port, proxy_user=proxy_user, proxy_password=proxy_password, logger=logger)
        keywords = splunka.get_keywords()
        if 'sample' in keywords:
            count, ioc_actor_map = load_iocs_from_lookup()
            logger.info("load_iocs_from_lookup, result count: %s" % count)
            logger.info("loading sample data...")
            intelMgr.load_sample_tm_data(ioc_actor_map)
        else:
            if kvsm.get_kvs('tm_tipreport') and not kvsm.get_kvs('ts_runtime_states'):
                msg = 'Removing sample thread model and IOC data...'
                logger.info(msg)
                print(msg)
                kvs_list = ['tm_tipreport', 'ts_iocs_ip', 'ts_iocs_domain', 'ts_iocs_url', 'ts_iocs_email', 'ts_iocs_md5']
                for kvs in kvs_list:
                    kvsm.delete_kvs(kvs)
            count, ioc_actor_map = load_iocs_from_lookup()
            logger.info("load_iocs_from_lookup, result count: %s" % count)
            try:
                intelMgr.download_tm_data(ioc_actor_map)
            except BaseException as e:
                logger.exception(e)
            finally:
                if not kvsm.get_kvs('tm_tipreport'):
                    msg = 'No thread model and IOC data from AE reports server - loading sample data instead...'
                    logger.info(msg)
                    print(msg)
                    intelMgr.load_sample_tm_data(ioc_actor_map)

        print('The job is done.')
        logger.info("Finish downloading thread model data")
        splunka.audit_log(type='download_tm_data', event='message:=End running ts_download_tm_data.py')
                
    except Exception as e:
        logger.error("Failed to download thread model data: %s" % str(e))
        logger.exception(e)
