import logging
import urllib2
import urlparse

import cherrypy

import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route

logger = logging.getLogger('splunk.custom.appserver')


class ProxyController(controllers.BaseController):
    """
    Test instantiation of a BaseController-style class
    """

    @expose_page(must_login=True, methods='GET')
    def twitter_image(self, uri=None, **unused):
        
        if not uri:
            raise cherrypy.HTTPError(400)

        uri = urlparse.urlparse(uri)

        proxy_uri = 'http://a0.twimg.com/%s' % uri.path.strip('/')

        response = urllib2.urlopen(proxy_uri, timeout=10)
        info = response.info()
        for k in info:
            logger.debug('PROXY header: %s=%s' % (k, info[k]))
            cherrypy.response.headers[k] = info[k]
        
        def content_iter():
            for chunk in response.read(8192):
                yield chunk

        return content_iter()

    twitter_image._cp_config = {'response.stream': True}
