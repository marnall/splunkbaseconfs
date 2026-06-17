import logging
import os
import shutil

import cherrypy
import splunk
import splunk.util as util
import splunk.rest as rest
import controllers.module as module
from splunk.appserver.mrsparkle.lib import cached, util

try:
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
except:
    # something is very wrong
    raise

# the global logger
logger = logging.getLogger('splunk.appserver.sosFTR')
logger.setLevel(logging.DEBUG)
logfile = os.path.join(SPLUNK_HOME, 'var', 'log', 'splunk', 'sos_ftr.log')
handler = logging.handlers.RotatingFileHandler(logfile, 
                                               maxBytes=5240000,
                                               backupCount=5)
g = logging.Formatter("%(asctime)s - %(message)s")
handler.setFormatter(g)
handler.setLevel(logging.INFO)
logger.addHandler(handler)

class sosFTR(module.ModuleHandler):

    def generateResults(self, host_app=None, client_app=None):

        token = cherrypy.session.get('sessionKey') 
        output = cached.getEntities('apps/local', search=['disabled=false','visible=true'], count=-1)
   
        if not 'sideview_utils' in output: 
            return 'noSVU'
        else:
            view_base = os.path.join(util.get_apps_dir(), 'sos', 
                                            'default', 'data', 'ui', 'views') 
            files = os.listdir(view_base)
            badfiles = []
            for file in files:
                if file.endswith('.bak'):
                    try:
                        source_file = os.path.join(view_base, file)
                        target_file = os.path.join(view_base, file[:-4])
                        if os.path.exists(target_file):
                            os.chmod(target_file,0644)
                        shutil.move(source_file, target_file)
                        logger.info('Renamed file = %s to %s.' % (source_file, file[:-4]))

                    except (IOError,OSError), e:
                        logger.info('ERROR : Could not rename file = %s to %s. Please check file permissions or perform the operation manually.' % (source_file, file[:-4]))
                        logger.info('Exception : %s' % e)
                        badfiles.append(file)
                        
            if len(badfiles) != 0:
                logger.info('Failed to rename the following files in %s : %s' % (view_base, ", ".join(badfiles)))
            else:
                logger.info('All files renamed successfully!')

            rest.simpleRequest('/services/data/ui/views/_reload', sessionKey = token, method = 'GET')
            logger.info('Views reloaded.')

            return 'hasSVU'
