import httplib
import json
import logging
import logging.handlers
import operator
import re
import os
import splunk.util as util
import sys
import hashlib

if sys.platform == "win32":
    import msvcrt
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)

from splunk                         import RESTException
from splunk.persistconn.application import PersistentServerConnectionApplication
from splunk.clilib.bundle_paths     import make_splunkhome_path

## Setup the logger
def setup_logger():
    """
    Setup a logger for the search command
    """
   
    logger = logging.getLogger('cef_certificate_rest_handler')
    logger.propagate = False  # Prevent the log messages from being duplicated in the python.log file
    logger.setLevel(logging.INFO)
   
    file_handler = logging.handlers.RotatingFileHandler(make_splunkhome_path(['var', 'log', 'splunk', 'cef_certificate_rest_handler.log']), maxBytes=25000000, backupCount=5)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)
   
    logger.addHandler(file_handler)
   
    return logger

logger = setup_logger()
    

class CEFCertificateRestHandler(PersistentServerConnectionApplication):
   
    PERMITTED_EXTENSIONS = ['.arm', '.ca-bundle', '.cer', '.crt', '.der', '.p7b', '.p7s', '.pem', '.pfx']

    MAX_SIZE_READABLE = "5 MB"
    MAX_SIZE = 5 * 1024 * 1024 # 5 MB

    def __init__(self, command_line, command_arg):
        super(CEFCertificateRestHandler, self).__init__()

        self.cef_file_dir = make_splunkhome_path(['etc', 'apps', 'splunk_app_cef', 'auth'])
        
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
            logger.info('Handling %s request.', args['method'])
            method = 'handle_' + args['method'].lower()

            if method == 'handle_post':
                return operator.methodcaller(method, args)(self)
            elif method == 'handle_get':
                return operator.methodcaller(method, args)(self)
            else:
                return self.error(httplib.METHOD_NOT_ALLOWED, 'Invalid method for this endpoint')
        except RESTException as e:
            msg = 'RESTException: %s' % e
            return self.error(httplib.INTERNAL_SERVER_ERROR, msg)
        except Exception as e:
            msg = 'UnknownException: %s' % e
            return self.error(httplib.INTERNAL_SERVER_ERROR, msg)

    def handle_get(self, args):
        """Provide the list of certificates files.

        @return dict: A valid REST response
        """

        if(not os.path.isdir(self.cef_file_dir)):
            # Return OK to indicate that the request worked even though no files exist. An OK
            # is appropriate since the lack of files isn't a problem.
            return {
                    'status':  httplib.OK,
                    'payload': []
            }
        else:
            cert_files = [{"name": f} for f in os.listdir(self.cef_file_dir) if os.path.isfile(os.path.join(self.cef_file_dir, f))]
            logger.info('Output %r', cert_files)
            return {
                    'status':  httplib.OK,
                    'payload': cert_files
            }

    def handle_post(self, args):
        """Upload a certificate.

        @param  args: A dictionary of arguments to the REST call.

        @return dict: A valid REST response
        """
        # Retrieve arguments
        post_args      = dict(args.pop('form', []))

        cert_file_name = os.path.basename(post_args.get('file_name')) # Using os.path.basename to prevent directory traversal attacks
        cert_file      = post_args.get('file_contents')

        ## Make sure that the file appears to be a certificate
        _, cert_file_extension = os.path.splitext(cert_file_name)
        if(not cert_file_extension in CEFCertificateRestHandler.PERMITTED_EXTENSIONS):
            
            logger.warn('File extension is not a supported type; filename=%s', cert_file_name)

            return {
                    'status':  httplib.NOT_ACCEPTABLE,
                    'payload': {
                        'message': 'File extension is not a supported type; must be one of ' + ', '.join(CEFCertificateRestHandler.PERMITTED_EXTENSIONS)
                    }
            }

        try:
            os.makedirs(self.cef_file_dir)
        except OSError:
            # Directory already exists
            pass

        ## Make the full path of certificate file
        full_cert_file_name = make_splunkhome_path([self.cef_file_dir, cert_file_name])

        ## Determine if the file already exists
        if(os.path.isfile(full_cert_file_name)):
            logger.info('The certificate file already existed; orig_filename=%s',  cert_file_name)

            return {
                    'status':  httplib.NOT_ACCEPTABLE,
                    'payload': {
                        'message': 'File with this name already exists'
                    }
            }

        ## Check the size of the data provided
        if len(cert_file.encode('utf8')) > CEFCertificateRestHandler.MAX_SIZE:
            logger.info('The certificate file is too large; orig_filename=%s, size=%i',  cert_file_name, len(cert_file.encode('utf8')))

            return {
                    'status':  httplib.NOT_ACCEPTABLE,
                    'payload': {
                        'message': 'File is too large; must be less than ' + CEFCertificateRestHandler.MAX_SIZE_READABLE
                    }
            }

        ## Open the file
        with open(full_cert_file_name, 'w') as cert_file_fp:
            cert_file_fp.write(cert_file)
            logger.info('Successfully wrote out the certificate file; orig_filename=%s, full_path=%s', cert_file_name, full_cert_file_name)

        ## Return the information about the file that was written out
        return {
                'status':  httplib.OK,
                'payload': {
                    'filename': cert_file_name,
                    'stored_filename' : os.path.basename(full_cert_file_name)
                }
        }
        
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
