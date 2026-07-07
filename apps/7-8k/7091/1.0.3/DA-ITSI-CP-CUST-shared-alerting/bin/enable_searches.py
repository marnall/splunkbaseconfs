import sys, os
import json
import logging
import logging.handlers
import splunk.rest as rest

def log(msg, *args):
    sys.stderr.write(msg + " ".join([str(a) for a in args]) + "\n")

def setup_logger(level):
     logger = logging.getLogger('my_search_command')
     logger.propagate = False # Prevent the log messages from being duplicated in the python.log file
     logger.setLevel(level)
     file_handler = logging.handlers.RotatingFileHandler(os.environ['SPLUNK_HOME'] + '/var/log/splunk/shared_alerting.log', maxBytes=10000000, backupCount=1)
     formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
     file_handler.setFormatter(formatter)
     logger.addHandler(file_handler)
     return logger
 
logger = setup_logger(logging.INFO)

def update_searches(payload):
    app = payload.get('app')
    search_name = payload.get('search_name')
    session_key = payload.get('session_key')

    if search_name == 'es_is_installed':
        log("std out ES is installed")
        logger.info("ES is installed")
        uri = '/servicesNS/nobody/'+app+'/saved/searches/es_share_itsi'
        postargs = {'is_scheduled': '1'}
        serverresponse, servercontent = rest.simpleRequest(uri, sessionKey=session_key, postargs=postargs)

        if serverresponse['status'] != '200':
            logger.warn("request error")
            raise Exception("Server response indicates that the request failed")
        else:
            logger.info("enabled es search to share with itsi")

        uri = '/servicesNS/nobody/'+app+'/saved/searches/es_is_installed'
        postargs = {'is_scheduled': '0'}
        serverresponse, servercontent = rest.simpleRequest(uri, sessionKey=session_key, postargs=postargs)

        if serverresponse['status'] != '200':
            logger.warn("request error")
            raise Exception("Server response indicates that the request failed")
        else:
            logger.info("unscheduled search checking for es")

        uri = '/servicesNS/nobody/'+app+'/saved/searches/itsi_is_installed'
        postargs = {'is_scheduled': '0'}
        serverresponse, servercontent = rest.simpleRequest(uri, sessionKey=session_key, postargs=postargs)

        if serverresponse['status'] != '200':
            logger.warn("request error")
            raise Exception("Server response indicates that the request failed")
        else:
            logger.info("unscheduled search checking for itsi")

    else:
        logger.info("ITSI is installed")
        uri = '/servicesNS/nobody/'+app+'/saved/searches/itsi_share_es'
        postargs = {'is_scheduled': '1'}
        serverresponse, servercontent = rest.simpleRequest(uri, sessionKey=session_key, postargs=postargs)

        if serverresponse['status'] != '200':
            logger.warn("request error")
            raise Exception("Server response indicates that the request failed")
        else:
            logger.info("enabled itsi search to share with es")

        uri = '/servicesNS/nobody/'+app+'/saved/searches/es_is_installed'
        postargs = {'is_scheduled': '0'}
        serverresponse, servercontent = rest.simpleRequest(uri, sessionKey=session_key, postargs=postargs)

        if serverresponse['status'] != '200':
            logger.warn("request error")
            raise Exception("Server response indicates that the request failed")
        else:
            logger.info("unscheduled search checking for es")

        uri = '/servicesNS/nobody/'+app+'/saved/searches/itsi_is_installed'
        postargs = {'is_scheduled': '0'}
        serverresponse, servercontent = rest.simpleRequest(uri, sessionKey=session_key, postargs=postargs)

        if serverresponse['status'] != '200':
            logger.warn("request error")
            raise Exception("Server response indicates that the request failed")
        else:
            logger.info("unscheduled search checking for itsi")

    return 0

def validate_payload(payload):
    if not 'configuration' in payload:
        logger.critical("FATAL Invalid payload, missing 'configuration'")
        return False
    config = payload.get('configuration')
    channel = config.get('channel')

    if channel and (channel[0] != '#' and channel[0] != '@'):
        # Only warn here for now
        logger.warning("WARN Validation warning: Parameter `channel` \"%s\" should start with # or @" % channel)

    return True

def main():
    #log("INFO Running python %s" % (sys.version_info[0]))
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        payload = json.loads(sys.stdin.read())
        if not validate_payload(payload):
            sys.exit(2)
        result = update_searches(payload)
        if result == 0:
            logger.info("INFO Successfully setup searches")
        else:
            logger.critical("FATAL Alert action failed")
        sys.exit(0)

if __name__ == '__main__':
    main()

