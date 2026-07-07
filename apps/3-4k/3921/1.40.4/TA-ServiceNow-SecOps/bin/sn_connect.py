
import sys
import traceback
import requests
import socket
import splunk.Intersplunk
import splunk.clilib.cli_common as cliLib
import sn_sec_util as snutil

  
def postData(sessionKey, url, headers, dataValues):
    try:
        accessSettings = cliLib.getMergedConf("sn_sec_instance")
        user = accessSettings['sn_instance']['username']
        pwd = accessSettings['sn_instance']['password']
        proxy_url = str(accessSettings['sn_instance']['proxy_url'])
        proxy_url = proxy_url.strip()
        
        clearPwd, clearPrx = snutil.getCredentials(sessionKey)
        if clearPwd not in [None, '']:
            pwd = clearPwd
        
        if proxy_url:        
            proxy_port = accessSettings['sn_instance']['proxy_port']
            proxy_user = accessSettings['sn_instance']['proxy_username']
            proxy_pwd = accessSettings['sn_instance']['proxy_password']
            if clearPrx not in [None, '']:
                proxy_pwd = clearPrx
          
            if not "://" in proxy_url:
                proxy_url = "https://{0}".format(proxy_url)
            proxyString = proxy_url
            
            if proxy_port:
                proxyString = "{0}:{1}".format(proxy_url, proxy_port)
                
            if proxy_user and proxy_pwd:
                proxyString = proxyString.replace("://", "://{0}:{1}@".format(proxy_user, proxy_pwd))
            proxies = { "http": proxyString, "https": proxyString }
            return requests.post(url, auth=(user, pwd), proxies=proxies, headers=headers, data=dataValues)        
        else:
            return requests.post(url, auth=(user, pwd), headers=headers, data=dataValues)
    except Exception:
        errorText = "Unable to connect to ServiceNow. Error: %s" % (traceback.format_exc())
        snutil.createSplunkEvent(sessionKey, errorText)
        splunk.Intersplunk.parseError(errorText)
