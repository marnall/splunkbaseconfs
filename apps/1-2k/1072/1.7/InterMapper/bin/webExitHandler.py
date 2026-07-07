# InterMapper for Splunk App - class to handle script exit and cleanup for splunkweb scripts

from exitHandler import SimpleExitHandler
from mako import exceptions #@UnresolvedImport
import logging

class LoadMapException(exceptions.MakoException):
    pass

class WebExitHandler(SimpleExitHandler):
    
    def __init__(self, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        SimpleExitHandler.__init__(self, sessionNo, logLevel, scrRuntime)
                    
    def crashOut(self):
        SimpleExitHandler.crashOut(self)
        raise LoadMapException()
