"""
Sample Twitter streaming API client

USAGE
    ./tweet.py [<FILTER_KEYWORD>]

    FILTER_KEYWORD
        string on which to search Twitter, or * to get the standard 1% firehose

"""

import __main__
import sys
import tweepy

try:
    import splunk.clilib.cli_common as comm
except ImportError, e:
    'This script must be run from within the Splunk python context; %s' % e


class Listener(tweepy.StreamListener):
    """
    define twitter firehose stream iterator
    see https://github.com/joshthecoder/tweepy/blob/master/tweepy/streaming.py
    """

    def on_status(self, status):
        try:
            text = status.text.replace('"', "'").replace('\n',' ')
            tags = [x['text'] for x in status.entities['hashtags']]
            author = status.author.screen_name
            create_time = status.created_at.strftime('%Y-%m-%d %H:%M:%S')
            client_type = status.source
            avatar = status.author.profile_image_url
    
            if tags:
                sys.stdout.write((u'%s  client_type="%s" author="%s" avatar="%s" tags="%s" tweet="%s"\n' % (
                    create_time, 
                    client_type, 
                    author, 
                    avatar, 
                    ','.join(tags), 
                    text)).encode('utf-8'))
            
            else:
                sys.stdout.write((u'%s  client_type="%s" author="%s" avatar="%s" tweet="%s"\n' % (
                    create_time, 
                    client_type, 
                    author, 
                    avatar, 
                    text)).encode('utf-8'))
            
            sys.stdout.flush()
        
        except Exception, e:
            print e
        

    def on_error(self, status_code):
        print 'tweepy returned HTTP status %s' % status_code



#
# main
#

if __name__ == "__main__":

    if len(sys.argv) == 2:
        filter_keyword = sys.argv[1]
    elif len(sys.argv) == 1:
        filter_keyword = '*'
    else:
        print __doc__
        sys.exit()

    # fetch oauth params
    for k in ('consumer_key', 'consumer_secret', 'access_key', 'access_secret'):
        setattr(__main__, k, comm.getConfKeyValue('tweepy', 'oauth', k))


    # setup stream
    auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
    auth.set_access_token(access_key, access_secret)
    listener = Listener()
    stream = tweepy.Stream(auth, listener)

    # choose stream source and start yielding
    if filter_keyword == '*':
        stream.sample()
    else:
        stream.filter(track=[filter_keyword])
