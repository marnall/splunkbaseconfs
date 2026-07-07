#!/opt/splunk/bin/python
# Copyright (C) 2014 MuS
# http://answers.splunk.com/users/2122/mus
#

# enable / disable logger debug output
myDebug='no'

# import some Python moduls
import sys, os, splunk.Intersplunk, re, urllib2, json, collections, logging, logging.handlers
import netaddr

# debug logging definition
def setup_logging(n):
    logger = logging.getLogger(n) # Root-level logger
    if myDebug == 'yes':
       logger.setLevel(logging.DEBUG)
    else:
       logger.setLevel(logging.ERROR)
    SPLUNK_HOME = os.environ['SPLUNK_HOME']
    LOGGING_DEFAULT_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log.cfg')
    LOGGING_LOCAL_CONFIG_FILE = os.path.join(SPLUNK_HOME, 'etc', 'log-local.cfg')
    LOGGING_STANZA_NAME = 'python'
    LOGGING_FILE_NAME = 'maclookup.log'
    BASE_LOG_PATH = os.path.join('var', 'log', 'splunk')
    LOGGING_FORMAT = '%(asctime)s %(levelname)-s\t%(module)s:%(lineno)d - %(message)s'
    splunk_log_handler = logging.handlers.RotatingFileHandler(os.path.join(SPLUNK_HOME, BASE_LOG_PATH, LOGGING_FILE_NAME), mode='a')
    splunk_log_handler.setFormatter(logging.Formatter(LOGGING_FORMAT))
    logger.addHandler(splunk_log_handler)
    splunk.setupSplunkLogger(logger, LOGGING_DEFAULT_CONFIG_FILE, LOGGING_LOCAL_CONFIG_FILE, LOGGING_STANZA_NAME)
    return logger

# set URL to be used for query
url = 'https://macvendors.co/api'

# set regex for MAC address like xx:xx.. or xx-xx.. or xxxx.xxxx..
regex = '[0-9A-Za-z]{2}[:-][0-9A-Za-z]{2}[:-][0-9A-Za-z]{2}[:-][0-9A-Za-z]{2}[:-][0-9A-Za-z]{2}[:-][0-9A-Za-z]{2}|[a-zA-Z0-9]{4}\.[a-zA-Z0-9]{4}\.[a-zA-Z0-9]{4}'

# set empty list to be used in Splunk output
list = []

# start the logger
logger = setup_logging( 'maclookup started ...' )

logger.info('getting Splunk options...')  # logger
# get key value pairs from user search
keywords, options = splunk.Intersplunk.getKeywordsAndOptions()
logger.info('got these options: %s ...' % (options))  # logger
# get user option or use a default value
field = options.get('field', 'src_mac')
logger.info('got these options: field = %s ...' % (field))  # logger
# get user option or use a default value
online = options.get('online', 'no')
logger.info('got these options: online = %s ...' % (online))  # logger


# get previous Splunk result events
logger.info( 'getting Splunk results ...' )
results,dummyresults,settings = splunk.Intersplunk.getOrganizedResults()

# loop through the results
logger.info( 'looping through the results ...' )
for line in results:
    try:
        macs = []
        logger.info( 'line: %s ' % line )
        if field == 'src_mac':
            logger.info( 'matching on src_mac ...' )
            macs.append(line['src_mac'])
            logger.info( 'list of macs : %s ...' % macs)
        else:
            logger.info( 'matching on %s : ' % field )
            l_field = line[field]
            logger.info( 'matching on %s : ' % l_field )
            # use the regex to get the mac out of _raw
            try:
                logger.info( 'regex matching on %s ...' % l_field )
                macs = re.findall(regex, l_field)
                logger.info( 'found macs: %s ' % macs )
            except:
                logger.error( 'failed to match regex!' )
                splunk.Intersplunk.generateErrorResults(': failed to match regex!')
                exit()
    except:
        logger.error( 'failed to read fields!' )
        splunk.Intersplunk.generateErrorResults(': failed to read fields!')
        exit()

    # for each found mac
    for MAC in macs:
        logger.info( 'for each found MAC ...' )
        # query the URL
        logger.info( 'Online : %s ...' % online )
        if 'yes' in online:
            try:
                logger.info( 'setup the online URL to query ...' )
                url2 = '%s/%s/json' % (url, MAC)
                logger.info('Using %s as URL and %s as MAC' % (url2, MAC))
                logger.info('connecting ... ')
                r = urllib2.urlopen(url2)
                logger.info('connected ...')
            except:
                logger.error( 'failed to setup the URL!' )
                splunk.Intersplunk.generateErrorResults(': failed to setup the URL! Using %s as URL and %s as MAC' % (url2, MAC))
                exit()
            try:
                # and read the result as JSON list of dicts
                logger.info( 'and read the result as JSON list of dicts ...' )
                data = json.loads(r.read().decode(r.info().getparam('charset') or 'utf-8'))
                logger.info( 'got JSON list of dict: %s ' % data )
            except:
                logger.error( 'failed to read the result for MAC %s' % MAC )
                splunk.Intersplunk.generateErrorResults(': failed to read the online result!')
                exit()
            # get the dict out of the URL result list
            logger.info( 'get the dict out of the URL result list ...' )
            try:
                # and put it into new list, so more dict can be added
                logger.info( 'adding result : %s ' % data['result'] )
                list.append(data['result'])
                logger.info( 'new list : %s ' % list )
            except:
                logger.error( 'failed to build the list for the splunk output!' )
                splunk.Intersplunk.generateErrorResults(': failed to build the list for the splunk output!')
                exit()

        # query the netaddr library
        if 'no' in online:
	    try:
                logger.info( 'setup the offline netaddr query ...' )
                logger.info( 'using mac to lookup : %s ' % MAC)
                lookup = netaddr.EUI(MAC)
                logger.info( 'netaddr lookup: %s ...' % lookup )
                vendor = ','.join([lookup.oui.registration(reg).org for reg in range(lookup.oui.reg_count)])
                logger.info('result from netaddr vendor :  %s ' % vendor)
                logger.info( 'add vendor to dict ...' )
                line['vendor'] = vendor
                # more fancy stuff, updating the previous results with the new fields
                logger.info( 'updated line : %s ' % line )
                #line.update(dict)
                # and put it into new list, so more dict can be added
                logger.info( 'and put it into new list, so more dict can be added ...' )
                list.append(line)
                logger.info( 'new list : %s ' % list)
            except:
                logger.error( 'failed to use the netaddr module!' )
                splunk.Intersplunk.generateErrorResults(': failed to use the netaddr module!')
                exit()

# output the result to splunk
logger.info( 'output the result to splunk> ...' )
splunk.Intersplunk.outputResults(list)
