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
import config
import security
from tweepy import OAuthHandler
from tweepy import API
from tweepy import parsers
from tweepy import StreamListener
from tweepy import Stream


_PACKAGE_ = os.getcwd() + '/packages'
sys.path.append(_PACKAGE_)

_version_ = '1.0.C'
_author_ = 'Juan Alejandro Perez Chandia'
_brand_ = 'JPEngineer'
_type_ = 'LTS'


class Listener(StreamListener):
    def on_data(self, data):
        try:
            data = data.replace('\n', '')
            log.info(data.replace('\n', ''))
        except Exception as error:
            log.error(error)


def authentication(cipher, consumer_key, consumer_secret, access_token, access_secret):
    try:
        # TODO remove - only testing
        # print "CONSUMER_KEY: ", cipher.decrypt(consumer_key).encode('utf-8')
        # print "CONSUMER_SECRET: ", cipher.decrypt(consumer_secret).encode('utf-8')
        # print "ACCESS_TOKEN: ", cipher.decrypt(access_token).encode('utf-8')
        # print "ACCESS_SECRET: ", cipher.decrypt(access_secret).encode('utf-8')

        # Authentication with Twiteer API
        authenticate = OAuthHandler(cipher.decrypt(consumer_key).encode('utf-8'),
                                    cipher.decrypt(consumer_secret).encode('utf-8'))
        authenticate.set_access_token(cipher.decrypt(access_token).encode('utf-8'),
                                      cipher.decrypt(access_secret).encode('utf-8'))
        twitter_api = API(authenticate, parser=parsers.JSONParser())
        return twitter_api, authenticate

    except Exception as error:
        log.error("There was an error trying to connect with twitter.")
        log.error(error.args)
        exit(0)


# Define the log path
path = os.getcwd() + '/logs/'
log_file = os.path.splitext(os.path.basename(__file__))[0] + '.log'

# Load Initial Configurations
conf = config.InitialConfig('twitter.conf')

if conf.load_config():
    logger = config.Log(log_file)
    log = logger.config_log(path, conf.log_max_bkp, conf.log_max_mb)

    try:
        AES = security.AESCipher(conf.encrypt_key)
        api, auth = authentication(AES, conf.consumer_key, conf.consumer_secret, conf.access_token, conf.access_secret)
    except Exception as error:
        print(error)

    try:
        listener = StreamListener()
        listener = Stream(auth, Listener(), tweet_mode='extended')
        listener.filter(track=[conf.filter])
    except Exception as err:
        log.error("The access token must be updated: " + str(err))
