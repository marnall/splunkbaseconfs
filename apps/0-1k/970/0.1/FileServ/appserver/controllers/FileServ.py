import re, sys, logging, fnmatch, os, glob, time, os.path
import cherrypy
from cherrypy.lib.static import serve_file
import splunk.appserver.mrsparkle as mrsparkle
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.appserver.mrsparkle.lib import util
import splunk.util, splunk.search, splunk.bundle
from mako import exceptions

# the global logger
logger = logging.getLogger('splunk.appserver.FileServ')
logger.setLevel(logging.DEBUG)

#Copyright 2012, Reed Kelly

#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at

#       http://www.apache.org/licenses/LICENSE-2.0

#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

class FileServController(controllers.BaseController):
    '''/FileServ'''

    @expose_page(must_login=True, methods=['GET', 'POST'])
    def index(self, **kwargs):

        cherrypy.response.headers['content-type'] = mrsparkle.MIME_HTML
        targs = {}
        sessionKey = kwargs['sessionKey'] = cherrypy.session['sessionKey']

        if not splunk.auth.ping(sessionKey=sessionKey):
            return self.redirect_to_url('/account/login', _qs=[ ('return_to', util.current_url_path())])

        logger.info("index: start")

        conf = {}
        dirlist = []
        found_dirs = False
                
        try:
            conf = splunk.bundle.getConf('fileserv', namespace='FileServ', sessionKey=sessionKey)
            for dirkey in conf.findStanzas().iterKeys():
                if ( not dirkey.startswith('dir:') ):
                    continue
                dirlist.append((dirkey, conf[dirkey].get('description')))
                found_dirs = True
        except Exception, e:
            targs['error'] = "Can't load FileServ config file: %s" % e
            logger.error(targs['error'])
            return self.render_template('FileServ:/templates/FileServ/error.html', targs)

        logger.info("index: got conf. dirlist has len: %d" % len(dirlist))

        dirlist.sort()                  # sort list based on key
        
        targs['found_dirs'] = found_dirs
        targs['dirlist'] = dirlist

        if not dirlist:
            targs['error'] = "No folders listed in configuration file"
            logger.error(targs['error'])
            return self.render_template('FileServ:/templates/FileServ/error.html', targs)

        try:
            return self.render_template('FileServ:/templates/FileServ/index.html', targs)
        except:
            logger.error("index: Mako Render Error:\n%s" % exceptions.html_error_template().render())
            targs['error'] = "Problem with template file. Check web_service.log file."
            return self.render_template('FileServ:/templates/FileServ/error.html', targs)
  
        
    
    @expose_page(must_login=True, methods=['GET', 'POST'])
    def download_folder(self, **kwargs):

        cherrypy.response.headers['content-type'] = mrsparkle.MIME_HTML
        targs = {}
        sessionKey = kwargs['sessionKey'] = cherrypy.session['sessionKey']

        if not splunk.auth.ping(sessionKey=sessionKey):
            return self.redirect_to_url('/account/login', _qs=[ ('return_to', util.current_url_path())])

        dirkey = kwargs.get('dirkey', '')
        asearch = kwargs.get('search', '')
        maxcount = int(kwargs.get('maxcount', 50))
        sortindex = int(kwargs.get('sortindex', 0))
        dirpath = ""
        description = ""
        matchstr = ""

        logger.info("download_folder: started with dirkey=%s" % dirkey)
        
        conf = {}
        
        try:
            conf = splunk.bundle.getConf('fileserv', namespace='FileServ', sessionKey=sessionKey)
            if ( not dirkey.startswith('dir:') ):
                targs['error'] = "Invalid key (%s). Must start with 'dir:'" % dirkey
                logger.error(targs['error'])
                return self.render_template('FileServ:/templates/FileServ/error.html', targs)
            if dirkey not in conf:
                targs['error'] = "Can't find %s in FileServ conf file" % dirkey
                logger.error(targs['error'])
                return self.render_template('FileServ:/templates/FileServ/error.html', targs)
            dirpath = conf.get(dirkey).get("path")
            description = conf.get(dirkey).get("description")
            matchstr = conf.get(dirkey).get("matchstr")
        except Exception, e:
            targs['error'] = "Can't load FileServ config file: %s" % e
            logger.error(targs['error'])
            return self.render_template('FileServ:/templates/FileServ/error.html', targs)

        cfiles = []
        found_files = False
        matchre = ""
        got_match = False
        if ( type(matchstr) == type("") ):
            try:
                matchre = re.compile(matchstr)
                got_match = True
            except Exception, e:
                logger.error("download_folder: invalid match string (matchstr): %s" % e )
                got_match = False
        
        if os.path.isdir(dirpath):
            for fpath in glob.glob( os.path.join( dirpath, '*%s*' % asearch )):
                if got_match and not matchre.match(fpath):
                    continue
                fsize = os.path.getsize(fpath)
                fitime = os.path.getmtime(fpath)
                fmtime = time.ctime(fitime)
                cfiles.append(( os.path.basename(fpath), fsize, fitime, fmtime ))
                found_files = True

        if ( sortindex < 0 or sortindex > 2 ):
            sortindex = 0

        cfiles.sort(key=lambda x: x[sortindex])
        
        targs['dirkey'] = dirkey
        targs['dirpath'] = dirpath
        targs['description'] = description
        targs['cfiles'] = cfiles
        targs['found_files'] = found_files
        targs['search'] = asearch
        
        logger.info("download_folder: %s, %s, %s, %s, %s" % (dirkey,dirpath,description,found_files,asearch))
        
        return self.render_template('FileServ:/templates/FileServ/download_folder.html', targs)

    @expose_page(must_login=True, methods=['GET', 'POST'])
    def download(self,dirkey,filepath):
        sessionKey = cherrypy.session['sessionKey']
        if not splunk.auth.ping(sessionKey=sessionKey):
            return self.redirect_to_url('/account/login', _qs=[ ('return_to', util.current_url_path())])

        conf = {}
        
        try:
            conf = splunk.bundle.getConf('fileserv', namespace='FileServ', sessionKey=sessionKey)
            if ( not dirkey.startswith('dir:') ):
                targs['error'] = "Invalid key (%s). Must start with 'dir:'" % dirkey
                logger.error(targs['error'])
                return self.render_template('FileServ:/templates/FileServ/error.html', targs)
            if dirkey not in conf:
                targs['error'] = "Can't find %s in FileServ conf file" % dirkey
                logger.error(targs['error'])
                return self.render_template('FileServ:/templates/FileServ/error.html', targs)
            adir = conf.get(dirkey)
        except Exception, e:
            targs['error'] = "Can't load FileServ config file: %s" % e
            logger.error(targs['error'])
            return self.render_template('FileServ:/templates/FileServ/error.html', targs)

        diritem = conf.get(dirkey)
        adir = diritem.get('path')
        filepath = os.path.basename(filepath)
        return serve_file( os.path.join(adir, filepath), "application/x-download", "attachment")


def unit_test():
    class FakeSession(dict):
        id = 5
    sessionKey = splunk.auth.getSessionKey('admin', 'changeme')
    try:
        cherrypy.session['sessionKey'] = sessionKey
    except AttributeError:
        setattr(cherrypy, 'session', FakeSession())
        cherrypy.session['sessionKey'] = sessionKey
    cherrypy.session['user'] = { 'name': 'admin' }
    cherrypy.session['id'] = 12345
    cherrypy.config['module_dir'] = '/'
    cherrypy.config['build_number'] = '123'
    cherrypy.request.lang = 'en-US'
    # roflcon
    class elvis:
        def ugettext(self, msg):
            return msg
    cherrypy.request.t = elvis()
    # END roflcon

    dCSV = FileServController()
    out = dCSV.index()
    print out

if __name__ == '__main__':
    unit_test()
