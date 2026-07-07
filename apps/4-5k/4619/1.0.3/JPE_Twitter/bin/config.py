# -*- coding: utf-8 -*-

# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////
#                                                                                                                     //
#   Author: Juan Alejandro Perez Chadia                                                                               //
#   Date: July 25th, 2019                                                                                             //
#   Personal brand: JPEngineer                                                                                        //
#                                                                                                                     //
# //////////////////////////////////////////////////////////////////////////////////////////////////////////////////////

import os
import sys
import logging
import logging.handlers
import time
import ConfigParser
import security

_PACKAGE_ = os.getcwd() + '/packages'
sys.path.append(_PACKAGE_)

_version_ = '1.0.C'
_author_ = 'Juan Alejandro Perez Chandia'
_brand_ = 'JPEngineer'
_type_ = 'LTS'
_debug = True


class InitialConfig(object):

    global _version_
    global _author_
    global _brand_
    global _type_
    global _debug

    def __init__(self, file_name=''):
        self.file_name = file_name

        # Twitter API token
        self.consumer_key = ''
        self.consumer_secret = ''
        self.access_token = ''
        self.access_secret = ''

        # Encryption
        self.encrypt = False
        self.encrypt_key = ''

        # Listener Filter
        self.filter = []

        # TODO No Implemented
        # Sentiment Analytics
        # self.sentiment = False

        # Logs
        self.log_path = os.getcwd() + '/logs/'
        self.log_max_mb = 0
        self.log_max_bkp = 0
        self.debug = _debug

        # INFO
        self.version = _version_
        self.author = _author_
        self.brand = _brand_
        self.type = _type_

        # if config was successfully loaded, the status parameter is True
        self.status = False

    def load_config(self):

        global _debug
        config = ConfigParser.SafeConfigParser(allow_no_value=True)

        def get_data(section, option, required=True, default=''):
            try:
                value = config.get(section, option)
                if len(value) < 1 and required:
                    raise ConfigParser.Error('\"{1}\" option is empty in [{0}] section'.format(section, option))

            except ConfigParser.Error as error:
                if required:
                    print(error.message)
                    sys.exit(1)
                else:
                    return default
            except ConfigParser.NoOptionError as error:
                print(error.message)
                sys.exit(1)
            except ConfigParser.NoSectionError as error:
                print(error.message)
                sys.exit(1)

            return value

        def get_integer_data(section, option, required=False, default=0):
            try:
                value = config.getint(section, option)
            except ValueError:
                if required:
                    print('\"{1}\" option is empty or has not boolean type value, in [{0}] section'
                          .format(section, option))
                    sys.exit(1)
                else:
                    return default
            except ConfigParser.NoOptionError as error:
                print(error.message)
                sys.exit(1)
            except ConfigParser.NoSectionError as error:
                print(error.message)
                sys.exit(1)

            return value

        def get_boolean_data(section, option, required=True, default=False):
            try:
                value = config.getboolean(section, option)
            except ValueError:
                if required:
                    print('\"{1}\" option is empty or has not boolean type value, in [{0}] section'
                          .format(section, option))
                    sys.exit(1)
                else:
                    return default
            except ConfigParser.NoOptionError as error:
                print(error.message)
                sys.exit(1)
            except ConfigParser.NoSectionError as error:
                print(error.message)
                sys.exit(1)

            return value

        def write_value(section, option, value):
            try:
                config.set(section, option, value)
                with open('twitter.conf', 'wb') as configfile:
                    config.write(configfile)
                configfile.close()
            except ValueError:
                print(ValueError.message)
                sys.exit(0)
            except ConfigParser.NoSectionError:
                config.add_section(section)
                write_value(section, option, value)
            return True

        def security_parameter():
            if self.encrypt:
                param = {
                    'consumer_key': self.consumer_key,
                    'consumer_secret': self.consumer_secret,
                    'access_token': self.access_token,
                    'access_secret': self.access_secret,
                    'encryption': self.encrypt,
                    'key': self.encrypt_key
                }
                verify = security.VerifyConfig()
                param = verify.load(param)
                write_value('token', 'consumer_key', param['consumer_key'])
                write_value('token', 'consumer_secret', param['consumer_secret'])
                write_value('token', 'access_token', param['access_token'])
                write_value('token', 'access_secret', param['access_secret'])
                write_value('security', 'encryption', str(param['encryption']))
                write_value('security', 'key', param['key'])
                self.consumer_key = param['consumer_key']
                self.consumer_secret = param['consumer_secret']
                self.access_token = param['access_token']
                self.access_secret = param['access_secret']
                self.encrypt = param['encryption']
                self.encrypt_key = param['key']

        config.read(self.file_name)
        self.consumer_key = get_data('token', 'consumer_key')
        self.consumer_secret = get_data('token', 'consumer_secret')
        self.access_token = get_data('token', 'access_token')
        self.access_secret = get_data('token', 'access_secret')
        self.encrypt = get_boolean_data('security', 'encryption', False)

        if self.encrypt:
            self.encrypt_key = get_data('security', 'key')
        else:
            self.encrypt_key = get_data('security', 'key', False)

        self.filter = get_data('listener', 'filter')
        self.log_max_mb = get_integer_data('logs', 'max_size_mb', False, 40)
        self.log_max_bkp = get_integer_data('logs', 'max_log_backup', False, 2)
        self.debug = get_boolean_data('logs', 'debug', False)

        # Write info
        write_value('info', 'app_version', self.version)
        write_value('info', 'type', self.type)

        # TODO No Implemented
        # self.sentiment = get_boolean_data('listener', 'sentiment', False)

        security_parameter()
        self.status = True

        # TODO Corregir degug del config file
        _debug = self.debug
        return self.status


