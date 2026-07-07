
'''
Sample tweet json:

{"contributors":null,"text":"@CraZiiBoSSx3 Yea ... Lo_Ok  http://twitpic.com/19ksg2","created_at":"Fri Mar 19 18:41:17 +0000 2010","truncated":false,"coordinates":null,"in_reply_to_screen_name":"CraZiiBoSSx3","favorited":false,"geo":null,"in_reply_to_status_id":10735405186,"source":"<a href=\"http://echofon.com/\" rel=\"nofollow\">Echofon</a>","place":null,"in_reply_to_user_id":114199314,"user":{"created_at":"Mon Dec 21 23:01:05 +0000 2009","profile_background_color":"0099B9","favourites_count":0,"lang":"en","profile_text_color":"3C3940","location":"iiN A Banqinq Body !","following":null,"time_zone":"Central Time (US & Canada)","description":"Da Names GiiqqL3z; Liqhtskin Beauty; FunSiized ;); Brookyln Babe Witt Carribean Wayyz; Waht Mo Can Ya Ask 4 ? Follow A Bad Chiq Buh Dnt Follow 2 Unfollow","statuses_count":1685,"profile_link_color":"0099B9","notifications":null,"profile_background_image_url":"http://s.twimg.com/a/1268437273/images/themes/theme4/bg.gif","contributors_enabled":false,"geo_enabled":false,"profile_sidebar_fill_color":"95E8EC","url":null,"profile_image_url":"http://a3.twimg.com/profile_images/703836981/PwettyChiQq_Kay_normal.jpg","profile_background_tile":false,"protected":false,"profile_sidebar_border_color":"5ED4DC","screen_name":"PwettyChiQq_Kay","name":"~GLam DOll GiiqqLez~","verified":false,"followers_count":77,"id":98491606,"utc_offset":-21600,"friends_count":64},"id":10735704604}

'''
import tweepy
import sys
import xml.dom.minidom, xml.sax.saxutils
import logging

#set up logging suitable for splunkd comsumption
logging.root
logging.root.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(levelname)s %(message)s')
handler = logging.StreamHandler()
handler.setFormatter(formatter)
logging.root.addHandler(handler)


SCHEME = """<scheme>
    <title>Twitter2</title>
    <description>Get sample data from Twitter.</description>
    <use_external_validation>true</use_external_validation>
    <streaming_mode>simple</streaming_mode>
    <use_single_instance>true</use_single_instance>
    <endpoint>
        <args>
            <arg name="name">
                <title>Twitter input name</title>
                <description>Name of the Twitter sample data input, ex: twitter_sample_input.</description>
            </arg>
            <arg name="CONSUMER_KEY">
                <title>CONSUMER_KEY</title>
                <description>Your Twitter CONSUMER_KEY.</description>
            </arg>
            <arg name="CONSUMER_SECRET">
                <title>CONSUMER_SECRET</title>
                <description>Your Twitter CONSUMER_SECRET</description>
            </arg>
            <arg name="ACCESS_TOKEN">
                <title>ACCESS_TOKEN</title>
                <description>Your Twitter ACCESS_TOKEN.</description>
            </arg>
            <arg name="ACCESS_TOKEN_SECRET">
                <title>ACCESS_TOKEN_SECRET</title>
                <description>Your twitter ACCESS_TOKEN_SECRET</description>
            </arg>
        </args>
    </endpoint>
</scheme>
"""

def do_scheme():
    print SCHEME

# prints XML error data to be consumed by Splunk
def print_error(s):
    print "<error><message>%s</message></error>" % xml.sax.saxutils.escape(s)

class SplunkListener( tweepy.StreamListener ):

    def on_data(self, data):
        super( SplunkListener, self).on_data( data )
        twt = tweepy.utils.import_simplejson().loads(data)
        if 'text' in twt:
           print tweepy.utils.import_simplejson().dumps(twt)
        return True

    def on_error(self, status_code):
        """Called when a non-200 status code is returned"""
        print 'got error\n'
        print status_code
        logging.error("got error: %s" %(status_code))
        return False

    def on_timeout(self):
        """Called when stream connection times out"""
        print 'got timeout'
        logging.info("Got a timeout")
        return

def validate_conf(config, key):
    if key not in config:
        raise Exception, "Invalid configuration received from Splunk: key '%s' is missing." % key

