#!/usr/bin/env python2.7
__author__ = 'Michael Uschmann / MuS'
__date__ = 'Copyright $Aug 25, 2017 7:48:46 PM$'
__version__ = '1.2.4'

import sys
import os
import json
import random
import urllib2
import splunk.Intersplunk
import logging.handlers
import xml.dom.minidom
import xml.sax.saxutils
import collections
from datetime import datetime
from ConfigParser import SafeConfigParser
from optparse import OptionParser

# get SPLUNK_HOME form OS
SPLUNK_HOME = os.environ['SPLUNK_HOME']

# get myScript name and path
myScript = os.path.basename(__file__)
myPath = os.path.dirname(os.path.realpath(__file__))

# define the logger to write into log file
def setup_logging(n):
    logger = logging.getLogger(n)
    if myDebug == 'yes':
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.ERROR)
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(
        SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = '%s.log' % myScript
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = '%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s'
    splunk_log_handler = logging.handlers.RotatingFileHandler(
        os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE,
                             LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger


# set path to inputs.conf file
try:  # lets do it
    # do we have a local inputs.conf?
    if os.path.isfile(os.path.join(myPath, '..', 'local', 'inputs.conf')):
        configLocalFileName = os.path.join(
            myPath, '..', 'local', 'inputs.conf')  # use it
    else:
        configLocalFileName = os.path.join(
            myPath, '..', 'default', 'inputs.conf')  # use the default one
    parser = SafeConfigParser()  # setup parser to read the inputs.conf
    parser.read(configLocalFileName)  # read inputs.conf options
    # if empty use settings from [default] stanza in inputs.conf
    if not os.path.exists(configLocalFileName):
        splunk.Intersplunk.generateErrorResults(
            ': No config found! Check your inputs.conf in local.')  # print the error into Splunk UI
        exit(0)  # exit on error
    debug_section_name = 'myGet://debug setting'
    myDebug = parser.get(debug_section_name, 'debug')
    # start the logger for troubleshooting
    logger = setup_logging('inputs.conf read, starting logger ...')  # logger

except Exception, e:  # get error back
    logger.error(
        'ERROR: No config found! Check your inputs.conf in local.')  # logger
    logger.error('ERROR: %e' % e)  # logger
    splunk.Intersplunk.generateErrorResults(
        ': No config found! Check your inputs.conf in local.')  # print the error into Splunk UI
    sys.exit()  # exit on error

# starting the script
logger.info('Starting the script ...')  # logger

# or get user provided options in Splunk as keyword, option
try:  # lets do it
    logger.info('getting Splunk options...')  # logger
    # get key value pairs from user search
    keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
    logger.info('got these options: %s ...' % (options))  # logger
    # get user option or use a default value
    lat = options.get('src_lat', '0')
    logger.info('got these options: lat = %s ...' % (lat))  # logger
    # get user option or use a default value
    lon = options.get('src_lon', '0')
    logger.info('got these options: lon = %s ...' % (lon))  # logger
    # get user option or use a default value
    lat = options.get('lat', '0')
    logger.info('got these options: lat = %s ...' % (lat))  # logger
    # get user option or use a default value
    lon = options.get('lon', '0')
    logger.info('got these options: lon = %s ...' % (lon))  # logger
    # get user option or use a default value
    dest_lat = options.get('dest_lat', '0')
    logger.info('got these options: dest_lat = %s ...' % (dest_lat))  # logger
    # get user option or use a default value
    dest_lon = options.get('dest_lon', '0')
    logger.info('got these options: dest_lon = %s ...' % (dest_lon))  # logger
    # get user option or use a default value
    section_name = options.get('me', 'moon')
    logger.info('got these option: section_name = %s ...' % (section_name))  # logger
    # get user option or use a default value
    forecast = options.get('forecast', 'no')
    logger.info('got these option: forecast = %s ...' % (forecast))  # logger

except:  # get error back
    logger.error('INFO: no option provided, using conf file!')  # logger


# get previous search results from Splunk
try:  # lets do it
    logger.info('getting previous search results...')  # logger
    # getting search results form Splunk
    myresults, dummyresults, settings = splunk.Intersplunk.getOrganizedResults()
    for r in myresults:  # loop the results
        logger.info('Result is : %s' % r)  # logger
        for k, v in r.items():  # get key value pairs for each result
            logger.info('Key is : %s | Value is : %s ' % (k, v))  # logger
            if k == 'dest_lat':  # get key
                dest_lat = v  # set value
            else:
                dest_lat = dest_lat  # get key
            if k == 'dest_lon':  # get key
                dest_lon = v  # set value
            else:
                dest_lon = dest_lon  # get key
            if k == 'src_lat':  # get key
                lat = v  # set value
            else:
                lat = lat  # get key
            if k == 'src_lon':  # get key
                lon = v  # set value
            else:
                lon = lon  # get key
            if k == 'lat':  # get key
                lat = v  # set value
            else:
                lat = lat  # get key
            if k == 'lon':  # get key
                lon = v  # set value
            else:
                lon = lon  # get key
            if k == 'forecast':  # get key
                forecast = v  # set value
            else:
                forecast = forecast  # get key


except:  # get error back
    logger.info(
        'INFO: no previous search results provided using [default]!')  # logger


# having fun
if 'beer' in section_name:
    logger.info('Starting beer response ...')  # logger
    foo = ['It was the accepted practice in Babylon, 4,000 years ago, that for a month after the wedding, the bride`s father would supply his son-in law with all the mead he could drink. Mead is a honey beer, and because their calendar was lunar based, this period was called the "honey month," or what we know today as the "honeymoon."', 'There are 19 different versions of Guinness (5 or 6 main types in 19 variations, according to the late Michael Jackson).', 'According to a diary entry from a passenger on the Mayflower, the pilgrims made their landing at Plymouth Rock, rather than continue to their destination in Virginia, due to lack of beer.', 'A barrel contains 31 gallons of beer. What Americans commonly refer to as a keg is actually 15.5 gallons, or a half-barrel.', 'The first beer cans were produced in 1935.', 'Before thermometers were invented, brewers would dip a thumb or finger into the mix to find the right temperature for adding yeast. Too cold, and the yeast wouldn`t grow. Too hot, and the yeast would die. This thumb in the beer is where the phrase "rule of thumb" comes from.', 'In 1788, Ale was proclaimed "the proper drink for Americans" at a parade in New York City.', 'In English pubs, ale is ordered by pints and quarts. So in old England, when customers got unruly, the bartender would yell at them to mind their own pints and quarts and settle down. It`s where we get the phrase "mind your P`s and Q`s."', 'The original text of the Reinheitsgebot (Germany`s Beer Purity Law) only had three ingredients: barley, hops and water. Yeast wasn`t mentioned for another 35 years.', 'George Washington had his own brewhouse on the grounds of Mount Vernon. On another note, we recently learned his wife, Martha, had a fantastic Rum Punch recipe.', 'After consuming a bucket or two of vibrant brew they called aul, or ale, the Vikings would head fearlessly into battle, often without armor or even shirts. In fact, "berserk" means "bare shirt" in Norse, and eventually took on the meaning of their wild battles.', 'The Budweiser Clydesdales weigh up to 2,300-pounds and stand nearly 6-feet at the shoulder.', '12-ounces of a typical American pale lager actually has fewer calories than 2 percent milk or apple juice.', 'In 1963, Jim Whitaker became the first American to reach the summit of Mt. Everest. A can of Seattle`s own Rainier Beer made the ascent with him.']
    logger.info('foo is : %s ...' % (foo))  # logger
    responses = []  # setup empty list
    response = {}  # setup empty dict
    baz = random.choice(foo)  # choose radom
    logger.info('choose random : %s ...' % (baz))  # logger
    response['Random beer fact'] = baz  # fill in key value pairs
    logger.info('created response : %s ...' % (response))  # logger
    logger.info('Printing to Splunk ...')  # logger
    responses.append(response)
    # print the result into Splunk UI
    splunk.Intersplunk.outputResults(responses)
    sys.exit()

# use user provided options or get stanza options
try:  # lets do it
    logger.info('read the default options from inputs.conf...')  # logger
    logger.info('reading server from inputs.conf...')  # logger
    section_name = 'myGet://%s' % section_name
    server = parser.get(section_name, 'server')
    token = parser.get(section_name, 'token')
    #myDebug = parser.get(section_name, 'debug')
    logger.info('got these options: %s %s ...' % (server, token))  # logger

except Exception, e:  # get error back
    logger.error(
        'ERROR: unable to get default options from inputs.conf')  # logger
    logger.error('ERROR: %e' % e)  # logger
    splunk.Intersplunk.generateErrorResults(
        ': unable to get default options from inputs.conf')  # print the error into Splunk UI
    sys.exit()  # exit on error

# starting the main
logger.info('Starting the main task ...')

# now we get data
try:  # lets do it
    logger.info('getting data ...')
    logger.info('using server %s ...' % server)
    logger.info('using token %s ...' % token)

    # getting moon phases
    if 'moon' in section_name:
        now = datetime.now()
        year = now.year
        con_str = '%s%s&token=%s' % (server, year, token)
        logger.info('using con_str %s ...' % con_str)
        url = urllib2.urlopen('%s' % con_str)
        r_parsed = json.loads(url.read())
        result = r_parsed['phasedata']
        logger.info('parsed result %s ...' % result)
        responses = []  # setup empty list
        p = '%Y %b %d %H:%M'
        epoch = datetime(1970, 1, 1)
        for f_c in result:
            response = {}  # setup empty dict
            mytime = '%s %s' % (f_c['date'], f_c['time'])
            _time = ((datetime.strptime(mytime, p) - epoch).total_seconds())
            response['_time'] = _time
            response['phase'] = f_c['phase']
            od = collections.OrderedDict(
                sorted(response.items()))  # sort the dict
            responses.append(od)  # append the ordered results to the list
        # print the result into Splunk UI
        splunk.Intersplunk.outputResults(responses)

    # getting weather data
    if 'weather' in section_name:
        r_parsed = ''
        if forecast == 'yes':
            con_str = '%s/data/2.5/forecast?lat=%s&lon=%s&units=metric&appid=%s&cnt=14' % (
                server, lat, lon, token)
        if forecast == 'no':
            con_str = '%s/data/2.5/weather?lat=%s&lon=%s&units=metric&appid=%s&cnt=14' % (
                server, lat, lon, token)
        logger.info('using con_str %s ...' % con_str)
        url = urllib2.urlopen('%s' % con_str)
        r_parsed = json.loads(url.read())
        logger.info('parsed result %s ...' % r_parsed)
        responses = []  # setup empty list
        if forecast == 'yes':
            result = r_parsed['list']
            for f_c in result:
                response = {}  # setup empty dict
                response['_time'] = f_c['dt']  # fill in key value pairs
                # fill in key value pairs
                response['temp'] = f_c['main']['temp']
                # fill in key value pairs
                response['pressure'] = f_c['main']['pressure']
                # fill in key value pairs
                response['humidity'] = f_c['main']['humidity']
                # fill in key value pairs
                response['weather.icon'] = f_c['weather'][0]['icon']
                # fill in key value pairs
                response['weather.id'] = f_c['weather'][0]['id']
                # fill in key value pairs
                response['weather.desc'] = f_c['weather'][0]['description']
                # fill in key value pairs
                response['weather.main'] = f_c['weather'][0]['main']
                # fill in key value pairs
                response['clouds'] = f_c['clouds']['all']
                # fill in key value pairs
                response['wind.speed'] = f_c['wind']['speed']
                # fill in key value pairs
                response['wind.deg'] = f_c['wind']['deg']
                od = collections.OrderedDict(
                    sorted(response.items()))  # sort the dict
                responses.append(od)  # append the ordered results to the list
            # print the result into Splunk UI
            splunk.Intersplunk.outputResults(responses)
        if forecast == 'no':
            f_c = r_parsed
            response = {}  # setup empty dict
            response['_time'] = f_c['dt']  # fill in key value pairs
            response['temp'] = f_c['main']['temp']  # fill in key value pairs
            # fill in key value pairs
            response['pressure'] = f_c['main']['pressure']
            # fill in key value pairs
            response['humidity'] = f_c['main']['humidity']
            # fill in key value pairs
            response['weather.icon'] = f_c['weather'][0]['icon']
            # fill in key value pairs
            response['weather.id'] = f_c['weather'][0]['id']
            # fill in key value pairs
            response['weather.desc'] = f_c['weather'][0]['description']
            # fill in key value pairs
            response['weather.main'] = f_c['weather'][0]['main']
            # fill in key value pairs
            response['clouds'] = f_c['clouds']['all']
            # fill in key value pairs
            response['wind.speed'] = f_c['wind']['speed']
            # fill in key value pairs
            response['wind.deg'] = f_c['wind']['deg']
            od = collections.OrderedDict(
                sorted(response.items()))  # sort the dict
            responses.append(od)  # append the ordered results to the list
            # print the result into Splunk UI
            splunk.Intersplunk.outputResults(responses)

    # getting directions
    if 'directions' in section_name:
        #con_str = '%sjson?origin=%s,%s&destination=%s,%s&units=metric&key=%s' % (
        #    server, lat, lon, dest_lat, dest_lon, token)
        con_str = '%s/%s,%s;%s,%s.json?access_token=%s&geometries=geojson' % (
            server, lon, lat, dest_lon, dest_lat, token)
        logger.info('using con_str %s ...' % con_str)
        url = urllib2.urlopen('%s' % con_str)
        r_parsed = json.loads(url.read())
        result = r_parsed['routes']
        logger.info('parsed result %s ...' % result)
        responses = []  # setup empty list
        step_num = 0
        for routes in result:
            logger.info('parsed routes %s ...' % routes)
            for key, value in routes.iteritems():
                if 'geometry' in key:
                    logger.info('parsed key %s, value %s ...' % (key, value))
                    coors = value['coordinates']
                    logger.info('parsed coors %s ...' % coors)
                    for steps in coors:
                        logger.info('parsed steps %s ...' % steps)
                        response = {}  # setup empty dict
                        response['step_num'] = step_num
                        # fill in key value pairs
                        response['start.lat'] = steps[1]
                        # fill in key value pairs
                        response['start.lon'] = steps[0]
                        od = collections.OrderedDict(
                             sorted(response.items()))  # sort the dict
                        # append the ordered results to the list
                        responses.append(od)
                        step_num += 1
                    logger.info('parsed response %s ...' % response)
        # print the result into Splunk UI
        splunk.Intersplunk.outputResults(responses)


except Exception, e:  # get error back
    logger.error('ERROR: unable to get data.')
    logger.error('ERROR: %s ' % e)
    splunk.Intersplunk.generateErrorResults(
        ': %s' % e)  # print the error into Splunk UI
    sys.exit()  # exit on error
