#!/usr/bin/env python
# coding=utf-8

__version__ = '1.1.13'

import sys
import urllib2
import ijson
import json
import optparse
import os
import re
import uuid
import zipfile
from contextlib import closing
import ssl
import socket
import httplib
import glob
import xml.etree.ElementTree as ET
import logging
import time
import datetime
import threading
import signal
import shutil

FEEDS_HOST = 'https://wlinfo.kaspersky.com'
FEEDS_LIST = '/api/v1.0/feeds'
FEEDS_PORT = 443
NETWORK_TIMEOUT = 15  # in seconds
LOCK_FILE = '.lockfile'
PEM_FILE = 'feeds.pem'
XOR_KEY = '#'
demo_feed = False
alive_threads = 0

if not sys.version_info >= (2, 7, 9):
    # hack way to force disable server certificate verification
    # urllib2 does not allow to pass this parameter "cert_reqs" outside
    def connect_patched(self):
        """Connect to a host on a given (SSL) port."""

        sock = socket.create_connection((self.host, self.port), self.timeout)
        if self._tunnel_host:
            self.sock = sock
            self._tunnel()
        self.sock = ssl.wrap_socket(sock, self.key_file, PEM_FILE, cert_reqs=ssl.CERT_NONE)

    httplib.HTTPSConnection.connect = connect_patched


def xor(text, key):
    """decode proxy settings """
    result = ''
    key_len = len(key)

    if not key:
        return text
    for i, char in enumerate(text):
        result += chr(ord(char) ^ ord(key[i % key_len]))
    return result


class Config(object):
    """Configuration class"""
    def __init__(self, config_path):
        self.conf_file = config_path
        self.download_dir = 'downloadDir'
        self.work_dir = 'workDir'
        self.logs_dir = ''
        self.proxy = ''
        self.org_proxy = ''
        self.ip_record_count = 200000
        self.url_record_count = 200000
        self.hash_record_count = 200000

        if not os.path.exists(config_path):
            return
        tree = ET.parse(config_path)
        root = tree.getroot()
        if root.tag != 'settings':
            raise Exception("Invalid configuration file: {0}".format(config_path))

        download_dir = tree.find('./SplunkLookupFilesDir')
        if download_dir is not None and download_dir.text is not None:
            self.download_dir = download_dir.text

        work_dir = tree.find('./workDir')
        if work_dir is not None and work_dir.text is not None:
            self.work_dir = work_dir.text

        logs_dir = tree.find('./logsDir')
        if logs_dir is not None:
            self.logs_dir = logs_dir.text

        proxy = tree.find('./proxySettings')
        if proxy is not None and proxy.text is not None:
            self.proxy = xor((proxy.text).decode("base64"), XOR_KEY)
            self.org_proxy = proxy.text

        ip_record_count = tree.find('./IPRecordCount')
        if ip_record_count is not None and ip_record_count.text is not None:
            self.ip_record_count = int(ip_record_count.text)

        url_record_count = tree.find('./UrlRecordCount')
        if url_record_count is not None and url_record_count.text is not None:
            self.url_record_count = int(url_record_count.text)

        hash_record_count = tree.find('./HashRecordCount')
        if hash_record_count is not None and hash_record_count.text is not None:
            self.hash_record_count = int(hash_record_count.text)


    def __str__(self):
        logging.info(u'Configuration:')
        logging.info(u'    configuration file = ' + self.conf_file)
        logging.info(u'    downloadDir = ' + self.download_dir)
        logging.info(u'    work_dir = ' + self.work_dir)
        logging.info(u'    logsDir = ' + self.logs_dir)
        logging.info(u'    proxy = ' + str(self.org_proxy))
        logging.info(u'    ip_record_count = ' + str(self.ip_record_count))
        logging.info(u'    url_record_count = ' + str(self.url_record_count))
        logging.info(u'    hash_record_count = ' + str(self.hash_record_count))
        return u'returned the current configuration'


def sigint_handler(sig, frame):
    """Handler for SIGINT"""
    print '\nYou have pressed Ctrl + C. Exiting...'
    logging.warning('WARN: Ctrl + C is handled. Exiting...')
    sys.exit(0)


def parse_filename(headers):
    """Parse filename from Content-Disposition header
       Expecting that header contains something like
       "attachment; filename=2015-07-14T182632.Phishing_URL_Data_Feed_140715_1826.zip"
    """
    if 'content-disposition' not in headers:
        # if Content-Disposition header is absent we should generate unique name
        logging.warning("WARN: Missing Content-Disposition header: failed to get package filename")
        filename = str(uuid.uuid4()) + ".zip"
        logging.warning("WARN: Using a randomly generated name: %s", filename)
        return filename
    return re.findall(r'filename=(\S+)', headers['content-disposition'])[0]


