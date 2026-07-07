try:
    import http.client as http_client
except ImportError:
    import httplib as http_client  # noqa
import json
import logging
import logging.handlers
import operator
import splunk.util as util
import sys

if sys.platform == "win32":
    import os
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk import RESTException
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'splunk_app_cef', 'lib']))
from cef_search_generator import CEFSearchGenerator,CEFSearchException


# Setup the logger
def setup_logger():
    """
    Setup a logger for the search command
    """

    logger = logging.getLogger('cef_search_rest_handler')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.INFO)

    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'cef_search_rest_handler.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)

    return logger


logger = setup_logger()


class CEFSearchRestHandler(PersistentServerConnectionApplication):

    def __init__(self, command_line, command_arg):
        super(CEFSearchRestHandler, self).__init__()

    def handle(self, args):
        """Main function for REST call.

        @param args:  A JSON string representing a dictionary of arguments to the REST call.

        @return dict: A valid REST response.

        - Routing of GET, POST, etc. happens here.
        - All exceptions should be caught here.
        """
        logger.debug('ARGS: %s', args)
        args = json.loads(args)

        try:
            logger.info('Handling %s request.' % args['method'])
            method = 'handle_' + args['method'].lower()
            if method == 'handle_post':
                return operator.methodcaller(method, args)(self)
            else:
                return self.error(http_client.METHOD_NOT_ALLOWED, 'Invalid method for this endpoint')
        except CEFSearchException as e:
            msg = 'CEFException: %s' % e
            return self.error(http_client.BAD_REQUEST, msg)
        except RESTException as e:
            msg = 'RESTException: %s' % e
            return self.error(http_client.INTERNAL_SERVER_ERROR, msg)
        except Exception as e:
            msg = 'UnknownException: %s' % e
            return self.error(http_client.INTERNAL_SERVER_ERROR, msg)

    def handle_post(self, args):
        """Generate a CEF search from JSON specification.

        @param  args: A dictionary of arguments to the REST call.

        @return dict: A valid REST response
        """
        # Retrieve arguments
        session_key = args['session']['authtoken']
        post_args = dict(args.pop('form', []))
        spec = post_args.get('spec')
        preview_mode = util.normalizeBoolean(post_args.get('preview_mode', False))

        # Generate search
        srch, parses = CEFSearchGenerator.get_cef_search(spec, session_key, preview_mode=preview_mode)

        # Return search
        if srch:
            return {
                'status':  http_client.OK,
                'payload': {
                    'search': srch,
                    'parses': parses
                }
            }
        else:
            raise CEFSearchException('Search generation resulted in empty search')

    @staticmethod
    def error(status, msg):
        """
        Return error.

        @param status: An integer to be returned as the HTTP status code.
        @param msg:    A message describing the problem (a string)

        @return dict:  A valid REST response
        """
        logger.exception(msg)
        return {'status': status, 'payload': msg}
