
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#                                                                                                                     //
#   Author: Juan Alejandro Perez Chadia                                                                               //
#   Date: July 25th, 2019                                                                                             //
#   Personal brand: JPEngineer                                                                                        //
#                                                                                                                     //
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

import traceback
import splunk.Intersplunk
import sys
import os
import config
import ConfigParser

_PACKAGE_ = os.getcwd() + '/packages'
sys.path.append(_PACKAGE_)

_version_ = '1.0.C'
_author_ = 'Juan Alejandro Perez Chandia'
_brand_ = 'JPEngineer'
_type_ = 'LTS'


def write_config(section, option, value, file_name):
    _configParser.read(file_name)
    if _configParser.has_option(section, option):
        _configParser.set(section, option, value)
        with open(file_name, 'wb') as configfile:
            _configParser.write(configfile)
        configfile.close()
    else:
        log.error('[{0}] section or "{1}" option doesn\'t exist'.format(str(section), str(option)))


def verify(param):
    result = False
    if (param[1].lower() == 'true' and len(param[6]) > 1) or param[1].lower() == 'false':
        if len(param[2]) > 1 and len(param[3]) > 1 and len(param[4]) > 1 and len(param[5]) > 1:
            result = True
    return result


def new_token(param):
    """
    param[0] = Option --> security
    param[1] = Encrypt --> true or false
    param[2] = consumer_key
    param[3] = consumer_secret
    param[4] = access_token
    param[5] = access_secret
    param[6] = key --> Only if param[1] is true
    """
    try:
        write_config('token', 'consumer_key', param[2], config_file)
        write_config('token', 'consumer_secret', param[3], config_file)
        write_config('token', 'access_token', param[4], config_file)
        write_config('token', 'access_secret', param[5], config_file)

        if arg[0].lower() == 'true':
            write_config('security', 'encryption', param[1], config_file)
            write_config('security', 'key', param[6], config_file)
        else:
            write_config('security', 'encryption', param[1], config_file)
            write_config('security', 'key', 'None', config_file)
            log.warn("The configuration isn't encrypted")

        log.info("Token successfully saved")

    except:
        log.warn("The token could not be saved")
        log.error(traceback.format_exc())


def new_filter(param):
    """
    param[0] = filter
    param[1] = action --> new
    param[2] = filter
    """
    try:
        user_filter = param[2].split(',')
        file_filter = []

        for element in user_filter:
            if element not in file_filter:
                file_filter.append(element)

        twitter_filter = ','.join(file_filter)
        write_config('listener', 'filter', twitter_filter, config_file)
        log.info("Filter successfully saved")
    except Exception as e:
        log.warn("The filter could not be saved")
        log.error(e.message)


def add_filter(param):
    """
    param[0] = filter
    param[1] = action --> add
    param[2] = filter
    """
    try:
        _configParser.read(config_file)
        file_filter = _configParser.get('listener', 'filter').split(',')
        user_filter = param[2].split(',')

        for element in user_filter:
            if element not in file_filter:
                file_filter.append(element)

        twitter_filter = ','.join(file_filter)
        write_config('listener', 'filter', twitter_filter, config_file)
        log.info("Filter successfully saved")
    except Exception as e:
        log.warn("The filter could not be saved")
        log.error(e.message)


#                  I N I T I A L I Z E

path = os.getcwd() + '/logs/'
config_file = 'twitter.conf'
log_file = os.path.splitext(os.path.basename(__file__))[0] + '.log'
logger = config.Log(log_file)
conf = config.InitialConfig(config_file)
log = logger.config_log(path, conf.log_max_bkp, conf.log_max_mb)


#       R E A D   S P L U N K   A R G U M E N T S

sys.argv.insert(1, "__EXECUTE__")
(isgetinfo, sys.argv) = splunk.Intersplunk.isGetInfo(sys.argv)
results = splunk.Intersplunk.readResults(None, None, True)

if len(sys.argv) > 1:
    arg = []
    for x in sys.argv[1:]:
        arg.append(x)

    _configParser = ConfigParser.SafeConfigParser()
    if arg[0].lower() == 'security':
        if not verify(arg):
            log.warn("Please, complete all fields.")
        else:
            new_token(arg)

    elif arg[0].lower() == 'filter':
        if arg[1] == 'add':
            add_filter(arg)
        if arg[1] == 'new':
            new_filter(arg)
    else:
        log.error("Command not found")

else:
    log.warn("Please, validate the setting on titter.conf")
    sys.exit(1)
