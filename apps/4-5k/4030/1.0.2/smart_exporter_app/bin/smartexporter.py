import logging
import base64
import os
import sys
import json
import cherrypy
import splunk
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util
import splunk.util
import splunk.clilib.cli_common
import shutil
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import jsonresponse
import smtplib
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import subprocess
import shlex
import logging.handlers
import splunk.rest
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib import cli_common as cli
import time
import tempfile
import splunk.entity as entity


settings = splunk.clilib.cli_common.getConfStanza('smartexporter', 'setup')
phantomjs_path = settings['phantomjs_path']
splunk_home = os.environ['SPLUNK_HOME']
template_path = "etc/apps/smart_exporter_app/appserver/static/templates"
JSScriptPath = "etc/apps/smart_exporter_app/appserver/static/script.txt"


def setup_logger():
    logger = logging.getLogger('smartexporter')
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    file_handler = logging.handlers.RotatingFileHandler(
                    make_splunkhome_path(['var', 'log', 'splunk', 
                                          'smartexporter.log']),
                                        maxBytes=25000000, backupCount=5)

    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    file_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

class ExportPDF(splunk.rest.BaseRestHandler):

    def __getCredentials(self, sessionKey):

        myapp = "smart_exporter_app"
        
        try:
            # list all credentials
            entities = entity.getEntities(['admin', 'passwords'], namespace=myapp,
                                        owner='nobody', sessionKey=sessionKey)
        except Exception, e:
            raise Exception("Could not get %s credentials from splunk. Error: %s"
                          % (myapp, str(e)))

        # return first set of credentials
        for i, c in entities.items():
            return c['username'], c['clear_password']

        raise Exception("No credentials have been found")

    def __die(self, msg):
        """ Handle an error gracefully """
        cmsg = str(msg)
        fmsg = str(msg)
        try:
            self.logger.error(str(cmsg))
        except:
            pass
        raise RuntimeError(str(fmsg))

    def handle_POST(self):
        sessionKey = self.sessionKey

        try:
            
            f = tempfile.NamedTemporaryFile(mode='w+b', delete=False)

            print f.name
            logger.info("temporary js file %s ", f.name)
            

            content = ""
            with open(os.path.join(splunk_home,JSScriptPath), 'r') as content_file:
                content = content_file.read()  

            username, password = self.__getCredentials(sessionKey)
            content = content.replace("##dashbord_URL##",self.args.get('DashboardURL'))

            content = content.replace("##username##",username)
            content = content.replace("##password##",password)
            content = content.replace("##scheduleparams##",self.args.get('ScheduleParam'))


            protocole = "http"
            if self.args.get('DashboardURL')[0:5] in ['https'] :
                protocole = "https"

            logger.info("protocole : %s Vs %s", protocole,self.args.get('DashboardURL')[0:5]);

            content = content.replace("##protocole##",protocole)
            
            logger.info("ExportPDF for url %s ", self.args.get('DashboardURL'))

            f.write(content)
            f.close();

            logger.info("start PhantomJS Process ...")

            #################################

            logger.info("phantomjs bin : " + phantomjs_path)
            logger.info("temp js file : " + f.name)

            if phantomjs_path in [None, '']:
                raise Exception('PhantomJs bin folder should be setup.')

            if not os.path.isdir(phantomjs_path):
                raise Exception('PhantomJs bin folder is not valid.')

            cmdargs = os.path.join(phantomjs_path,"phantomjs")+ "  --ignore-ssl-errors=true "+f.name
            
            timeout_rem = 600
            cmd_env = os.environ.copy()

            args = shlex.split(cmdargs)

            task = subprocess.Popen(args, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE,env=cmd_env)

            while task.poll() is None and timeout_rem > 0:
                time.sleep(1)
                timeout_rem -= 1
            if timeout_rem < 1:
                task.terminate()
                self.__die('Failed to capture the page within the allocated time')

            cmd_out, cmd_err = task.communicate()

            logger.info("cmd_out: %s", cmd_out)
            logger.info("cmd_err: %s", cmd_err)

            #################################@

            logger.info("end PhantomJS Process.")
            logger.info("delete temp JS file script.")
            os.remove(f.name);

            #self.response.write(base64.decodestring(code))
            self.response.write("finished")

        except Exception, e:
            logger.exception(e)
            self.response.write(e)

                
    #handle verbs, otherwise Splunk will throw an error
    handle_GET = handle_POST
