from distutils.version import LooseVersion
import logging
import os
import sys 
import cherrypy

import splunk
import splunk.entity as entity
import splunk.bundle as bundle
from splunk.util import normalizeBoolean as normBool 
import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util

from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
from splunk.models.app import App

sysdir = os.path.join(util.get_apps_dir(), __file__.split('.')[-2], 'bin')
if not sysdir in sys.path:
    sys.path.append(sysdir)

from windowsmonitoring.models.input import MonitorInput, WinEventLogInput, EventLogCannon, WinPerfmonInput 

logger = logging.getLogger('splunk.windows_setup')
WINDOWS_MONITORING_PREFIX = 'Windows__' 
PERFMON_CANON_ENDPOINT = '/admin/win-perfmon-find-collection'
PERFMON_EXISTING_ENDPOINT = '/data/inputs/win-perfmon'
DHCP_LOG_FILE = r'$WINDIR\System32\DHCP'
WIN_UPDATE_LOG_FILE = r'$WINDIR\WindowsUpdate.log'

PERFMON_APP_INPUTS = ['Processor', 'Network Interface', 'Memory', 'PhysicalDisk', 'LogicalDisk', 'Process', 'System']
PERFMON_DEFAULTS = PERFMON_APP_INPUTS
EVENT_LOG_DEFAULTS = ['Application', 'Security', 'System', 'Setup']

