import os, json
import splunk.Intersplunk
import splunk.entity
from splunk.clilib import cli_common as cli
from requests import (adapters, exceptions, packages, Session)
from requests.packages.urllib3.util.retry import Retry
import splunk.bundle
import splunk.rest
import base64
import time
import splunklib.client as client
import xml.etree.ElementTree as ET

APP_NAME = "Kaspersky_Threat_Feed_App_for_Splunk"
KVSTORE = "kl_settings"
SPLUNK_REST_SSL = 0
XOR_KEY = "#"
PORT = 8089
REST = "https://localhost:8089"

def KLSetSettings():
    """Main function"""
    with open('kl_set_settings_err.log', 'a') as logf:
        try:
            results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
            keywords, argvals = splunk.Intersplunk.getKeywordsAndOptions()
            if argvals['run'] == 'true':
                if argvals.get('cert', False): 
                    get_cert(argvals['cert'], logf)
                sesKey = settings.get("sessionKey")
                settings = get_splunk_collection(sesKey, logf)
                settings['ProxyPassword'] = get_splunk_password(sesKey, logf)
                save_in_configuration_file(settings, logf)
        except Exception, e:
            logf.write (str(e) + '\n')
            import traceback
            stack =  traceback.format_exc()
            logf.write(splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack)) + '\n')


def get_cert(input, logf):
    """get certificate from params, decode from base64 and save"""
    try:
        cert = base64.b64decode(input + b'===')
        with open('feeds.pem', 'w') as fcert:
            fcert.write(cert)
    except Exception, e:
        logf.write (str(e) + '\n')


def get_splunk_collection (sesKey, logf):
    """get splunk collection with KL App settings"""
    try:
        splunk_uri = '/servicesNS/nobody/{0}/storage/collections/data/{1}'.format(
           APP_NAME, KVSTORE)
        splunk_url = '{0}{1}'.format(REST, splunk_uri)
        session = Session()
        session.headers.update({
            'Authorization': 'Splunk {0!s}'.format(sesKey),
            'Content-Type': 'application/json',
            'User-Agent': 'KasperskyLab Splunk App'
        })
        session.verify = SPLUNK_REST_SSL
        retries = Retry(
            total=5,
            backoff_factor=0.5
        )
        session.mount('https://', adapters.HTTPAdapter(max_retries=retries))
        config = get_conf(splunk_url, session, logf)[0]
        return config
    except Exception, e:
        logf.write (str(e) + '\n')
        import traceback
        stack =  traceback.format_exc()
        logf.write(splunk.Intersplunk.generateErrorResults(str(e) + ". Traceback: " + str(stack)) + '\n')

def get_conf(splunk_url, session, logf):
    """get KL App settings"""
    parameters = {
            'limit': 50000,
            'skip': 0,
    }

    results = 1
    data = []
    while results > 0:
        r = session.get(splunk_url, params=parameters)

        if r.status_code == 200:
            results = len(r.json())
            data.extend(r.json())
        else:
            err = 'Failed to *get* collection. ({})'.format(r.text)
            logf.write (str(err) + '\n')
        parameters['skip'] += results  # update after results retrieved

    return data


def get_splunk_password(sesKey, log):
  """ get proxy password"""
  try:
    proxy_pass = ""
    splunk_uri = '/servicesNS/nobody/{0}/storage/passwords'.format(APP_NAME)
    splunk_url = '{0}{1}'.format(REST, splunk_uri)
    time.sleep(5)
    session = Session()
    session.headers.update({
            'Authorization': 'Splunk {0!s}'.format(sesKey),
            'Content-Type': 'application/json',
            'User-Agent': 'KasperskyLab Splunk App'})
    
    session.verify = SPLUNK_REST_SSL

    retries = Retry(total=5, backoff_factor=0.5)
    session.mount('https://', adapters.HTTPAdapter(max_retries=retries))

    parameters = {
            'output_mode': 'json',
            'count': -1
    }

    r = session.get(splunk_url, params=parameters)
    if r.status_code == 200:
        for entry in r.json().get('entry', []):
            if entry.get('content', {}).get('username') == 'proxyUser':
                proxy_pass = entry.get('content', {}).get('clear_password')
    else:
         err = 'Failed retrieving passwords. ({})'.format(r.text)
         log.write(str(err)+'\n')
    return proxy_pass
  except Exception, e:
        log.write (str(e) + '\n')


def save_in_configuration_file(settings, log):
    """save all settings in configuration file"""
    try:
        proxy_str = ""
        tree = ET.parse('kl_feed_for_splunk.conf')
        root = tree.getroot()
        IPrecordCount = root.find('IPRecordCount')
        IPrecordCount.text = str(settings['maxrecip'])
        UrlRecordCount = root.find('UrlRecordCount')
        UrlRecordCount.text = str(settings['maxrecurl'])
        HashRecordCount = root.find('HashRecordCount')
        HashRecordCount.text = str(settings['maxrechash'])
        if settings['proxyHost']:
            if settings['proxyUser']:
                proxy_str = settings['proxyUser'] + ':' + settings['ProxyPassword'] + '@' + settings['proxyHost'] + ':' + settings['proxyPort']
            else:
                proxy_str = settings['proxyHost'] + ':' + settings['proxyPort']
            proxy_str = xor(proxy_str, XOR_KEY).encode('base64')
        proxy = root.find('proxySettings')
        proxy.text = proxy_str
        tree.write('kl_feed_for_splunk.conf')
    except Exception, e:
        log.write (str(e) + '\n')


def xor(text, key):
    """encode proxy settings"""
    result = ''
    key_len = len(key)

    if (len(key) == 0):
        return text

    for i in range(len(text)):
        result += chr(ord(text[i]) ^ ord(key[i % key_len]))
    return result


results = KLSetSettings()
