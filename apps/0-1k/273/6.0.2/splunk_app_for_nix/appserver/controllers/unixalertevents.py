
import logging
import json

import cherrypy

import splunk

from splunk.models.fired_alert import FiredAlert

import splunk.appserver.mrsparkle.controllers as controllers

from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

logger = logging.getLogger('splunk')


class unixAlertEvents(controllers.BaseController):
    '''unixAlertEvents Controller'''

    @route('/:app/:action=id/:sid')
    @expose_page(must_login=True, methods=['GET'])
    def sid(self, app, action, sid, **kwargs):
        ''' return details for a specific alertevent'''

        alertevent = None
        output = None
        user = cherrypy.session['user']['name']
        host_app = cherrypy.request.path_info.split('/')[3]

        try:
            job = splunk.search.getJob(sid)

            # for r in job.results:
            #    logger.debug("results %s" % r)

            fired = FiredAlert.all()
            fired = fired.search('sid=%s' % sid)[0]

            hosts = sorted(list({str(x.get('host'))
                                 for x in job.results if x.get('hosts')}))
            alertevent = {'alert_name': job.label,
                          'time': fired.trigger_time,
                          'description': fired.savedsearch_name,
                          'severity': fired.severity,
                          'hosts': hosts,
                          'sid': sid,
                          'et': job.earliestTime,
                          'lt': job.latestTime}

            logger.debug(alertevent)

        except Exception as ex:
            logger.exception(ex)
            logger.warn('problem retreiving alertevent %s' % id)
            return self.render_json({"error": str(ex)})

        return self.render_json({"alertevent": json.dumps(
            alertevent, default=str), "host_app": host_app, "app": app})
