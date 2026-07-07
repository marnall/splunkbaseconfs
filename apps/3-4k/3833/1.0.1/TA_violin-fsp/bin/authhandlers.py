from requests.auth import AuthBase
import requests
import logger_manager as log
import json
import os

from requests_toolbelt.adapters import host_header_ssl
import utilities

logger = log.setup_logging('violin_fsp')

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
myapp = "TA_violin-fsp"
file_path = os.path.join(SPLUNK_HOME, "etc", "apps", myapp, "local")


class TokenAuth(AuthBase):
    def __init__(self, **args):
        self.node = args.get('node')
        self.session_key = args.get("session_key")
        self.original_endpoint = args.get('endpoint')
        self.filename = "certificate_host_info.txt"
        self.host = "violin-systems.com"

    
    def get_session_id(self, username, password, verify):
        """
        To get session-id as a cookie and issuer of certificate
        
        :param username: username for vmem FSP
        :param password: password for vmem FSP
        :param verify: value for certificate-verification param in requests module
        :param host: issuer of certificate
        :return: cookie of session-id or None in case of error, issuer/host of certificate
        """
        try:
            write_data = True
            file_data = utilities._read_meta_info(self.filename, file_path)
            if file_data!= -1:
                if str(self.node) in file_data and file_data.get(str(self.node)) != None:
                    self.host =  file_data[str(self.node)]
                    write_data = False
                else:
                    file_data.update({str(self.node): self.host})
            else:
                 file_data = {}
                 file_data[str(self.node)] = self.host
            try:
                cookies = self.getSessionvalidity(username, password, verify, self.host)
            except requests.exceptions.SSLError as e:
                logger.warning("Violin FSP Error: Getting SSL error while executing API call with certificate host, retrying once using other host")
                if self.host == "violin-systems.com":
                    self.host = "violin-memory.com"
                else:
                    self.host = "violin-systems.com"
                cookies = self.getSessionvalidity(username, password, verify, self.host)
                file_data[str(self.node)] = self.host
                write_data = True
            
            if write_data:
                utilities._write_meta_info(file_data, self.filename, file_path)    
            return cookies, self.host
        except Exception as e:
            logger.exception("Violin FSP Error: Error while getting session validity for authentication. %s" % str(e))
    
    def getSessionvalidity(self, username, password, verify, host):
        """
        To get session-id as a cookie
        
        :param username: username for vmem FSP
        :param password: password for vmem FSP
        :param verify: value for certificate-verification param in requests module
        :param host: issuer of certificate
        :return: cookie of session-id or None in case of error
        """
        headers = {'Content-Type': 'application/json', "Host": host}
        body = json.dumps({"data": {"username": username, "password": password}})
        url = 'https://' + self.node + '/concerto/auth/login'
        request_session = requests.Session()
        
        request_session.mount('https://', host_header_ssl.HostHeaderSSLAdapter())
        response = request_session.post(url=url, headers=headers, data=body, verify=verify)
        if response.status_code == 200:
            return dict(response.cookies)