def download_package(opener, url, feeds_dir):
    """Download single package to feeds_dir"""
    logging.info("Download a feed package from %s", url)
    with closing(opener.open(url, timeout=NETWORK_TIMEOUT)) as response:
        logging.info('HTTP status code: %d', response.getcode())
        if response.getcode() != 200:
            e = Exception("ERROR: Failed to download package from '{0}'".format(url))
            logging.error(e)
            raise e

        package_name = parse_filename(response.headers)
        logging.info("Feed package name: %s", package_name)

        feed_package_path = os.path.join(feeds_dir, package_name)
        with open(feed_package_path, 'wb') as feed_archive:
            feed_archive.write(response.read())

        logging.info("Feed package was successfully downloaded to '%s'", feed_package_path)
        logging.info('Extracting...')
        with closing(zipfile.ZipFile(feed_package_path, 'r')) as feed_zip:
            feed_zip.extractall(feeds_dir)
        os.remove(feed_package_path)
        logging.info('Feed was successfully extracted')


def download_feed(opener, feed_name, feed_url, feeds_dir):
    """Downloads a single feed to feeds_dir"""
    try:
        logging.info("Downloading feed '%s' from %s", feed_name, feed_url)
        with closing(opener.open(feed_url, timeout=NETWORK_TIMEOUT)) as response:
            logging.info('HTTP status code: %d', response.getcode())
            if response.getcode() != 200:
                e = Exception("ERROR: Failed to download feed '{0}'".format(feed_name))
                logging.error(e)
                raise e

            result = json.loads(response.read())
            logging.info('Feed version: %s', result['updates'][0]['version'])
            package_url = result['updates'][0]['packages'][0]['link']
            logging.info('Feed link: %s', package_url)
            logging.info('Feed package size: %d',
                         result['updates'][0]['packages'][0]['size'])
            download_package(opener, package_url, feeds_dir)

    except urllib2.HTTPError, e:
        if e.code == 404:
            logging.error('ERROR: Invalid address. Check settings')
        elif e.code == 403:
            logging.error('ERROR: Permission denied')
        else:
            logging.error('ERROR: %s', str(e))
        raise
    except urllib2.URLError:
        logging.error('ERROR: Network error. Check network connection or certificate')
        raise
    else:
        logging.info("Feed '%s' was successfully downloaded to '%s'", feed_name, feeds_dir)


def get_available_feeds_list(opener, config):
    """Get feeds available for using certificate"""
    full_url = '{0}:{1}'.format(FEEDS_HOST + FEEDS_LIST, FEEDS_PORT)

    with closing(opener.open(FEEDS_HOST + FEEDS_LIST, timeout=NETWORK_TIMEOUT)) as response:
        logging.info('HTTP status code: %d', response.getcode())
        if response.getcode() != 200:
            e = Exception("ERROR: Failed to download feed '{0}'".format(feed_name))
            logging.error(e)
            raise e

        result = json.loads(response.read())
        for feed in result:
            feed_name = feed['name']
            logging.info("Feed %s avaliable for download", feed_name)
            feed_url = feed['updates']['href']
            download_feed(opener, feed_name, feed_url, config.work_dir)


def download(config):
    """Downloads all feeds to work_dir"""
    logging.info('Downloading feeds...')
    if os.path.exists(config.work_dir):
        if not os.access(config.work_dir, os.R_OK) or not os.access(config.work_dir, os.W_OK):
            e = Exception('ERROR: not enought rights to the workDir')
            logging.error(e)
            raise e
        logging.info('Removing feeds in workDir: %s', config.work_dir)
        for feed in glob.glob(config.work_dir + '/*_Data_Feed_*_*.json'):
            os.remove(feed)
    else:
        os.makedirs(config.work_dir)
    if os.path.exists(config.download_dir):
        if not os.access(config.download_dir, os.R_OK) or not os.access(config.download_dir, os.W_OK):
            e = Exception('ERROR: not enought rights to the downloadDir')
            logging.error(e)
            raise e
    else:
        os.makedirs(config.download_dir)

    logging.info('Connecting to %s:%d', FEEDS_HOST, FEEDS_PORT)
    logging.info('PEM file: %s', PEM_FILE)
    if sys.version_info >= (2, 7, 9):
        # since 2.7.9 version Python performs certificate and hostname checks by default
        ctx = ssl._create_unverified_context()
        ctx.load_cert_chain(certfile=PEM_FILE)
        https_handler = urllib2.HTTPSHandler(context=ctx)
    else:
        https_handler = urllib2.HTTPSHandler()

    opener = urllib2.build_opener(https_handler)
    try:
        get_available_feeds_list(opener, config)
        logging.info('Download process finished')
    finally:
        opener.close()