class Log(object):

    global _debug

    def __init__(self, file_name):
        self.full_path = ''
        self.file_name = file_name
        self.backup = 0
        self.max_log_mb = 0
        self.debug = _debug

    def config_log(self, log_path, backup, max_log_mb):
        self.full_path = log_path + self.file_name
        self.backup = backup
        self.max_log_mb = max_log_mb * 1024 * 1024

        log_handler = logging.handlers.RotatingFileHandler(self.full_path, mode='a', maxBytes=self.max_log_mb,
                                                           backupCount=self.backup, encoding=None, delay=0)
        formatter = logging.Formatter('%(asctime)s ' + self.file_name + ' %(levelname)s : %(message)s', '%b %d %H:%M:%S')
        formatter.converter = time.localtime
        log_handler.setFormatter(formatter)
        logger = logging.getLogger()
        logger.addHandler(log_handler)
        if self.debug:
            logger.setLevel(logging.DEBUG)
        else:
            logger.setLevel(logging.INFO)
        return logger


# ==================================================================================
#                           T  E  S  T  I  N  G
# ==================================================================================
if __name__ == '__main__':
    print('Ejecutando como programa principal')
    print(os.getcwd() + '/packages')
#     initConf = InitialConfig('twitter.conf')
#     if initConf.load_config():
#
#         print initConf.consumer_key
#         print initConf.consumer_secret
#         print initConf.access_token
#         print initConf.access_secret
#         print initConf.encrypt
#         print initConf.encrypt_key
#         print initConf.filter
#         print initConf.log_max_mb
#         print initConf.log_max_bkp
#         print initConf.debug
#         print initConf.log_path
#         print initConf.file_name
#         log_name = os.path.splitext(os.path.basename(__file__))[0] + '.log'
#         config_log = Log(log_name)
#         _log = config_log.config_log(initConf.log_path, initConf.log_max_bkp, initConf.log_max_mb)
#         _log.info('test')
#         _log.warning('test')
#         _log.error('test')
#         _log.debug('test')
#     else:
#         print("Initial config return False... F*ck U!")
