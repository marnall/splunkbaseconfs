# InterMapper for Splunk App - class to handle file accesses

import logging
from imUtils import logMethodEntry, logMethodExit, FILEPATHS
import os
from os.path import abspath
import codecs

class SplunkFileHandler(object):
    sessionNo = None
    exitHandler = None
    logger = None
    scrRuntime = None
    
    def __init__(self, exitHandler, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        self.sessionNo = sessionNo
        self.exitHandler = exitHandler
        self.logger = logging.getLogger('splunk.apps.intermapper.splunkfilehandler')
        self.logger.setLevel(logLevel)
        self.scrRuntime = scrRuntime
        
    def accessPath(self, path, mode):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        # appPath is defined as absolute path of InterMapper app root directory
        appPath = FILEPATHS['appPath']
        if mode == "r" or mode == "rb":  
            if abspath(path).startswith(appPath):
                try:
                    openFile = codecs.open(path, mode, encoding='utf-8-sig')
                    # use of codecs enforces binary mode
                    # ok since we always expect to write and read unix newlines
                    # utf-8-sig used to remove BOM from files if it appears
                except IOError as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Opening File Handle for %s\" message=\"IO Error when trying to open file for read access\"", self.sessionNo, path)
                except OSError as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Opening File Handle for %s\" message=\"OS Error when trying to open file for read access\"", self.sessionNo, path)
                else:
                    logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
                    return openFile
            else:
                self.logger.error("sessionNo=\"%i\" action=\"Checking absolute read path\" message=\"Error - Paths do not match.\"", self.sessionNo)
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
        
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            # exits with non-fatal error
        
        if mode == "w" or mode == "wb" or mode == "a" or mode == "ab":  
            if abspath(path).startswith(appPath):
                dir = os.path.dirname(path)
                if not os.path.exists(dir):
                    os.makedirs(dir)
                try:
                    openFile = open(path, mode)
                except IOError as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Opening File Handle for %s\" message=\"IO Error when trying to open file for write access\"", self.sessionNo, path)
                except OSError as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Opening File Handle for %s\" message=\"OS Error when trying to open file for write access\"", self.sessionNo, path)
                else:
                    logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
                    return openFile
            else:
                self.logger.error("sessionNo=\"%i\" action=\"Checking absolute write path\" message=\"Error - Paths do not match.\"", self.sessionNo)
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
        
            logMethodExit(start_time, 'Error')
            # exits with non-fatal error
        
        if mode == "d":
            if abspath(path).startswith(appPath):
                try:
                    os.remove(path)
                except IOError as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Delete File %s\" message=\"Error: %s\"", self.sessionNo, path, str(format(e)))
                except OSError as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Delete File %s\" message=\"Error: %s\"", self.sessionNo, path, str(format(e)))
                except Exception as e:
                    self.logger.error("sessionNo=\"%i\" action=\"Delete File %s\" message=\"Error: Unexpected error - %s\"", self.sessionNo, path, str(format(e)))
                else:
                    logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
                    return
            else:
                self.logger.error("sessionNo=\"%i\" action=\"Checking absolute delete path\" message=\"Error - Paths do not match.\"", self.sessionNo)
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
                self.exitHandler.crashOut()
        
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            # exits with non-fatal error
 
## end class SplunkFileHandler