def read_ransomware_feed(feed_path, feed_name, config):
    """Parses Ransomware URL DF"""
    logging.info("Transforming feed '%s'...", feed_name)
    count = 0
    hashcount = 0
    global alive_threads
    try:
        csv_url = open(config.work_dir + '//' + feed_name + "_URL.csv", 'w')
        csv_url.write("kl_url,kl_first_seen,kl_popularity\n")
        csv_host = open(config.work_dir + '//' + feed_name + "_HOST.csv", 'w')
        csv_host.write("kl_host,kl_first_seen,kl_popularity\n")
        csv_domain = open(config.work_dir + '//' + feed_name + "_DOMAIN.csv", 'w')
        csv_domain.write("kl_domain,kl_first_seen,kl_popularity\n")
        csv_md = open(config.work_dir + '//' + feed_name + "_MD5.csv", 'w')
        csv_shai = open(config.work_dir + '//' + feed_name + "_SHA1.csv", 'w')
        csv_shaii = open(config.work_dir + '//' + feed_name + "_SHA2.csv", 'w')
        csv_md.write("kl_hash,kl_first_seen,kl_popularity\n")
        csv_shai.write("kl_hash,kl_first_seen,kl_popularity\n")
        csv_shaii.write("kl_hash,kl_first_seen,kl_popularity\n")
        with open(feed_path) as feed:
            for it in ijson.items(feed, 'item'):
                if config.url_record_count != 0 and config.url_record_count == count:
                    break;
                count += 1
                context = it['first_seen'] + ","
                context += str(it['popularity'])
                if it['type'] == 1:
                    csv_domain.write(it['mask'] + ',' + context + '\n')
                if it['type'] == 2:
                    csv_host.write(it['mask'] + ',' + context + '\n')
                if it['type'] == 4:
                    if "\"" not in it['mask']:#if URL contains " , it can make whole lookup-file incorrect 
                        csv_url.write(it['mask'] + ',' + context + '\n')
                if 'files' in it:
                    for files in it['files']:
                        if (config.hash_record_count != 0 and config.hash_record_count > hashcount) or config.hash_record_count == 0:
                            hashcount += 1
                            temp_indicator = files.get('MD5', False)
                            if temp_indicator:
                                csv_md.write(temp_indicator + ',' + context + '\n')
                            temp_indicator = files.get('SHA1', False)
                            if temp_indicator:
                                csv_shai.write(temp_indicator + ',' + context + '\n')
                            temp_indicator = files.get('SHA256', False)
                            if temp_indicator:
                                csv_shaii.write(temp_indicator + ',' + context + '\n')
        logging.info("finished transform %s", feed_name)
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise
    finally:
        csv_url.close()
        logging.info("%s saved", feed_name + "_URL.csv")
        csv_host.close()
        logging.info("%s saved", feed_name + "_HOST.csv")
        csv_domain.close()
        logging.info("%s saved", feed_name + "_DOMAIN.csv")
        csv_md.close()
        logging.info("%s saved", feed_name + "_MD5.csv")
        csv_shai.close()
        logging.info("%s saved", feed_name + "_SHA1.csv")
        csv_shaii.close()
        logging.info("%s saved", feed_name + "_SHA2.csv")
        alive_threads -= 1


def read_hash_feed(feed_path, feed_name, config):
    """Parses Malicious Hash and Mobile Hash DF"""
    logging.info("Transforming feed '%s'...", feed_name)
    count = 0
    global alive_threads
    try:
        csv_md = open(config.work_dir + '//' + feed_name + "_MD5.csv", 'w')
        csv_shai = open(config.work_dir + '//' + feed_name + "_SHA1.csv", 'w')
        csv_shaii = open(config.work_dir + '//' + feed_name + "_SHA2.csv", 'w')
        csv_md.write("kl_hash,kl_first_seen,kl_popularity,kl_threat\n")
        csv_shai.write("kl_hash,kl_first_seen,kl_popularity,kl_threat\n")
        csv_shaii.write("kl_hash,kl_first_seen,kl_popularity,kl_threat\n")
        with open(feed_path) as feed:
            for it in ijson.items(feed, 'item'):
                if config.hash_record_count != 0 and config.hash_record_count == count:
                    break;
                count += 1
                context = it['first_seen'] + ","
                context += str(it['popularity']) + ","
                context += str(it['threat'])
                hash = it['MD5']
                csv_md.write(hash + ',' + context + '\n')
                temp_indicator = it.get('SHA1', False)
                if temp_indicator:
                    csv_shai.write(temp_indicator + ',' + context + '\n')
                temp_indicator = it.get('SHA256', False)
                if temp_indicator:
                    csv_shaii.write(temp_indicator + ',' + context + '\n')
        logging.info("finished transform %s", feed_name)
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise
    finally:
        csv_md.close()
        logging.info("%s saved", feed_name + "_MD5.csv")
        csv_shai.close()
        logging.info("%s saved", feed_name + "_SHA1.csv")
        csv_shaii.close()
        logging.info("%s saved", feed_name + "_SHA2.csv")
        alive_threads -= 1


