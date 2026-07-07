# -*- coding: utf8 -*-

import os
import urllib
import json
import base64
import logging
import sys
import datetime
import hashlib
import csv
sys.path.append('lib')
from ConfigFile import *
from navigator import Navigator
from dateutil.tz import tzlocal
from dateutil import parser
from datetime import timedelta
from StringUtils import StringUtils
from urlparse import urlparse

__LOG_DIRECTORY = "logs"
__LOG_FILE = "{}/updateDBScript.log".format(__LOG_DIRECTORY)


class UpdateDB():

    __MESSAGES = {
        'no_last_update': "There is no `lastUpdate`",
        'last_updated_at': "Last DB update was at `{}`",
        'outdated_db': "Crime servers DB is outdated",
        'download_crime_servers': "Getting ALL online crime servers",
        'update_crime_servers': "Updating crime servers",
        'done': "Done!"
    }

    __BASE_END_POINT = '/v1/crimeserver'
    __ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    __END_POINTS = {
        'online': '/online',
        'recent': '/recent',
        'last': '/last'
    }

    def __to_iso_date(self, date):
        return parser.parse(date)

    def __check_if_has_to_be_executed(self, date1, date2):
        access_type = self.configuration.get_api_access_type()
        if access_type == "PAID":
            delta_ms = 14*60*1000
        else:
            delta_ms = 359*60*1000
        return (date1 - date2) >= timedelta(milliseconds=delta_ms)

    def __is_outdated(self, date1, date2, delta_ms):
        return (date1 - date2) > timedelta(milliseconds=delta_ms)

    def __get_endpoint(self):
        logger = logging.getLogger('__get_endpoint')

        now = datetime.datetime.now(tzlocal())
        now_str = now.strftime(self.__ISO_DATE_FORMAT)

        last_update = self.configuration.get_last_updated()
        if last_update is None:
            logger.info(self.__MESSAGES['no_last_update'])
            return self.__END_POINTS['online']
        else:
            last_update_date = self.__to_iso_date(last_update)
            if not self.__check_if_has_to_be_executed(now, last_update_date):
                logger.info("No new data available, last updated at {}".format(last_update_date))
                return None
            update_time = self.configuration.get_update_time()
            n_available_updates = self.configuration.get_available_updates()
            partially_outdated = self.__is_outdated(now,
                                                    last_update_date,
                                                    update_time * 2)
            fully_outdated = self.__is_outdated(now,
                                                last_update_date,
                                                update_time *
                                                n_available_updates)

            if fully_outdated:
                logger.info(self.__MESSAGES['outdated_db'])
                self.__delete_crime_servers_table()
                return self.__END_POINTS['online']
            elif partially_outdated:
                logger.info(self.__MESSAGES['last_updated_at'].format(
                    last_update_date))
                return self.__END_POINTS['recent']
            else:
                logger.info(self.__MESSAGES['last_updated_at'].format(
                    last_update_date))
                return self.__END_POINTS['last']

    def __download_and_update_crime_servers(self, url):
        logger = logging.getLogger('__download_and_update_crime_servers')
        response = self.download.go(url)
        if response is not '':
            output = csv.writer(sys.stdout, delimiter=',')
            output.writerow(['_key','url','domain','host','type','subtype','ip','asn','lat','lon','status','country','firstSeenAt','lastSeenAt'])
            try:
                for crimeServer in response['crimeServers']:
                    url = crimeServer["url"].encode('utf-8','replace') if "url" in crimeServer else ""
                    cs_type = crimeServer["type"].encode('utf-8','replace') if "type" in crimeServer else ""
                    cs_subType = crimeServer["subType"].encode('utf-8','replace') if "subType" in crimeServer else ""
                    status = crimeServer["status"].encode('utf-8','replace') if "status" in crimeServer else ""
                    ip = crimeServer["ip"].encode('utf-8','replace') if "ip" in crimeServer else ""
                    host = crimeServer["host"].encode('utf-8','replace') if "host" in crimeServer else ""
                    domain = crimeServer["domain"].encode('utf-8','replace') if "domain" in crimeServer else ""
                    asn = crimeServer["asnDesc"].encode('utf-8','replace') if "asnDesc" in crimeServer else ""
                    country = crimeServer["country"].encode('utf-8','replace') if "country" in crimeServer else ""
                    lat = crimeServer["latitude"] if "latitude" in crimeServer else ""
                    lon = crimeServer["longitude"] if "longitude" in crimeServer else ""
                    firstSeenAt = crimeServer["firstSeenAt"] if "firstSeenAt" in crimeServer else ""
                    lastSeenAt = crimeServer["lastSeenAt"] if "lastSeenAt" in crimeServer else ""
                    try:
                        if url != '' and host == '':
                            host = urlparse(url).hostname
                            host = host if host is not None else ''
                    except:
                        pass
                    key = self.__create_hash_id(url,ip,cs_type)
                    if key:
                        output.writerow([key,url,domain,host,cs_type,cs_subType,ip,asn,lat,lon,status,country,firstSeenAt,lastSeenAt])
                if 'meta' in response and 'updated' in response['meta']:
                    logger.info('Saving last update: {}'.format(response['meta']['updated']))
                    self.configuration.setLastUpdated(response['meta']['updated'])
                else:
                    logger.error('Could not save any updated date')
            except Exception as e:
                logger.error("Error saving data")
            

    def __create_hash_id(self, url, ip, cs_type):
        m = hashlib.md5()
        if url == '' and ip == '':
            return None
        elif url == '':
            m.update("#".join((ip, cs_type)))
        else:
            m.update("{}#{}".format(url,cs_type))
        
        key = m.hexdigest()
        
        return key

    def __init__(self):
        self.configuration = ConfigFile()
        self.base_url = self.configuration.get_api_url() + self.__BASE_END_POINT
        self.download = Navigator()

    def update(self):
        logger = logging.getLogger('update')
        endpoint = self.__get_endpoint()
        if endpoint:
            url = self.base_url + endpoint
            self.__download_and_update_crime_servers(url)
        logger.info(self.__MESSAGES['done'])

    def close(self):
        self.conn.close()

if __name__ == '__main__':
    if not os.path.exists(__LOG_DIRECTORY):
        os.makedirs(__LOG_DIRECTORY)
    logging.basicConfig(filename=__LOG_FILE, level=logging.DEBUG)
    db = UpdateDB()
    db.update()
