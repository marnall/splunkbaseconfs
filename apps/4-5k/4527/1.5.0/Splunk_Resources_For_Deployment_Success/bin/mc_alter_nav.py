# this script alters nav bar to include extend app's dashboards

import sys, os, time, json
import splunk.rest as rest
import logging, logging.handlers

LOG_LEVEL = logging.INFO
LOG_FILE_NAME = "mchealthcheck.log"

MC_NAV_ENDPOINT = '/servicesNS/nobody/splunk_monitoring_console/data/ui/nav/default?output_mode=json'

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

    logger.propagate = False
    return logger

def update_nav_bar():
    session_key = sys.stdin.read()

    response, server_response = rest.simpleRequest(MC_NAV_ENDPOINT, session_key)
    data = json.loads(server_response)
    nav = data["entry"][0]["content"]["eai:data"]

    if ("Resources for Deployment Success" in nav):
        logger.info("nav menu already modified, no action")
    else:
        logger.info("nav menu needs modification, adding")

        post = {}
        post["eai:data"] = nav.replace('</nav>', 
'''
  <collection label="Resources for Deployment Success">
    <view name="essentials_trend" />
    <view name="export_share" />
  </collection>
</nav>
'''
        )
        response, server_response = rest.simpleRequest(MC_NAV_ENDPOINT, sessionKey=session_key, method='GET', postargs=post, raiseAllErrors=False)

        error_detail = "ok"
        if response.status != 200:
            error_detail = server_response
        logger.info('calling endpoint="%s", returned status=%s, detail="%s"' % (str(MC_NAV_ENDPOINT), response.status, error_detail))  


if __name__ == '__main__':
    logger = setup_logging()
    logger.info('starting..')
    eStart = time.time()

    try:
        update_nav_bar()
    except:
        logger.error('Cannot update MC nav bar.')
        raise
    finally:
        logger.info('exiting, execution duration=%s seconds' % (time.time() - eStart))
