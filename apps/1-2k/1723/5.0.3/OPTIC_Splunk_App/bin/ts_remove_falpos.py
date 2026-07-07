import os, time, csv, datetime
from random import randint
from logger import setup_logger
import util.splunk_access
import util.kvs_manager
import settings

logger = setup_logger('ts_remove_falpos')
logger.debug('starting ts_remove_falpos ...')
splunka = util.splunk_access.Splunk_access(logger)
kvsm = splunka.get_kvsm()

def run():
    ioc_kv_stores = ('ts_iocs_ip',
                   'ts_iocs_domain',
                   'ts_iocs_url',
                   'ts_iocs_md5',
                   'ts_iocs_email'
                   )
    
    count = 0
    print('Remving false positive IOCs from kvs stores...')

    falpos_kvs = kvsm.get_kvs('ts_ioc_falsepos')
    iocs = [item.get('indicator') for item in falpos_kvs]
    for ioc in iocs:
        for kvs in ioc_kv_stores:
            delete_count = kvsm.delete_kvs_items_by_query(kvs, {'lookup_key_value' : ioc})
            if delete_count > 0:
                count += delete_count
                break

    print('%s Number of IOCs removed' % count)   
    logger.debug('%s IOCs removed' % count)          

if __name__ == "__main__":
    try:
        run()
    except BaseException as e:
        print('Error: %s' % e)
        logger.exception(e)
        raise