def read_mobile_botnet_feed(feed_path, feed_name, config):
    """Parses MobileBotnet DF"""
    logging.info("Transforming feed '%s'...", feed_name)
    count = 0
    global alive_threads
    try:
        csv_url = open(config.work_dir + '//' + feed_name + "_URL.csv", 'w')
        csv_url.write("kl_url,kl_verdict\n")
        csv_host = open(config.work_dir + '//' + feed_name + "_HOST.csv", 'w')
        csv_host.write("kl_host,kl_verdict\n")
        csv_domain = open(config.work_dir + '//' + feed_name + "_DOMAIN.csv", 'w')
        csv_domain.write("kl_domain,kl_verdict\n")
        csv_md = open(config.work_dir + '//' + feed_name + "_MD5.csv", 'w')
        csv_md.write("kl_hash,kl_verdict\n")
        with open(feed_path) as feed:
            for it in ijson.items(feed, 'item'):
                if config.hash_record_count != 0 and config.hash_record_count == count:
                    break;
                count += 1
                context = it['verdict']
                hash = it['MD5']
                csv_md.write(hash + ',' + context + '\n')
                if 'Details' in it:
                    for masks in it['Details']:
                        mask = masks['Mask']
                        if "/" in mask:
                            if "\"" not in mask:
                                csv_url.write(mask + ',' + context + '\n')
                        elif mask.count('.') > 1:
                            csv_host.write(mask + ',' + context + '\n')
                        else:
                            csv_domain.write(mask + ',' + context + '\n')
        logging.info("finished transform %s", feed_name)
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise
    finally:
        csv_url.close()
        logging.info("%s saved", feed_name + "_URL.csv")
        csv_host.close()
        logging.info("%s saved", feed_name + "_HOST.csv")
        csv_domain.close()
        logging.info("%s saved", feed_name + "_DOMAIN.csv")
        csv_md.close()
        logging.info("%s saved", feed_name + "_MD5.csv")
        alive_threads -= 1


