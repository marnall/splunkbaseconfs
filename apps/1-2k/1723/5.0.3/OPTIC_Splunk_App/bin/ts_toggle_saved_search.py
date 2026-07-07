import collections
from logger import setup_logger
import splunk.Intersplunk
import util.splunk_access
import util.kvs_manager

logger = setup_logger('ts_toggle_saved_search', True)
splunka = util.splunk_access.Splunk_access(logger)

def run():
    logger.debug('ts_toggle_saved_search.py starts ...')
    print()
    options = splunka.get_options()
    logger.info('Running ts_toggle_saved_search: options: %s' % options)
    service = splunka.get_service()
    
    saved_search_name = 'Generating and Uploading Summaries'
    enable = True
    if 'saved_search' in options:
        saved_search_name = options['saved_search']
        
    if 'action' in options:
        action = options['action']
        enable = action != 'disable'

    search = service.saved_searches[saved_search_name]
    search.enable() if enable else search.disable()
    msg = 'saved_search "%s" is %s' % (saved_search_name, 'enabled' if enable else 'disabled')
    logger.info(msg)
    print(msg)
    
if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        logger.error("Running ts_toggle_saved_search.py failed.")
        logger.exception(e)
        raise
