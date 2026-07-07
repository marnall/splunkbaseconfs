import sys
import os
import re
import base64
import json
import logging, logging.handlers
import splunk

from base64 import b64decode, urlsafe_b64encode
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

def setup_logging():
    logger = logging.getLogger('splunk.jwt-decoder')    
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = "jwt-decoder.log"
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = "%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s"
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a') 
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

logger = setup_logging()
@Configuration()

class JWTCommand(StreamingCommand):
    """
    Decode JWT token
   
     | jwt field=<field> [secret=<secret>] [wrap=(true|false)]
     """

    def decode_base64(self, data, altchars=b'+/'):
        missing_padding = len(data) % 4
        if missing_padding:
            data = f"{data}{'=' * ((4 - len(data) % 4) % 4)}"
        return b64decode(data, altchars).decode("utf-8")

    field  = Option(name='field',  require=True)
    secret = Option(name='secret',   require=False, default=None)
    wrap = Option(name='wrap',   require=False, default=True, validate=validators.Boolean())
    filter = Option(name='filter',   require=False, default=False, validate=validators.Boolean())
    debug = Option(name='debug', require=False, default=False, validate=validators.Boolean())

    def stream(self, events):
        
        module = sys.modules['base64']

        # Only load hashing libraries if we are validating signature
        if self.secret is not None:
            import hashlib
            import hmac

        for event in events:
            # Set default value in case parsing fails for some reason to ensure Splunk sees a value
            event["jwt"] = None

            # If filtering enabled, skip events which do not contain the requested field
            if self.filter and not self.field in event :
                continue

            try:
                if self.field in event.keys():
                    raw = event[self.field]
                    # If filtering enabled, skip events where supplied field is empty
                    if self.filter and not raw:
                        continue

                    # Basic JWT structure. The top level "jwt" property ensures that spath output will result 
                    # in fully qualified names, e.g. jwt.header.alg or jwt.payload.name.
                    jwt = {
                        "jwt": {
                            "header": {},
                            "payload": {},
                        }
                    };

                    # Attempt to pparse JWT from authoriazation header, if present
                    if type(raw) in (list, tuple):
                        for item in raw:
                            match = re.search(r'^Authorization: Bearer (.*)$', item, re.MULTILINE)
                            if(match):
                                raw = str(match.groups()[0])
                    else:
                        match = re.search(r'^Authorization: Bearer (.*)$', raw, re.MULTILINE)
                        if(match):
                            raw = str(match.groups()[0])

                    # Split JWT into header, payload and signature components
                    if '.' in raw:
                        token = raw.split('.')
                        try:
                            jwt["jwt"]["header"] = json.loads(self.decode_base64(token[0], "-_"));
                            jwt["jwt"]["payload"] = json.loads(self.decode_base64(token[1], "-_"));
                        except Exception as e:
                            if self.debug:
                                raise Exception("Error decoding JWT: ", e, token)    
                            raise Exception("Error decoding JWT: ", e)
                        
                        # If a secret was provided, validate the signature and inject the results
                        if self.secret is not None:
                            try:
                                payload = bytes(token[0] + '.' + token[1]).encode('utf-8')
                                sec = bytes(self.secret).encode('utf-8')
                                signature = urlsafe_b64encode(hmac.new(sec, payload, digestmod=hashlib.sha256).digest())
                                valid = (signature == urlsafe_b64encode(self.decode_base64(token[2], '-_')))

                                if valid:
                                    jwt["jwt"]["signature"] = "Valid"
                                else:
                                    jwt["jwt"]["signature"] = "Invalid"

                            except Exception as e:
                                raise Exception("Error validating secret: ", e)

                        # Allow user to disable wrapping if they need to reference properties via spath without jwt prefix
                        if self.wrap:
                            event["jwt"] = json.dumps(jwt)
                        else:
                            event["jwt"] = json.dumps(jwt["jwt"])
                else:
                    pass

            except Exception as e:
                logger.fatal(e)
                if self.debug:
                    raise e

            yield event

dispatch(JWTCommand, sys.argv, sys.stdin, sys.stdout, __name__)
