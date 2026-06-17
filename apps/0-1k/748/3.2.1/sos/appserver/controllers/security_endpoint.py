import cherrypy

import splunk
import splunk.util

import os
import sys

import splunk.appserver.mrsparkle.controllers as controllers
from splunk.appserver.mrsparkle.lib.decorators import expose_page
from splunk.appserver.mrsparkle.lib.routes import route
import splunk.appserver.mrsparkle.lib.util as util

import httplib2

import splunk.clilib.cli_common as comm


class SecurityHealthController(controllers.BaseController):
    """
        Instantiation of a BaseController-style class
        """
    
    
    
    @expose_page(must_login=True)
    def check_ssl(self, **kwargs):
        """ Endpoint that returns JSON object with Security config info """
        
        
        
        #Get configurations from conf files
        web_ssl_conf = comm.getConfKeyValue('web', 'settings','enableSplunkWebSSL')
        
        sslv3_conf = comm.getConfKeyValue('web', 'settings', 'supportSSLV3Only')
        
        
        mgmtHost = comm.getConfKeyValue('web', 'settings', 'mgmtHostPort')
        
        splunkd_ssl_conf = comm.getConfKeyValue('server', 'sslConfig', 'enableSplunkdSSL')
        
        cert_path = comm.getConfKeyValue('web', 'settings', 'caCertPath')
        
        
        web_ssl  = comm.getWebConfKeyValue(comm.KEY_WEB_SSL).lower() == "true"
        
        
        if sslv3_conf == 'false':
            sslv3 = False
        else:
            sslv3 = True
        
        
        if splunkd_ssl_conf == 'false':
            splunkd_ssl = False
        else:
            splunkd_ssl = True
        
        
        
        # Create url for default password test
        url = comm.getMgmtUri() +  '/services'
        # Create http request object
        h = httplib2.Http(disable_ssl_certificate_validation=True)
        
        
        # Try default creds
        h.add_credentials('admin', 'changeme')
        # Store response
        http_response = str(h.request(url, "GET"))
        
        # Grab the certificate
        
        cert_path = os.path.join( os.environ['SPLUNK_HOME'], cert_path )
        cert_info = os.popen('openssl x509 -in ' + str(cert_path) + ' -noout -text').read()
        
        is_defaultcrt = False
        is_root = False
        default_pasword = None
        
        # Check for the SplunkCommonCA default string
        if cert_info.find("SplunkCommonCA") != -1:
            is_defaultcrt = True
        
        # Check if process is running as root
        if os.geteuid() == 0:
            is_root = True
        
        
        # Check repsonse codes from request to see if default creds are valid
        if http_response.find("Unauthorized") != -1 and http_response.find("401") != -1 :
            default_pasword = False
        elif http_response.find("200"):
            default_pasword = True
        
        output = {'is_root' : is_root, 'is_defaultcrt' : is_defaultcrt, 'is_sslweb' : web_ssl, 'default_pasword' : default_pasword, 'splunkd_ssl' : splunkd_ssl, "sslv3" : sslv3 }
        #output = {'is_root' : is_root,  'is_sslweb' : web_ssl, 'default_pasword' : default_pasword, 'splunkd_ssl' : splunkd_ssl }
        return self.render_json(output)
    
    
    
    
    
    """
        Docs Info:
        well, it depends on the type of content
        typically, description of items shown on the view should be in the HTML file that expands in the view itself when clicking on the "Learn More" button
        this should include links to relevant topics on docs.splunk.com or Splunk Answers to resolve the security problems raised
        that should be the bulk of the documentation
        the rest should be some odds and ends in the README file and on the home view - a short description of the view
        we can go over those bits with our Docs writer, Vince
        
        """
