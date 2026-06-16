try:
    import defusedxml.cElementTree as et 
except:
    import defusedxml.ElementTree as et

import logging
import os
import re
import sys
import time

import cherrypy

import splunk
import splunk.rest
import uuid

from splunk.models.fired_alert import FiredAlert 
from splunk.models.saved_search import SavedSearch 

import splunk.appserver.mrsparkle.controllers as controllers
import splunk.appserver.mrsparkle.lib.util as util

from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

dir = os.path.join(util.get_apps_dir(), __file__.split('.')[-2], 'bin')
if not dir in sys.path:
    sys.path.append(dir)
    
from unix.util.timesince import *
from unix.models.headlines import Headlines 

logger = logging.getLogger('splunk')

class unixHeadlines(controllers.BaseController):
    '''unixHeadlines Controller'''

    @route('/:app/:action=manage')
    @expose_page(must_login=True, methods=['GET']) 
    def manage(self, app, action, **kwargs):
        ''' return the headlines as output'''
 
        output = {'headlines': []}
        user = cherrypy.session['user']['name'] 
        host_app = cherrypy.request.path_info.split('/')[3]

        headlines = Headlines.all()
        headlines = headlines.filter_by_app(app)
        output['headlines'] = [{"name": headline.name, "label": headline.label, "alert_name": headline.alert_name } for headline in headlines]

        return self.render_json(output)

    @route('/:app/:action=delete')
    @expose_page(must_login=True, trim_spaces=True, methods=['POST']) 
    def delete(self, app, action, **params):
        ''' delete the provided headline '''

        user = cherrypy.session['user']['name'] 
        host_app = cherrypy.request.path_info.split('/')[3]
        id = params.get('name')

        if not id:
            logger.error('on delete, no identifier was provided')
            return self.render_json({'success':'false', 'error':'internal server error'})
        try:
            headline = Headlines.get(Headlines.build_id(id, app, user))
        except:
            logger.error('Failed to load headline %s' % id)
            return self.render_json({'success':'false', 'error':'failed to load headline'})

        if not headline.delete():
            logger.error('failed to delete headline %s' % headline.label)
            return self.render_json({'success':'false', 'error':'failed to delete headline'})
        
        logger.info('successfully deleted headline %s' % headline.label)

        return self.render_json({'success':'true', 'error':'headline %s deleted' % headline.label})

    @route('/:app/:action=id/:id')
    @expose_page(must_login=True, methods=['GET']) 
    def id(self, app, action, id, **kwargs):
        ''' return details for a specific headline'''

        headline = None
        output = {}
        user = cherrypy.session['user']['name'] 
        host_app = cherrypy.request.path_info.split('/')[3]

        try:
            headline = Headlines.get(Headlines.build_id(id, app, 'nobody')) 
        except Exception as ex:
            logger.exception(ex)
            logger.warn('problem retreiving headline %s' % id)
            return self.render_json({'success':'false', 'error':'problem retreiving headline %s' % id})

        alerts = SavedSearch.all()
        alerts = alerts.filter_by_app(app)
        alerts = alerts.search('is_scheduled=True')
        output['headline'] = [{"name": headline.name, "label": headline.label, "alert_name": headline.alert_name, "message": headline.message, "description": headline.description, "errors": headline.errors}]
        output['alerts'] = [{"name": alert.name, "is_disabled": alert.is_disabled} for alert in alerts]

        return self.render_json(output)
    
    @route('/:app/:action=new')
    @expose_page(must_login=True, methods=['GET']) 
    def new(self, app, action, **kwargs):
        ''' return new headline and alerts '''

        output = {'headlines': [], 'alerts':[]}
        user = cherrypy.session['user']['name'] 
        host_app = cherrypy.request.path_info.split('/')[3]
       
        headline = Headlines(app, user, '_new')
        alerts = SavedSearch.all()
        alerts = alerts.filter_by_app(app)
        alerts = alerts.search('is_scheduled=True')

        output['headline'] = [{"name": headline.name, "errors": headline.errors}]
        output['alerts'] = [{"name": alert.name, "is_disabled": alert.is_disabled} for alert in alerts]

        return self.render_json(output)
        

    @route('/:app/:action=list')
    @expose_page(must_login=True, methods=['GET']) 
    def list(self, app, action, **kwargs):
        ''' return headlines'''

        output = {'headlines': []} 
        user = cherrypy.session['user']['name'] 
        host_app = cherrypy.request.path_info.split('/')[3]

        count = int(kwargs.get('count', '10'))
        earliest = kwargs.get('earliest', None)
        severity = kwargs.get('severity', ['1','2','3','4','5'])

        headlines = Headlines.all()
        headlines = headlines.filter_by_app(app)
        headlines = headlines.filter_by_user(user)
      
        output['headlines'] = self.get_headlines_detail(headlines, app, user, 
                                                        count, earliest, severity=severity, srtd=True)

        return self.render_json(output)

    @route('/:app/:action=save')
    @expose_page(must_login=True, methods=['POST']) 
    def save(self, app, action, **params):
        ''' save the posted headline '''

        user = cherrypy.session['user']['name'] 
        host_app = cherrypy.request.path_info.split('/')[3]

        key = params.get('name')

        try:
            if key == '_new':
                headline = Headlines(app, user, str(uuid.uuid4()))
            else:
                headline = Headlines.get(Headlines.build_id(key, app, user))
        except:
            headline = Headlines(app, user, str(uuid.uuid4()))

        headline.label = params.get('label')
        if not headline.label:
            headline.errors = ['label cannot be blank']
        else:
            headline.message = params.get('message')
            headline.description = params.get('description')
            headline.alert_name = params.get('alert_name')
            headline.metadata.sharing = 'app'

        if headline.errors or not headline.passive_save():
            logger.error('Error saving headline %s: %s' % (headline.name, headline.errors[0]))
            alerts = SavedSearch.all()
            alerts = alerts.filter_by_app(app)
            alerts = alerts.search('is_scheduled=True')
            headline.name = key
            output = {}
            output['headline'] = [{"name": headline.name, "alert_name": headline.alert_name, "message": headline.message, "description":headline.description, "errors": headline.errors}]
            output['alerts'] = [{"name": alert.name, "is_disabled": alert.is_disabled} for alert in alerts]
            return self.render_json(output)
        else:
            return self.render_json({'success':'true', 'error':'headline %s saved' % headline.label})

    def get_headlines_detail(self, headlines, app, user, count, earliest, severity=None, srtd=None):
        search_string = "" 
        sorted_list = []
        if earliest is not None: 
            search_string = search_string + ' trigger_time > ' + str(self.get_time(earliest))

        for headline in headlines:
            try:
                s = SavedSearch.get(SavedSearch.build_id(headline.alert_name, app, user))
                alerts = None
                if s.alert.severity in severity:
                    alerts = s.get_alerts()
                if alerts is not None:
                    if len(search_string) > 0:
                        alerts.search(search_string)
                    for alert in alerts:
                        h = {'message'   : self.replace_tokens(headline.message, alert.sid), 
                             'job_id'    : alert.sid,
                             'severity'  : s.alert.severity,
                             'count'     : alert.triggered_alerts,
                             'time'      : int(time.mktime(alert.trigger_time.timetuple())),
                             'timesince' : timesince(alert.trigger_time)}
                        sorted_list.append(h)
            except Exception as ex:
                logger.warn('problem retreiving alerts for saved search %s' % headline.alert_name) 
                logger.info(ex)

        if len(sorted_list) > 0:
            if srtd is not None:
                tmp = sorted(sorted_list, key=lambda k: k['time'], reverse=True)[0:count]
                sorted_list = tmp

        return sorted_list

    def get_time(self, time):
        getargs = {'time': time, 'time_format': '%s'}
        serverStatus, serverResp = splunk.rest.simpleRequest('/search/timeparser', getargs=getargs)
        root = et.fromstring(serverResp)
        if root.find('messages/msg'):
            raise splunk.SplunkdException(root.findtext('messages/msg'))
        for node in root.findall('dict/key'):
            return node.text

    def discover_tokens(self, search):
        return re.findall('\$([^\$]+)\$', search)

    def replace_tokens(self, search, sid):
        output = search 
        tokens = self.discover_tokens(search)

        if len(tokens) > 0:
            try:
                job = splunk.search.JobLite(sid)
                rs = job.getResults('results', count=1)
                for row in rs.results(): 
                    tmp = []
                    for token in tokens:
                        if row[token] is not None:
                            output = re.sub(r'\$' + token + '\$', str(row[token]), output)
            except Exception as ex:
                logger.warn('unable to parse tokens from search %s' % sid) 
                logger.debug(ex) 
        return output
