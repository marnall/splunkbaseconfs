from __future__ import with_statement

import os
try:
    from urllib.request import urlopen, Request, build_opener
    from urllib.parse import urlencode, unquote
except ImportError:
    from urllib2 import urlopen, Request, build_opener, HTTPError
    from urllib import urlencode, unquote
from contextlib import closing, nested

from splunk import auth
from splunk.rest import format

import core.appmap as appmap
from .model import PaladinModel, PaladinField, RESTResource, LocalApps, RemoteApps, PaladinQueryRunner, LocalAppConfigs
from .model import RemoteAppEntries, NamedRemoteAppEntries


'''
PaladinException intended to be used to notify splunkd errors to the application in a systematical way -
include status, message etc.
'''
class PaladinException(Exception):
    exceptions = dict(
                      )

    def __init__(self, tag):
        self.message = PaladinException.exceptions[tag]


ATOM_NS = "{%s}" % format.ATOM_NS
NSMAP   = {'a' : format.ATOM_NS}

URLOPEN_TIMEOUT     = 15


@RESTResource(path='services/server/info')
class ServerInfo(PaladinModel):
    name        = PaladinField('title')
    server_name = PaladinField('content', 'serverName')
    platform    = PaladinField('content', 'os_name')
    version     = PaladinField('content', 'version')

@RESTResource(path='services/apps/apptemplates')
class AppTemplates(PaladinModel):
    name        = PaladinField('title')
    href        = PaladinField('links', 'alternate', 'href')
    
@RESTResource(path='services/apps/appinstall')
class AppInstall(PaladinModel):
    location        = PaladinField('content', 'localtion')
    name            = PaladinField('content', 'name')
    status          = PaladinField('content', 'status')
    source_location = PaladinField('content', 'source_localtion')


'''
any splunkd will provide:
    1. access server info of this instance.
    2. local apps infos and browsing.
    3. archive a local app.
    4. restore an app to local
    5. install an app to local.
    6. remove an app in local.
    7. create a new app from template
    8. restart this instance
'''
class Splunkd(object):
    
    def __init__(self, host_path=None, sessionKey=None):
        self.runner = PaladinQueryRunner(host_path, sessionKey)
        self.host_path = host_path
        self.sessionKey = sessionKey
        
        info = ServerInfo.build (self.runner)
        
        # there is only one entry anyway
        for f in info.all():
            self.platform       = f.platform.value
            self.version        = f.version.value
            self.server_name    = f.server_name.value

        self.m_localapps = LocalApps.build (self)
        self.m_templates = AppTemplates.build (self.runner)
        self.m_installer = AppInstall.build (self.runner)

    def get_templates(self):
        return self.m_templates.all()
    
    def create_app_from_template(self, appname, template='barebones', **kwargs):
        return self.m_apps.create(appname, template, **kwargs)

    def local_apps(self):
        return self.m_localapps.all()
    
    '''
    Allows for restarting Splunk.
    POST server/control/restart

    Restarts the Splunk server. no return if ok.    
    '''
    def restart(self):
        self.runner.set_entity('services/server/control/restart')
        
    def remove_app(self, app):
        m_app = self.m_localapps.get(app)
        if m_app: m_app.delete()
        # after deletion, the splunkd should restart to respond the change.
        # here it is left to the application to do/control that.
    
    
    def install_app(self, fileName, update=False):
        return self.m_installer.create(name=fileName, update=update)
    
    def archive_app(self, app):
        m_app = self.m_localapps.get(app)
        return m_app.archive() if m_app else None
    
    '''
    The restoration of an app is based on the app file or a link from package_app that can be downloaded.
    it actually calls install_app with update=True flag.
    '''
    def restore_app(self, archive):
        return self.install_app(archive.path.value, True)


if __name__ == "__main__":
    host_path = 'https://localhost:8089'
    sessionKey = auth.getSessionKey('admin', 'monday', host_path)
    
    splunkd = Splunkd(host_path, sessionKey)
    templates = splunkd.get_templates()
    
    '''
    for t in templates:
        napp = splunkd.create_app_from_template('ap-%s' % t.name.value, t.name.value)
        print(napp.name.value)
        print(napp.href.value)
    '''

    apps = splunkd.get_installed_apps()
    
    for app in apps:
        print(app.name.value)
        print(app.description.value)
            
    print('----------------------------------------')
    apps = splunkd.get_installed_apps()
    for app in apps:
        print(app.name.value)
        print(app.version.value)

