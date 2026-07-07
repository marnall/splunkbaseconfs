#!/usr/bin/env python


import os
import sys
from datetime import datetime
import logging
import logging.handlers

currentdir = os.path.dirname(os.path.abspath(__file__))
reportsdir = os.path.normpath(os.path.abspath(currentdir + '/../reports/'))

# create logger
LOG_FILENAME = os.path.normpath(currentdir +'/ssl-framework-report.log')
logger = logging.getLogger('clear-old-reports')
logger.setLevel(logging.INFO)
handler = logging.handlers.RotatingFileHandler(LOG_FILENAME, maxBytes=5242880, backupCount=4)
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s [%(name)s]: %(message)s'))
logger.addHandler(handler)

#logger.info('Current dir:'+currentdir)
#logger.info('Reports dir:'+reportsdir)

def calc_date_diff(utc_datetime):
    utc_datetime = datetime.utcfromtimestamp(utc_datetime)
    utc_date = datetime.date(utc_datetime)
    utc_now = datetime.now().date()
    diff = (utc_now - utc_date).days
    if diff < 0:
        diff = 0
    return diff

try:
    for file in os.listdir(reportsdir):
        if file.endswith('.log'):
            filepath = reportsdir + '/' + file
            age = calc_date_diff(os.path.getctime(filepath))
            if age > 2:
                logger.info('{0}, age={1}, deleting...'.format(file, age))
                os.remove(filepath)
                logger.info('{0}, succesfully deleted'.format(file))
            else:
                logger.info('{0}, age={1}, skip.'.format(file, age))
except Exception as e:
    logger.error(str(e))