class WindowsSetup(controllers.BaseController):
    '''Windows Setup Controller'''
 
    @route('/:app/:action=setup')
    @expose_page(must_login=True, methods=['GET']) 
    def setup(self, app, action, **kwargs):
        ''' show the setup page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        user = cherrypy.session['user']['name'] 
        this_app = App.get(App.build_id(host_app, host_app, user))

        mon = self.get_file_monitors(app)

        cannon = EventLogCannon.all()
        cannon = cannon.order_by('importance', sort_dir='asc')

        win = WinEventLogInput.all()
        win = win.search('name=localhost')

        system = (sys.platform.startswith("win"))

        log_override = False
        log_list = set()
        perfmon_canon = []
        perfmon_active = None

        if system:

            perfentity = self.get_perfmon_canon_entity()
            perfmon_active_entity = self.get_perfmon_active_entities(host_app)

    #        for k, v in perfmon_active_entity.iteritems():
    #            logger.debug('BEGINNING %s' % k)
    #            for kk, vv in v.iteritems():
    #                logger.debug('k=%s, v=%s' % (kk, vv))
    #            logger.debug('ENDING %s' % k)
    #

            
            class PerfmonCanonEntityMap:
                def __init__(self, name):
                    self.name = name

            class ActivePerfmon:
                def __init__(self, logs):
                    self.disabled = False
                    self.logs = logs

            perfmon_canon = map(lambda e: PerfmonCanonEntityMap(e), perfentity)

            log_override = False
            log_list = []
            perfmon_active_logs = set()
            if this_app.is_configured:
                perfmon_active_logs = set(v['object'] for k, v in perfmon_active_entity.iteritems())
            else:
                perfmon_active_logs = PERFMON_DEFAULTS
                if win[0].disabled:
                    log_list = EVENT_LOG_DEFAULTS
                    log_override = True
                else:
                    log_list = set(win[0].logs + EVENT_LOG_DEFAULTS)
                updateLog, = (m for m in mon if m.name == WIN_UPDATE_LOG_FILE)
                updateLog.disabled = False

            perfmon_active = ActivePerfmon(perfmon_active_logs)


        return self.render_template('/%s:/templates/setup_show.html' % host_app, 
                                    dict(system=system, 
                                         mon=mon, 
                                         win=win, 
                                         cannon=cannon, 
                                         app=app, 
                                         log_override=log_override,
                                         log_list=log_list,
                                         perfmon_canon=perfmon_canon, 
                                         perfmon_active=perfmon_active))

    @route('/:app/:action=success')
    @expose_page(must_login=True, methods=['GET']) 
    def success(self, app, action, **kwargs):
        ''' render the success page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        return self.render_template('/%s:/templates/setup_success.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=failure')
    @expose_page(must_login=True, methods=['GET']) 
    def failure(self, app, action, **kwargs):
        ''' render the failure page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        return self.render_template('/%s:/templates/setup_failure.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=unauthorized')
    @expose_page(must_login=True, methods=['GET']) 
    def unauthorized(self, app, action, **kwargs):
        ''' render the unauthorized page '''

        host_app = cherrypy.request.path_info.split('/')[3]
        return self.render_template('/%s:/templates/setup_403.html' \
                                    % host_app,
                                    dict(app=app))

    @route('/:app/:action=save')
    @expose_page(must_login=True, methods=['POST']) 
    def save(self, app, action, **params):
        ''' save the posted setup content '''

        host_app = cherrypy.request.path_info.split('/')[3]
        user = cherrypy.session['user']['name'] 

        # get list of perfmon requests
        perfmon_requests = params.get('winperfmons');

        # Normalize perfmon_requests
        # if there is only one request, its type is basestring, else it's list. thanks, framework!
        if isinstance(perfmon_requests, basestring):
            perfmon_requests = [perfmon_requests]
        # if there are no requests, it gets set to None
        if perfmon_requests is None:
            perfmon_requests = []

        perfmon_active_logs = self.get_perfmon_active_entities(host_app)
        perfmon_canon = self.get_perfmon_canon_entity()
        perfmon_requests = set(perfmon_requests) & set(perfmon_canon)

        # for each request that is not in existing:
        for request in perfmon_requests:
            existing = dict((k, v) for k, v in perfmon_active_logs.iteritems() if v['object'] == request)
            if not existing: 
                # NOTE risk: n REST network calls are implied here
                existing_metadata = self.get_perfmon_canon_entity(object=request)
                counters = existing_metadata['counters']
                instances = existing_metadata['instances']

                new_entity = entity.Entity(
                    PERFMON_EXISTING_ENDPOINT,
                    WINDOWS_MONITORING_PREFIX + request,
                    namespace=host_app,
                    owner=user)
                new_entity['counters'] = counters # we use all counters
                new_entity['instances'] = instances # we use all instances
                new_entity['index'] = 'default'
                new_entity['interval'] = 10
                new_entity['object'] = request

                entity.setEntity(new_entity)
                    
        # else for each existing that is not in request:
        for existingKey, existingValue in perfmon_active_logs.iteritems():
            if existingValue['object'] not in perfmon_requests:
                #   delete existing
                entity.deleteEntity(
                    PERFMON_EXISTING_ENDPOINT,
                    WINDOWS_MONITORING_PREFIX + existingValue['object'],
                    host_app,
                    user)

        # now, event logs:

        win = WinEventLogInput.get(WinEventLogInput.build_id('localhost', host_app, user))
        evt_logs = params.get('winevtlogs')
	if evt_logs:

            win.logs = evt_logs 

	    if normBool(win.disabled):
                win.enable()
	    try:
	        win.edit()
            except Exception, ex:
                logger.exception(ex)
	        raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'failure'))
	else:
            win.disable()

        mon = self.get_file_monitors(app)
  
        for m in mon:
            disabled = normBool(params.get(m.name + '.disabled'))
            if disabled:
                m.disable()
            else:
                m.enable()
            m.share_global()

        logger.debug('Splunk Version = %s' % self._get_version())
        if self._get_version() <= LooseVersion('4.2.2'):
            temp_app = bundle.getConf('app', namespace=host_app, owner='nobody') 
            temp_app['install']['is_configured'] = 'true'
        else:
            this_app = App.get(App.build_id(host_app, host_app, user))
            this_app.is_configured = True 
            this_app.share_app()
            try:
                this_app.passive_save()
            except Exception, ex:
                logger.info(ex)

        logger.info('%s - App setup successful' % host_app)

        raise cherrypy.HTTPRedirect(self._redirect(host_app, app, 'success'))

    def get_distsearch(self, host_app):
        return bundle.getConf('distsearch', 
                               namespace=host_app, 
                               owner='nobody')['replicationBlacklist']['nontsyslogmappings'] 

    def _redirect(self, host_app, app, endpoint):
        return self.make_url(['custom', host_app, 'windowssetup', app, endpoint])

    def _get_version(self):
        try:
            return LooseVersion(entity.getEntity('server/info', 'server-info')['version'])
        except:
            return LooseVersion('0.0')
   
    def get_file_monitors(self, host_app):
        mon = MonitorInput.all()
        mon = [m for m in mon if m.name in [DHCP_LOG_FILE, WIN_UPDATE_LOG_FILE]]
        return mon

    def get_perfmon_canon_entity(self, **kwargs):
        the_entity = entity.getEntity(PERFMON_CANON_ENDPOINT, 'PERFResult', **kwargs)
        if kwargs:
            return the_entity
        return [e for e in the_entity['objects'] if e in PERFMON_APP_INPUTS]

    def get_perfmon_active_entities(self, host_app):
        entities = entity.getEntities(PERFMON_EXISTING_ENDPOINT)
        return dict((k, v) for k, v in entities.iteritems() if v['eai:acl']['app'] == host_app and v['object'] in PERFMON_APP_INPUTS)