#read XML configuration passed from splunkd
def get_config():
    config = {}

    try:
        # read everything from stdin
        config_str = sys.stdin.read()

        # parse the config XML
        doc = xml.dom.minidom.parseString(config_str)
        root = doc.documentElement
        conf_node = root.getElementsByTagName("configuration")[0]
        if not conf_node:
            raise Exception, "Invalid configuration received from Splunk, missing configuration tagname."
            return
        logging.debug("XML: found configuration")

        stanza = conf_node.getElementsByTagName("stanza")[0]
        if not stanza:
            raise Exception, "Invalid configuration received from Splunk, missing stanza tagname."
            return

        stanza_name = stanza.getAttribute("name")
        if not stanza_name:
            raise Exception, "Invalid configuration received from Splunk, missing name attribute."
            return
        logging.debug("XML: found stanza " + stanza_name)
        config["name"] = stanza_name

        params = stanza.getElementsByTagName("param")
        for param in params:
            param_name = param.getAttribute("name")
            logging.debug("XML: found param '%s'" % param_name)
            if (param_name and param.firstChild and
               param.firstChild.nodeType == param.firstChild.TEXT_NODE):
                data = param.firstChild.data
                config[param_name] = data
                logging.debug("XML: '%s' -> '%s'" % (param_name, data))

        checkpnt_node = root.getElementsByTagName("checkpoint_dir")[0]
        if (checkpnt_node and checkpnt_node.firstChild and
            checkpnt_node.firstChild.nodeType == checkpnt_node.firstChild.TEXT_NODE):
            config["checkpoint_dir"] = checkpnt_node.firstChild.data

        if not config:
            raise Exception, "Invalid configuration received from Splunk."

        # just some validation: make sure these keys are present (required)
        validate_conf(config, "name")
        validate_conf(config, "CONSUMER_KEY")
        validate_conf(config, "CONSUMER_SECRET")
        validate_conf(config, "ACCESS_TOKEN")
        validate_conf(config, "ACCESS_TOKEN_SECRET")
        validate_conf(config, "checkpoint_dir")
    except Exception, e:
        raise Exception, "Error getting Splunk configuration via STDIN: %s" % str(e)

    return config

def get_validation_data():
    val_data = {}

    # read everything from stdin
    val_str = sys.stdin.read()

    # parse the validation XML
    doc = xml.dom.minidom.parseString(val_str)
    root = doc.documentElement

    logging.debug("XML: found items")
    item_node = root.getElementsByTagName("item")[0]
    if item_node:
        logging.debug("XML: found item")

        name = item_node.getAttribute("name")
        val_data["stanza"] = name

        params_node = item_node.getElementsByTagName("param")
        for param in params_node:
            name = param.getAttribute("name")
            logging.debug("Found param %s" % name)
            if (name and param.firstChild and
                param.firstChild.nodeType == param.firstChild.TEXT_NODE):
                val_data[name] = param.firstChild.data

    return val_data

# parse the twitter error string and extract the message
def get_twitter_error(s):
    try:
        doc = xml.dom.minidom.parseString(s)
        root = doc.documentElement
        messages = root.getElementsByTagName("Message")
        if (messages and messages[0].firstChild and
            messages[0].firstChild.nodeType == messages[0].firstChild.TEXT_NODE):
            return messages[0].firstChild.data
        return ""
    except xml.parsers.expat.ExpatError, e:
        return s

def validate_arguments():
    val_data = get_validation_data()
    CONSUMER_KEY = val_data["CONSUMER_KEY"]
    CONSUMER_SECRET = val_data["CONSUMER_SECRET"]
    ACCESS_TOKEN = val_data["ACCESS_TOKEN"]
    ACCESS_TOKEN_SECRET = val_data["ACCESS_TOKEN_SECRET"]

    try:
        auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
        auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
        api = tweepy.API(auth)

        if api.verify_credentials() is False:
            raise Exception, "Invalid twitter oauth, please check your key and secret"
    except Exception,e:
        print_error("Invalid configuration specified, please check your key and secret: %s" % str(e))
        sys.exit(1)     

def run():
    config = get_config()

    CONSUMER_KEY = config["CONSUMER_KEY"]
    CONSUMER_SECRET = config["CONSUMER_SECRET"]
    ACCESS_TOKEN = config["ACCESS_TOKEN"]
    ACCESS_TOKEN_SECRET = config["ACCESS_TOKEN_SECRET"]

    logging.debug("XML ACCESS_TOKEN: " + ACCESS_TOKEN)
    logging.debug( "start run")
    
    auth = tweepy.OAuthHandler(CONSUMER_KEY, CONSUMER_SECRET)
    auth.set_access_token(ACCESS_TOKEN, ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)

    listener = SplunkListener()
    stream = tweepy.Stream(auth=auth, listener=listener)
    stream.sample()

if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            do_scheme()
        elif sys.argv[1] == "--validate-arguments":
            validate_arguments()
        elif sys.argv[1] == "--test":
            print 'No tests for the scheme present'
        else:
            print 'You giveth weird arguments'
    else:
        # just request data from Twitter
        run()

    sys.exit(0)