def read_url_feed(feed_path, feed_name, config):
    """Parses KL Phishing and Malicious URL Data Feed"""
    logging.info("Transforming feed '%s'...", feed_name)
    count = 0
    hashcount = 0
    threat_name = ""
    global alive_threads
    try:
        csv_url = open(config.work_dir + '//' + feed_name + "_URL.csv", 'w')
        csv_host = open(config.work_dir + '//' + feed_name + "_HOST.csv", 'w')
        csv_domain = open(config.work_dir + '//' + feed_name + "_DOMAIN.csv", 'w')
        if "Malicious" in feed_name:
            csv_url.write("kl_url,kl_first_seen,kl_popularity,kl_category\n")
            csv_host.write("kl_host,kl_first_seen,kl_popularity,kl_category\n")
            csv_domain.write("kl_domain,kl_first_seen,kl_popularity,kl_category\n")
            csv_md = open(config.work_dir + '//' + feed_name + "_MD5.csv", 'w')
            csv_shai = open(config.work_dir + '//' + feed_name + "_SHA1.csv", 'w')
            csv_shaii = open(config.work_dir + '//' + feed_name + "_SHA2.csv", 'w')
            csv_md.write("kl_hash,kl_first_seen,kl_popularity,kl_category,kl_threat\n")
            csv_shai.write("kl_hash,kl_first_seen,kl_popularity,kl_category,kl_threat\n")
            csv_shaii.write("kl_hash,kl_first_seen,kl_popularity,kl_category,kl_threat\n")
        else:
            csv_url.write("kl_url,kl_first_seen,kl_popularity\n")
            csv_host.write("kl_host,kl_first_seen,kl_popularity\n")
            csv_domain.write("kl_domain,kl_first_seen,kl_popularity\n")
        with open(feed_path) as feed:
            for it in ijson.items(feed, 'item'):
                if config.url_record_count != 0 and config.url_record_count == count:
                    break;
                count += 1
                context = it['first_seen'] + ","
                context += str(it['popularity'])
                category = it.get('category', False)
                if category:
                     context += "," + category
                if 'urls' in it:
                    for urls in it['urls']:
                        if "\"" not in urls['url']:
                            csv_url.write(urls['url'] + ',' + context + '\n')
                if 'hosts' in it:
                    for hosts in it['hosts']:
                        csv_host.write(hosts['host'] + ',' + context + '\n')
                if 'domains' in it:
                    for domains in it['domains']:
                        csv_domain.write(domains['domain'] + ',' + context + '\n')
                if 'files' in it:
                    for files in it['files']:
                        if (config.hash_record_count != 0 and config.hash_record_count > hashcount) or config.hash_record_count == 0:
                            hashcount += 1
                            threat_name = files.get('threat', False)
                            if threat_name:
                                threat_name = "," + str(threat_name)
                            else:
                                threat_name = ",-"
                            temp_indicator = files.get('MD5', False)
                            if temp_indicator:
                                csv_md.write(temp_indicator + ',' + context + threat_name  + '\n')
                            temp_indicator = files.get('SHA1', False)
                            if temp_indicator:
                                csv_shai.write(temp_indicator + ',' + context + threat_name  +  '\n')
                            temp_indicator = files.get('SHA256', False)
                            if temp_indicator:
                                csv_shaii.write(temp_indicator + ',' + context + threat_name  +  '\n')
        logging.info("finished transform %s", feed_name)
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise
    finally:
        csv_url.close()
        logging.info("%s saved", feed_name + "_URL.csv")
        csv_host.close()
        logging.info("%s saved", feed_name + "_HOST.csv")
        csv_domain.close()
        logging.info("%s saved", feed_name + "_DOMAIN.csv")
        if "Malicious" in feed_name:
            csv_md.close()
            logging.info("%s saved", feed_name + "_MD5.csv")
            csv_shai.close()
            logging.info("%s saved", feed_name + "_SHA1.csv")
            csv_shaii.close()
            logging.info("%s saved", feed_name + "_SHA2.csv")
        alive_threads -= 1


def read_botnet_url_feed(feed_path, feed_name, config):
    """Parses KL BotnetCnC URL Data Feed"""
    global demo_feed
    logging.info("Transforming feed '%s'...", feed_name)
    count = 0
    hashcount = 0
    global alive_threads
    try:
        feed_name = "Botnet_CnC_URL_Exact_Data_Feed"
        csv_url = open(config.work_dir + '//' + feed_name + "_URL.csv", 'w')
        csv_url.write("kl_url,kl_first_seen,kl_popularity,kl_threat\n")
        csv_host = open(config.work_dir + '//' + feed_name + "_HOST.csv", 'w')
        csv_host.write("kl_host,kl_first_seen,kl_popularity,kl_threat\n")
        csv_domain = open(config.work_dir + '//' + feed_name + "_DOMAIN.csv", 'w')
        csv_domain.write("kl_domain,kl_first_seen,kl_popularity,kl_threat\n")
        csv_md = open(config.work_dir + '//' + feed_name + "_MD5.csv", 'w')
        csv_shai = open(config.work_dir + '//' + feed_name + "_SHA1.csv", 'w')
        csv_shaii = open(config.work_dir + '//' + feed_name + "_SHA2.csv", 'w')
        csv_md.write("kl_hash,kl_first_seen,kl_popularity,kl_threat\n")
        csv_shai.write("kl_hash,kl_first_seen,kl_popularity,kl_threat\n")
        csv_shaii.write("kl_hash,kl_first_seen,kl_popularity,kl_threat\n")
        with open(feed_path) as feed:
            for it in ijson.items(feed, 'item'):
                if config.url_record_count != 0 and config.url_record_count == count:
                    break;
                count += 1
                context = it['first_seen'] + ","
                context += str(it['popularity']) + ","
                context += str(it['threat'])
                if demo_feed:
                    if it['type'] == 1:
                        csv_domain.write(it['mask'] + ',' + context + '\n')
                    if it['type'] == 2:
                        csv_host.write(it['mask'] + ',' + context + '\n')
                    if it['type'] == 4:
                        if "\"" not in it['mask']:
                            csv_url.write(it['mask'] + ',' + context + '\n')
                else:
                    if 'urls' in it:
                        for urls in it['urls']:
                            if "\"" not in urls['url']:
                                csv_url.write(urls['url'] + ',' + context + '\n')
                    if 'hosts' in it:
                        for hosts in it['hosts']:
                            csv_host.write(hosts['host'] + ',' + context + '\n')
                    if 'domains' in it:
                        for domains in it['domains']:
                            csv_domain.write(domains['domain'] + ',' + context + '\n')
                if 'files' in it:
                    for files in it['files']:
                        if (config.hash_record_count != 0 and config.hash_record_count > hashcount) or config.hash_record_count == 0:
                            hashcount += 1
                            temp_indicator = files.get('MD5', False)
                            if temp_indicator:
                                csv_md.write(temp_indicator + ',' + context + '\n')
                            temp_indicator = files.get('SHA1', False)
                            if temp_indicator:
                                csv_shai.write(temp_indicator + ',' + context + '\n')
                            temp_indicator = files.get('SHA256', False)
                            if temp_indicator:
                                csv_shaii.write(temp_indicator + ',' + context + '\n')
        logging.info("finished transform %s", feed_name)
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise
    finally:
        csv_url.close()
        logging.info("%s saved", feed_name + "_URL.csv")
        csv_host.close()
        logging.info("%s saved", feed_name + "_HOST.csv")
        csv_domain.close()
        logging.info("%s saved", feed_name + "_DOMAIN.csv")
        csv_md.close()
        logging.info("%s saved", feed_name + "_MD5.csv")
        csv_shai.close()
        logging.info("%s saved", feed_name + "_SHA1.csv")
        csv_shaii.close()
        logging.info("%s saved", feed_name + "_SHA2.csv")
        alive_threads -= 1


