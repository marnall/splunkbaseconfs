# InterMapper for Splunk App - class to handle scheduled script exit and cleanup

import logging
from imUtils import logMethodEntry, logMethodExit, returnParent, FILEPATHS
import os
from os.path import join, exists, split
import __main__ as main

class SimpleExitHandler(object):
    sessionNo = None
    logger = None
    scrRuntime = None
    
    def __init__(self, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        self.sessionNo = sessionNo
        self.logger = logging.getLogger('splunk.apps.intermapper.exithandler')
        self.logger.setLevel(logLevel)
        self.scrRuntime = scrRuntime
        
    def cleanExit(self):
        self.logger.info("sessionNo=\"%i\" parentFunction=\"%s\" message=\"Script exiting normally.\"", self.sessionNo, returnParent())
        self.clearErrors()
        
    def clearErrors(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        if exists(FILEPATHS['errFile']):
            try:
                os.remove(FILEPATHS['errFile'])
            except IOError as e:
                self.logger.error("sessionNo=\"%i\" action=\"Delete ErrLog\" message=\"Error: Unable to delete ErrLog\" error=\"%s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            except Exception as e:
                self.logger.error("sessionNo=\"%i\" action=\"Delete ErrLog\" message=\"Error: Unexpected Error\" error=\"%s\"", self.sessionNo, str(format(e)))
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
            else:
                self.logger.info("sessionNo=\"%i\" action=\"Delete ErrLog\" message=\"ErrLog Deleted\"", self.sessionNo)
                logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
        else:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
            
    def fatalErrorHandler(self, error, errorMessage):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)        
        try:
            with open(join(FILEPATHS['outputHtml'], "immapDefault.html"), 'w') as htmlOut:
                if error == "sectionError":
                    htmlOut.write('<H2>Errors Encountered</H2><META HTTP-EQUIV="REFRESH" CONTENT="10"/>\n')
                    htmlOut.write('<center><H3>Error: Please ensure settings.conf exists in $SPLUNK_HOME/etc/apps/InterMapper/local/<H3></center><br/>')
                    htmlOut.write('<center><H3>Installation may be corrupt. Please either reinstall or replace settings.conf from App file.<H3></center>')
                elif error == "genError":
                    htmlOut.write('<H1>Errors Encountered</H1><META HTTP-EQUIV="REFRESH" CONTENT="10"/>\n')
                    htmlOut.write('<center><H3>Error: ' + errorMessage + '<H3></center>')
                elif error == "optionError":
                    htmlOut.write('<H2>Errors Encountered</H2><META HTTP-EQUIV="REFRESH" CONTENT="10"/>\n')
                    htmlOut.write('<center><H3>Error: Please ensure settings.conf exists in $SPLUNK_HOME/etc/apps/InterMapper/local/<H3></center><br/>')
                    htmlOut.write('<center><H3>Configuration file may be corrupt. Please either reinstall or replace settings.conf from App file.<H3></center>')
                elif error == "emptyValue":
                    htmlOut.write('<H2>Errors Encountered</H2><META HTTP-EQUIV="REFRESH" CONTENT="10"/>\n')
                    htmlOut.write('<center><H3>Error: Please ensure all configuration options have been completed from the setup screen<H3></center><br/>')
                    htmlOut.write('<center><H3>Once completed the first time setup will continue automatically.<H3></center>')
                    htmlOut.write('<center><H3>Select "Configure App" from the navigation bar above to quickly access the setup screen<H3></center>')
                elif error == "connError":
                    htmlOut.write('<H1>Errors Encountered</H1><META HTTP-EQUIV="REFRESH" CONTENT="10"/>\n')
                    htmlOut.write('<center><H3>Error: Unable to connect to Intermapper Server.<H3></center><br/>')
                    htmlOut.write('<center><H3>Error message returned by script;<H3></center>')
                    htmlOut.write('<center><H3>' + errorMessage + '<H3></center><br/>')
                    htmlOut.write('<center><H3>Common Error Messages and their meanings:<H3></center>')
                    htmlOut.write('<center>No route to host - Incorrect IP:PORT entered during App setup or firewall between servers</center><br/>')
                    htmlOut.write('<center>Connection refused - Incorrect PORT provided during App setup or no port provided<H3></center>')
                    htmlOut.write('<center>EOF occurred in violation of protocol - HTTPS enabled in setup when only HTTP access is available<H3></center>')
                    htmlOut.write('<center>Connection reset by peer - Possible mismatch of HTTPS/HTTP and PORT options.<H3></center>')
                    htmlOut.write('<center>No connection could be made because the target machine actively refused it - Check Intermapper IP:PORT detail is correct and for open firewall ports.<H3></center>')
                elif error == "connErrorTwo":
                    htmlOut.write('<H1>Errors Encountered</H1><META HTTP-EQUIV="REFRESH" CONTENT="10"/>\n')
                    htmlOut.write('<center><H3>Error: Unable to establish two connections in quick succession to Intermapper Server<H3></center><br/>')
                    htmlOut.write('<center><H3>Error message returned by script;<H3></center>')
                    htmlOut.write('<center><H3>' + errorMessage + '<H3></center><br/>')
                    htmlOut.write('<center><H3>Common Error Messages and their meanings:<H3></center>')
                    htmlOut.write('<center>No route to host - Incorrect IP:PORT entered during App setup or firewall between servers</center><br/>')
                    htmlOut.write('<center>Connection refused - Incorrect PORT provided during App setup or no port provided<H3></center>')
                    htmlOut.write('<center>EOF occurred in violation of protocol - HTTPS enabled in setup when only HTTP access is available<H3></center>')
                    htmlOut.write('<center>Connection reset by peer - Possible mismatch of HTTPS/HTTP and PORT options.<H3></center>')
                    htmlOut.write('<center>No connection could be made because the target machine actively refused it - Check Intermapper IP:PORT detail is correct and for open firewall ports.<H3></center>')
            with open(FILEPATHS['errFile'], 'w') as errLog:
                if error == "sectionError":
                    errLog.write('Error with $SPLUNK_HOME/etc/apps/InterMapper/local/settings.conf - Section Error')
                elif error == "genError":
                    errLog.write(errorMessage)
                elif error == "optionError":
                    errLog.write('Error with $SPLUNK_HOME/etc/apps/InterMapper/local/settings.conf - Option Error')
                elif error == "emptyValue":
                    errLog.write('Configuration option missing; select "Configure App" from the navigation bar')
                elif error == "connError":
                    errLog.write('Unable to connect to Intermapper Server. ' + errorMessage)
                elif error == "connErrorTwo":
                    errLog.write('Unable to establish two connections in quick succession to Intermapper Server. ' + errorMessage)
        finally:
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Fatal')
            self.crashOut()
    
    def crashOut(self):
        self.logger.critical("sessionNo=\"%i\" parentFunction=\"%s\" message=\"Critical - Exiting due to error.\"", self.sessionNo, returnParent())


class ExitHandler(SimpleExitHandler):
    
    def __init__(self, sessionNo= -1, logLevel=logging.INFO, scrRuntime=False):
        SimpleExitHandler.__init__(self, sessionNo, logLevel, scrRuntime)
        
    def cleanExit(self):
        SimpleExitHandler.cleanExit(self)
        self.clearPid()
        quit()
        
    def clearPid(self):
        start_time = logMethodEntry(self.logger, self.sessionNo, self.scrRuntime)
        pidName = split(main.__file__)[1] + '.pid'
        pidPath = join(FILEPATHS['pidDir'], pidName)
        try:
            os.remove(pidPath)
        except IOError as e:
            self.logger.error("sessionNo=\"%i\" action=\"Delete PID\" message=\"Error: Unable to delete PID\" path=\"%s\" error=\"%s\"", self.sessionNo, pidPath, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
        except Exception as e:
            self.logger.error("sessionNo=\"%i\" action=\"Delete PID\" message=\"Error: Unexpected Error\" path=\"%s\" error=\"%s\"", self.sessionNo, pidPath, str(format(e)))
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime, 'Error')
        else:
            self.logger.info("sessionNo=\"%i\" action=\"Delete PID\" message=\"PID Deleted\" path=\"%s\"", self.sessionNo, pidPath)
            logMethodExit(start_time, self.logger, self.sessionNo, self.scrRuntime)
    
    def crashOut(self):
        SimpleExitHandler.crashOut(self)
        self.clearPid()
        quit()
        
## End class ExitHandler
