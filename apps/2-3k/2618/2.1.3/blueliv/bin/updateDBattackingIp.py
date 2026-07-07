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
#sys.path.append('lib')
from lib.utils import write_to_csv_nested_objects
from ConfigFile import *
from navigator import Navigator
from dateutil.tz import tzlocal
from dateutil import parser
from datetime import timedelta
from StringUtils import StringUtils

__LOG_DIRECTORY = "logs"
__LOG_FILE = "{}/updateDBScript.log".format(__LOG_DIRECTORY)


class UpdateDB():

    __MESSAGES = {
        'no_last_update': "There is no `lastUpdate`",
        'last_updated_at': "Last DB update was at `{}`",
        'outdated_db': "Attacking IPs DB is outdated",
        'done': "Done!"
    }

    __BASE_END_POINT = '/v1/attack'
    __ISO_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"
    __END_POINTS = {
        'recent': '/recent',
        'last': '/last'
    }

    __HEADER = [
        "_key",
        "attackType",
        "firstEvent",
        "lastEvent",
        "numEvents",
        "source.ip",
        "source.country",
        "source.city",
        "source.port",
        "source.latitude",
        "source.longitude",
        "destination.port",
        "destination.serviceName",
        "destination.country",
        "destination.latitude",
        "destination.longitude",
        "createdAt"
    ]

    def __to_iso_date(self, date):
        return parser.parse(date)

    def __check_if_has_to_be_executed(self, date1, date2):
        access_type = self.configuration.get_api_access_type()
        delta_ms = 29*60*1000
        return (date1 - date2) >= timedelta(milliseconds=delta_ms)

    def __is_outdated(self, date1, date2, delta_ms):
        return (date1 - date2) > timedelta(milliseconds=delta_ms)

    def __get_endpoint(self):
        logger = logging.getLogger('__get_endpoint')

        now = datetime.datetime.now(tzlocal())
        now_str = now.strftime(self.__ISO_DATE_FORMAT)

        last_update = self.configuration.get_last_updated_attacks()
        if last_update is None:
            logger.info(self.__MESSAGES['no_last_update'])
            return self.__END_POINTS['recent']
        else:
            last_update_date = self.__to_iso_date(last_update)
            if not self.__check_if_has_to_be_executed(now, last_update_date):
                logger.info("No new data available, last updated at {}".format(last_update_date))
                return None
            update_time = self.configuration.get_update_time_attacks()
            partially_outdated = self.__is_outdated(now,
                                                    last_update_date,
                                                    update_time * 2)

            if partially_outdated:
                logger.info(self.__MESSAGES['last_updated_at'].format(
                    last_update_date))
                return self.__END_POINTS['recent']
            else:
                logger.info(self.__MESSAGES['last_updated_at'].format(
                    last_update_date))
                return self.__END_POINTS['last']

    def __download_and_update_attack_ips(self, url):
        logger = logging.getLogger('__download_and_update_attack_ips')
        response = self.download.go(url)
        output = csv.DictWriter(sys.stdout, delimiter=',', quotechar='"', fieldnames=[h.replace(".","") for h in self.__HEADER])
        try:
            write_to_csv_nested_objects(output, response.get("attacks", []), self.__HEADER, "_id")
            if 'meta' in response and 'updated' in response['meta']:
                logger.info('Saving last update: {}'.format(response['meta']['updated']))
                self.configuration.setLastUpdatedAttacks(response['meta']['updated'])
            else:
                logger.error('Could not save any updated date')
        except Exception as e:
            logger.error("Error: {}".format(e))

    def __create_hash_id(self, ip, portalUrl, seenAt, url):
        logger = logging.getLogger('__create_hash_id')
        key = None
        try:
            m = hashlib.md5()
            m.update("{}{}{}{}".format(ip, portalUrl, seenAt, url))
            key = m.hexdigest()
        except:
            logger.error("Error generating hash for {}".format(ip))
        
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
            self.__download_and_update_attack_ips(url)
        logger.info(self.__MESSAGES['done'])

    def close(self):
        self.conn.close()

if __name__ == '__main__':
    if not os.path.exists(__LOG_DIRECTORY):
        os.makedirs(__LOG_DIRECTORY)
    logging.basicConfig(filename=__LOG_FILE, level=logging.DEBUG)
    db = UpdateDB()
    db.update()