def read_ip_feed(feed_path, feed_name, config):
    """Parses KL IP Reputation Data Feed"""
    logging.info("Transforming feed '%s'...", feed_name)
    count = 0
    hashcount = 0
    threat_name = ""
    global alive_threads
    try:
        csv_ip = open(config.work_dir + '//' + feed_name + ".csv", 'w')
        csv_ip.write("kl_ip,kl_threat_score,kl_category,kl_first_seen,kl_popularity\n")
        csv_md = open(config.work_dir + '//' + feed_name + "_MD5.csv", 'w')
        csv_shai = open(config.work_dir + '//' + feed_name + "_SHA1.csv", 'w')
        csv_shaii = open(config.work_dir + '//' + feed_name + "_SHA2.csv", 'w')
        csv_md.write("kl_hash,kl_threat_score,kl_category,kl_first_seen,kl_popularity,kl_threat\n")
        csv_shai.write("kl_hash,kl_threat_score,kl_category,kl_first_seen,kl_popularity,kl_threat\n")
        csv_shaii.write("kl_hash,kl_threat_score,kl_category,kl_first_seen,kl_popularity,kl_threat\n")
        with open(feed_path) as feed:
            for it in ijson.items(feed, 'item'):
                if config.ip_record_count != 0 and config.ip_record_count == count:
                    break;
                count += 1
                context = str(it['threat_score']) + ","
                context += str(it['category']).replace(",", "and") + ","
                context += str(it['first_seen']) + ","
                context += str(it['popularity'])
                csv_ip.write(it['ip'] + ',' + context + '\n')
                if 'files' in it:
                    for files in it['files']:
                        if (config.hash_record_count != 0 and config.hash_record_count > hashcount) or config.hash_record_count == 0:
                            hashcount += 1
                            threat_name = files.get('threat', False)
                            if  threat_name:
                                 threat_name = "," + str(threat_name)
                            else:
                                 threat_name  = ",-"
                            temp_indicator = files.get('MD5', False)
                            if temp_indicator:
                                csv_md.write(temp_indicator + ',' + context + threat_name  +  '\n')
                            temp_indicator = files.get('SHA1', False)
                            if temp_indicator:
                                csv_shai.write(temp_indicator + ',' + context + threat_name  +  '\n')
                            temp_indicator = files.get('SHA256', False)
                            if temp_indicator:
                                csv_shaii.write(temp_indicator + ',' + context + threat_name  +  '\n')
        logging.info("finished transform %s", feed_name)
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise
    finally:
        csv_ip.close()
        logging.info("%s saved", feed_name + ".csv")
        csv_md.close()
        logging.info("%s saved", feed_name + "_MD5.csv")
        csv_shai.close()
        logging.info("%s saved", feed_name + "_SHA1.csv")
        csv_shaii.close()
        logging.info("%s saved", feed_name + "_SHA2.csv")
        alive_threads -= 1


