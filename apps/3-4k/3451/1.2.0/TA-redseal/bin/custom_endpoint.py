import splunk
import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
from splunk.util import safeURLQuote
import six

APPNAME = 'TA-redseal'

def setup_logger(level):
    """
    Setup a logger for the REST handler.
    """
    logger = logging.getLogger('splunk.appserver.%s.controllers.configuration' % APPNAME)
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(level)
    file_handler = logging.handlers.RotatingFileHandler(
        make_splunkhome_path([os.environ["SPLUNK_HOME"],'var', 'log', 'splunk', 'redsealirScriptController.log']), maxBytes=20000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger(logging.DEBUG)

def manual_make_url(url, _qs):
    qargs = '?' + '&'.join([ '%s=%s' % (safeURLQuote(six.text_type(k), safe=''), safeURLQuote(six.text_type(v), safe='')) for k, v in _qs])
    return url + qargs

def getRedSealServer(sessionKey):
    servername = None
    entity = splunk.entity.getEntity('/data/inputs', 'redsealModInput', sessionKey=sessionKey, owner='nobody', sort_dir='asc', sort_key='name')

    if (entity != None):
        #  Extract Redseal servername
        servername = str(entity.properties.get('redsealServer'))

    return servername

class Receive(splunk.rest.BaseRestHandler):

    def handle_GET(self):

        # URL format in browser to call Rest API
        # https://localhost:8000/en-US/splunkd/__raw/services/redseal?Username=tester
        # https://localhost:8089/services/redseal?Username=tester


        hostname = self.request['query']['hostvalue']
        type = self.request['query']['type']
        sid = self.request['query']['sid']
        namespace = self.request['query']['namespace']
        sessionKey = self.sessionKey

        url = '/'

        logger.debug('hostname:' + hostname)


        # TESTING ONLY
        # value =  None
        value = getRedSealServer(sessionKey)
        logger.debug("Reseal Server: %s" % value)

        if ((value == '' or value is None)):
            args = None
            url = '/app/%s/error' % APPNAME

        else:
            args = [('source', hostname)]

            #url = 'https://<server>/redseal/a/incidentResponse/queryResult'
            if (type == 'IR'):
                url = 'https://' + value +'/redseal/a/incidentResponse/queryResult'
                args = [('source', hostname)]

            # elif (type=='SIA'):
            #     # type SIA
            #     dest = destinations
            #     src = sources

                # #url = 'https://<server>/redseal/a/securityImpact/queryResult?sources=$src$&destinations=$dest$
                # url = 'https://' + value +'/redseal/a/securityImpact/queryResult'
                # args = [('sources', src), ('destinations',dest)]
            else:
                logger.error("crossLaunch | Type param is not set.");


        logger.debug("crossLaunch | url:" + url)
        if not url.startswith('/'):
            redirect_url = manual_make_url(url, args)
        else:
            try:
                redirect_url = self.make_url(url, _qs=args, encode=False) # bubbles
            except:
                redirect_url = self.make_url(url, _qs=args) # pre-bubbles


        # setting response code for browser re-direct
        self.response.setStatus(303)
        self.response.setHeader('Content-type', 'text/html')
        logger.debug("Redirect_URL:"+redirect_url)
        self.response.setHeader('Location', redirect_url)

    handle_POST = handle_GET


