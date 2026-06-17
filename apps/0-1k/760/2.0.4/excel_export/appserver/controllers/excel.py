try:
    from cStringIO import StringIO
except:
    from StringIO import StringIO


import asyncore
import json
import logging
import os
import re

import cherrypy

import splunk
import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib import util
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.rest
import splunk.search
import splunk.util

from excel_export.clients.json_https_client import JSONHttpsClient
from excel_export.clients.wb_client import WBClient
from excel_export.decorators import host_app

logger = logging.getLogger('splunk')

SPLUNK_HOME = os.environ.get('SPLUNK_HOME')

class excel(controllers.BaseController):
    """Excel Export Controller"""

    @route('/:sid')
    @expose_page(must_login=True, methods=['GET']) 
    @host_app
    def default(self, sid, host_app=None, filename=None, count=10000, **kwargs):
        """ create excel report """
 
        try:
            count = abs(int(count)) 
        except:
            logger.warn('given count %s is not a positive integer, reverting to 10000' % count)
            count = 10000

        if count > 1000000:
            count = 1000000 
            logger.warn('count %s was reduced so as not to exceed excel max row count' % count) 
        
        if not filename:
            filename = 'splunk_report.xls'
        elif not filename.endswith('.xls'):
            logger.warn('xls file extension will be appended to given filename %s ' % filename) 
            filename = '.'.join([filename, 'xls'])

        use_sid = None
        etype = None
        user = cherrypy.session['user']['name']
        logger.info('creating excel export for user %s from search id %s' %(user, sid))

        cherrypy.response.stream = True
        cherrypy.response.headers['Content-Type'] = 'application/mx-excel'
        cherrypy.response.headers['Content-Disposition'] = 'attachment; filename="%s"' % filename

        job = self.get_processed_job(sid)

        results = getattr(job, 'results')
        field_names = [x for x in getattr(job, 'results').fieldOrder 
                       if (not x.startswith('_') or x == '_time' or x == '_raw')]
        if len(field_names) > 256:
            logger.warn('reducing the number of fields from %s to 256' % len(field_names))
            field_names = field_names[:255]
        
        j = job.toJsonable()

        search = j['request']['search'] + ' | head %s ' % count
        params = {
                  'required_field_list': '*',
                  'status_buckets': str(j.get('statusBuckets', 0)), 
                  'remote_server_list': '*',  
                  'output_mode': 'json'
                 }

        if j.get('reportSearch') and int(j.get('resultCount')) <= count:
            use_sid = sid 
            etype = 'results'
        elif int(j.get('eventAvailableCount')) >= count:
            use_sid = sid 
            etype = 'events'
        else:
            if j.get('searchEarliestTime'):
                params['earliest_time'] = j['searchEarliestTime']
            if j.get('searchLatestTime'):
                if not j['request'].get('latest_time'):
                    params['latest_time'] = j.get('createTime')
                else:
                    params['latest_time'] = j['searchLatestTime']

        use_ssl = splunk.util.normalizeBoolean(splunk.rest.simpleRequest(
                          '/services/properties/server/sslConfig/enableSplunkdSSL')[1]) 

        #SPL-58975 - json mode change in 5.0 
        isNewFormat = None
        try:
            version = json.loads(splunk.rest.simpleRequest('/services/server/info?output_mode=json')[1])['generator']['version']
            v = version[0]
            if v.isdigit() and int(v) >= 5:
                isNewFormat = True
        except:
            pass

        consumer = WBClient(field_names, isNewFormat=isNewFormat) 
        cherrypy.session.release_lock()
        s = StringIO()

        try:
            # APP-815: JSONHttpsClient now supports chunked-encoding
            request = JSONHttpsClient(
                          host = splunk.getDefault('host'),
                          port =splunk.getDefault('port'),
                          use_ssl = use_ssl,
                          user = cherrypy.session['user']['name'],
                          token = cherrypy.session.get('sessionKey'),
                          search = search,
                          namespace = host_app,
                          parameters = params,
                          callback = consumer,
                          sid = use_sid,
                          etype = etype
                      )
        except TypeError, ex:
            logger.exception(ex)
            raise

        def stream():
            ''' APP-815 - Use streaming mode and immediately start the download.
                Immediately send the first 8-bytes of the Excel XLS header since
                PEP-333 requires wsgi write() not send any headers until at least
                one byte is available for the response body. 
            '''
            yield '\xD0\xCF\x11\xE0\xA1\xB1\x1A\xE1'
            asyncore.loop()
            consumer.wb.save(s)
            s.seek(8)
            yield s.read()
            
        return stream()

    def get_processed_job(self, sid, search=None):
        """ retrieve finished (optionally postprocessed) job """

        try:
            job = splunk.search.getJob(sid, sessionKey=cherrypy.session['sessionKey'])
        except:
            raise cherrypy.HTTPError('400', 'sid not found')

        if search: 
            job.setFetchOption(search=search)

        while not job.isDone:
            time.sleep(.1)
       
        return job