def read_psms_feed(feed_path, feed_name, config):
    """Parses KL IP P-SMS Data Feed"""
    logging.info("Transforming feed '%s'...", feed_name)
    count = 0
    global alive_threads
    try:
        csv_md = open(config.work_dir + '//' + feed_name + "_MD5.csv", 'w')
        csv_md.write("kl_hash,kl_av_verdict,kl_date\n")
        with open(feed_path) as feed:
            for it in ijson.items(feed, 'item'):
                if config.hash_record_count != 0 and config.hash_record_count == count:
                    break;
                count += 1
                context = str(it['AV Verdict']) + ","
                context += str(it['Date']) + ","
                csv_md.write(it['MD5'] + ',' + context + '\n')
        logging.info("finished transform %s", feed_name)
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise
    finally:
        csv_md.close()
        logging.info("%s saved", feed_name + "_MD5.csv")
        alive_threads -= 1


def processing_feeds(config):
    """Processes and convert KL Data Feed for Splunk"""
    global alive_threads
    try:
        logging.info('Processing feeds for Splunk')
        feed_list = get_feed_list(config)
        start_thread = False
        for feed in feed_list:
            logging.info('Starting process %s', feed)
            if "Ransomware" in feed:
                thread =  threading.Thread(target=read_ransomware_feed,name="read_ransomware_feed", args=(feed_list[feed], feed, config,))
                start_thread = True
            elif "Mobile_Botnet" in feed:
                thread =  threading.Thread(target=read_mobile_botnet_feed, name="read_mobile_botnet_feed", args=(feed_list[feed], feed, config,))
                start_thread = True
            elif "Botnet_C&C_URL" in feed:
                thread =  threading.Thread(target=read_botnet_url_feed, name="read_botnet_url_feed", args=(feed_list[feed], feed, config,))
                start_thread = True
            elif "Malicious_URL" in feed or "Phishing_URL" in feed:
                thread =  threading.Thread(target=read_url_feed, name="read_url_feed", args=(feed_list[feed], feed, config,))
                start_thread = True
            elif "Malicious_Hash" in feed or "Mobile_Malicious" in feed:
                thread =  threading.Thread(target=read_hash_feed, name="read_hash_feed", args=(feed_list[feed], feed, config,))
                start_thread = True
            elif "IP_Reputation" in feed:
                thread =  threading.Thread(target=read_ip_feed, name="read_ip_feed", args=(feed_list[feed], feed, config,))
                start_thread = True
            elif "P-SMS" in feed:
                thread =  threading.Thread(target=read_psms_feed, name="read_psms_feed", args=(feed_list[feed], feed, config,))
                start_thread = True
            if start_thread:
                thread.deamon = True
                alive_threads += 1
                thread.start()
                start_thread = False
        while alive_threads > 0:
            logging.info("still some alive threads")
            time.sleep(600)
        for feed in feed_list:
            os.remove(feed_list[feed])
        copy_lookups(config)
        logging.info('Successfully finished processing feeds for Splunk')
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise


def copy_lookups(config):
    """Copy lookup files from workDir to SplunkLookupFilesDir"""
    try:
        logging.info('Start copy lookup files to %s', config.download_dir)
        lookups_paths = glob.glob(config.work_dir + '/*.csv')
        reg_exp = '(?:(?:[^=]+\/)*)(.*?)(?:$)'
        for lookup_f in lookups_paths:
            filename = re.search(reg_exp, lookup_f)
            shutil.copy(lookup_f, config.download_dir + '//' + filename.group(1))
            logging.info('Copied %s', filename.group(1))
            os.remove(lookup_f)
        logging.info('Successfully copied all lookup files')
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise


def get_feed_list(config):
    """Get all feeds in downloadDir and downloadDemoDir"""
    global demo_feed
    feed_list = {}
    reg_exp = '(?:(?:[^=]+\/)*)(?:Demo_|)(.*?)(?:\_\d+)'
    feed_paths = glob.glob(config.work_dir + '/*Data_Feed_*_*.json')
    for feed_path in feed_paths:
        feed_name = re.search(reg_exp, feed_path)
        if "Demo_" in feed_path:
            demo_feed = True
        feed_list.update([(feed_name.group(1), feed_path)])
    return feed_list


