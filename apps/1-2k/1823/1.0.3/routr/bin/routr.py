__author__ = 'Levonne Key <levonnekey@gmail.com>'
__license__ = 'Apache License, Version 2.0'

import ConfigParser
import base64
import logging
import os
import sys
import urllib

TOKEN_DELIMITER = '###'
SPLUNK_HOME_PATH = os.environ.get("SPLUNK_HOME")

# Dynamically load egg files at runtime
EGG_DIR = SPLUNK_HOME_PATH + "/etc/apps/routr/bin/"
for filename in os.listdir(EGG_DIR):
    if filename.endswith(".egg"):
        sys.path.append(EGG_DIR + filename)

# Set up logging
log_file = os.path.join(SPLUNK_HOME_PATH, 'var', 'log', 'splunk', 'routr.log')
logging.basicConfig(level=logging.INFO, filename=log_file,
    format=('%(asctime)s lvl=%(levelname)s '
            'loc=%(module)s:%(funcName)s:%(lineno)d '
            'comp=%(name)s %(message)s'))
logger = logging.getLogger(__name__)

# Shorten URL using tinyurl
def shorten_url(input_url):
    result = None
    tinyurl = urllib.urlopen(
        "http://tinyurl.com/api-create.php?url=%s" % input_url)
    try:
        result = tinyurl.read()
    finally:
        tinyurl.close()
    return result

# Decode creds from routrcreds.conf in local directory
def get_creds(social_media_channel):
    compiled_creds = None
    stanza_name = None
    if social_media_channel == 'Twitter':
        stanza_name = 'twittercreds'
        compiled_creds = [
            ['twitter_consumer_key', ''],
            ['twitter_consumer_secret', ''],
            ['twitter_access_token', ''],
            ['twitter_access_token_secret', '']]
    elif social_media_channel == 'Tumblr':
        stanza_name = 'tumblrcreds'
        compiled_creds = [
            ['tumblr_blogname', ''],
            ['tumblr_consumer_key', ''],
            ['tumblr_consumer_secret', ''],
            ['tumblr_access_token', ''],
            ['tumblr_access_token_secret', '']]

    app_creds = None
    creds_file = os.path.join(
        SPLUNK_HOME_PATH, 'etc', 'apps', 'routr',
        'local', 'routrcreds.conf')

    # Checks if routrcreds.conf exists in local directory and read it
    if os.path.exists(creds_file):
        config = ConfigParser.SafeConfigParser()
        config.read(creds_file)

        # Decode the creds
        for key, val in config.items(stanza_name):
            decoded_creds = base64.urlsafe_b64decode(val)
            decoded_creds = decoded_creds.split(TOKEN_DELIMITER)

            for _index in range(0, len(decoded_creds)):
                compiled_creds[_index][1] = decoded_creds[_index]

        # Convert list into dictionary
        app_creds = dict((x, y) for x, y in compiled_creds)
    return app_creds


class TumblrSplunkAlerts(object):

    def __init__(self):
        pass

    # Create a Tumblr post when Splunk alert is triggered
    def post_tumblr(self, number_events_returned, search_terms,
                    fully_qualified_search_string, name_of_saved_search,
                    reason_triggered_script, link_to_saved_search):
        tumblr_creds = get_creds('Tumblr')
        pytumblr_client = None 
        if tumblr_creds:
            try:
                import pytumblr
                pytumblr_client = pytumblr.TumblrRestClient(
                    tumblr_creds['tumblr_consumer_key'],
                    tumblr_creds['tumblr_consumer_secret'],
                    tumblr_creds['tumblr_access_token'],
                    tumblr_creds['tumblr_access_token_secret'])

                pytumblr_client.create_text(
                    tumblr_creds['tumblr_blogname'],
                    title=name_of_saved_search,
                    body="<b>Reason alert triggered: </b>{0}<br/>"
                         "<b>Number of events returned: </b>{1}<br/>"
                         "<b>Search terms: </b>{2}<br/>"
                         "<b>Fully qualified search string: </b>{3}<br/>"
                         "<b>Link to saved search: </b><a href=\"{4}\">{4}</a><br/>".format(
                            reason_triggered_script, number_events_returned,
                            search_terms, fully_qualified_search_string,
                            link_to_saved_search),
                    format='html',
                    state='published',
                    tags=['Splunkalert', name_of_saved_search.replace(" ", "")])
            except Exception as exc:
                logger.error("exception: %s" % exc)


class TweetSplunkAlerts(object):

    def __init__(self):
        pass

    # Post tweet when Splunk alert is triggered
    def post_tweet(self, alert_name, alert_url):
        tweet = "Alert:[{0}] {1}"
        twitter_creds = get_creds('Twitter')
        if twitter_creds:
            import twitter
            twitter_api = None
            try:
                twitter_api = twitter.Api(
                    consumer_key=twitter_creds['twitter_consumer_key'],
                    consumer_secret=twitter_creds['twitter_consumer_secret'],
                    access_token_key=twitter_creds['twitter_access_token'],
                    access_token_secret=twitter_creds['twitter_access_token_secret'])
                alert_url = shorten_url(alert_url)
                tweet = tweet.format(alert_name, alert_url)
                twitter_api.PostUpdate(tweet)
                logger.info("alert_name=%s alert_url=%s tweet=%s" % (
                    alert_name, alert_url, tweet))
            except Exception as exc:
                logger.error("exception: %s" % exc)
