import collections
from logger import setup_logger
import splunk.Intersplunk
import util.splunk_access
import util.kvs_manager

logger = setup_logger('ts_clear_kvs')
splunka = util.splunk_access.Splunk_access(logger)
kvsm = util.kvs_manager.Kvs_manager(splunka, logger)

def run():
    logger.debug('run starts ...')
   
    keywords = splunka.get_keywords()
    logger.debug('keywords: %s' % keywords)
    if not keywords:
        return
    
    collection_name = keywords[0]
    logger.debug('collection_name: %s' % collection_name)
    kvsm.delete_kvs(collection_name)
    splunk.Intersplunk.outputResults([collections.OrderedDict({'action': 'clear kvs: %s' % collection_name})])

if __name__ == "__main__":
    run()