def initialize_logging(config):
    """Initializes logging if it is enabled in the configuration file"""
    try:
        if not config.logs_dir or config.logs_dir == '':
            logging.disable(logging.CRITICAL)
            return
        if not os.path.exists(config.logs_dir):
            os.makedirs(config.logs_dir)
        else:
            old_logs = glob.glob(config.logs_dir + '/kl_feed_for_splunk*.log')
            for old_log in old_logs:
                os.remove(old_log)
        logfile = datetime.datetime.now().strftime('kl_feed_for_splunk_' + str(os.getpid()) + '_%d%m%Y_%H%M%S.log')
        logging.basicConfig(datefmt='%d.%m.%Y %H:%M:%S', format=u'%(asctime)s.%(msecs)03d %(filename)s:%(lineno)d %(threadName)s %(message)s', level=logging.INFO, filename=config.logs_dir + '/' + logfile, filemode='a')
        logging.info('kl_feed_for_splunk Version: {0}'.format(__version__))
        logging.info(str(config))
    except Exception as e:
        logging.error("ERROR: " + str(e))
        raise


def check_proxy(config):
    """check configuration file"""
    if config.proxy:
        proxy = re.search(r'^(?:\S+\:\S+\@|)(\S+)\:(\d+)(?:$)', config.proxy)
        if not proxy:
            logging.error('incorrect format of proxy')
            return False
    return True


def clean_dir(config):
    """ remove all feeds after work of kl_feed_for_splunk"""
    feed_paths = glob.glob(config.work_dir + '/*Data_Feed*.*')
    for feed_path in feed_paths:
        logging.info('removing %s', feed_path)
        os.remove(feed_path)


def check_proc():
    """Check proc from previous launch for live"""
    try:
        logging.info("check that another instance of kl_feed_for_splunk is working")
        with open(LOCK_FILE, 'r') as lock:
            pid = lock.readline()
            logging.info('check process %s', pid)
            return os.getpgid(int(pid))
    except OSError as e:
        return False


def main():
    """Main function"""
    try:
        reload(sys)
        sys.setdefaultencoding('utf-8')
        signal.signal(signal.SIGINT, sigint_handler)

        os.chdir(os.path.dirname(os.path.realpath(__file__)))

        parser = optparse.OptionParser()
        parser.add_option('--conf',
                          help="Path to configuration file",
                          default='kl_feed_for_splunk.conf')
        args, _ = parser.parse_args()
        if args.conf:
            if not (os.path.exists(args.conf) or os.path.isfile(args.conf)):
                raise Exception('Invalid path to configuration file')
            else:
                config = Config(args.conf)

        initialize_logging(config)

        if os.path.exists(LOCK_FILE):
            if check_proc():
                e = Exception("An instance of the kl_feed_for_splunk is already running")
                logging.error(e)
                raise e
            else:
                logging.info("another instance of kl_feed_for_splunk doesn't work")
                logging.info("removing lock-file from previous launch")
                os.remove(LOCK_FILE)

        logging.info("creating lock-file")
        with open(LOCK_FILE, 'a') as lock:
            lock.write(str(os.getpid()))

        if not check_proxy(config):
            e = Exception('Invalid proxy format')
            logging.error(e)
            raise e

        if config.proxy and (not os.environ.has_key('HTTPS_PROXY') or not os.environ['HTTPS_PROXY']):
            logging.info("Setting proxy settings")
            os.environ['HTTPS_PROXY'] = "https://" + config.proxy

        if not os.path.isfile(PEM_FILE):
            e = Exception("ERROR: PEM certificate was not found at {0}".format(PEM_FILE))
            logging.error(e)
            raise e
        download(config)
        logging.info(u'Finished downloading')

        processing_feeds(config)
        logging.info(u'All feeds were transformed successfully')
        print "Kaspersky_Threat_Feed_App_for_Splunk: All Kaspersky Lab Data Feeds were transformed successfully"
        return 0
    except ssl.SSLError:
        e = "\nERROR: PEM certificate {0} is invalid".format(PEM_FILE)
        logging.error(e)
        print "Kaspersky_Threat_Feed_App_for_Splunk: Error while downloading Kaspersky Lab Data Feeds: pem certificate is invalid"
        return 1
    except ET.ParseError as e:
        e = "\nIncorrect configuration file: {0}".format(e)
        print "Kaspersky_Threat_Feed_App_for_Splunk: Error while downloading Kaspersky Lab Data Feeds: configuration file is invalid"
        return 1
    except Exception as e:
        print "Kaspersky_Threat_Feed_App_for_Splunk: Error while downloading Kaspersky Lab Data Feeds: " + str(e)
        return 1
    finally:
        if os.path.exists(LOCK_FILE):
            with open(LOCK_FILE, 'r') as lock:
                if str(os.getpid()) in lock:
                    os.remove(LOCK_FILE)
                    logging.info('The lock-file was removed')
                    clean_dir(config)

if __name__ == '__main__':
    sys.exit(main())
