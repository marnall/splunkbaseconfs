import sys
import splunk
import splunklib.client
import splunklib.results
import splunklib.binding
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, Boolean
import splunk.mining.dcutils
from asx_lib import ASXLib
from splunk.clilib import cli_common as cli
import time

@Configuration(streaming=True, local=True)
class ASXUpdate(GeneratingCommand):
    logger = splunk.mining.dcutils.getLogger()

    list_all = Option(doc='''
        **Syntax: update_all=<bool>
        **Description:** When `true`, retrives all analytics stories from the API.
        Defaults to `false`.
        ''', name='list_all', default=False, validate=Boolean())

    story = Option(doc='''
        **Syntax:** **story=***<story name>*
        **Description:** Story to update.
        ''', name='story', require=False, default=None)

    def getURL(self):
        cfg = cli.getConfStanza('asx','settings')
        self.logger.info("asxupdate.py - asx_conf: {0}".format(cfg['api_url']))
        return cfg['api_url']

    def generate(self):
        # connect to splunk and start execution
        port = splunk.getDefault('port')
        service = splunklib.client.connect(token=self._metadata.searchinfo.session_key, port=port, owner="nobody",app="Splunk_ASX")
        API_URL = self.getURL()
        asx_lib = ASXLib(service, API_URL)
        self.logger.info("asxupdate.py - start")

        if self.list_all:
            self.logger.info("asxupdate.py - list all stories")
            stories = asx_lib.list_analytics_stories()
            for story in stories:
                self.logger.info("asxupdate.py - processing story {0}".format(story['name']))

                yield {
                    '_time': time.time(),
                    'sourcetype': "_json",
                    '_raw': {'name': story['name']},
                    'status': "successfully listed all stories"
                }
        # only updating specific stories
        if self.story and self.story != "all":
            self.logger.info("asxupdate.py - stories to update {0}".format(self.story))
            stories = self.story.split(",")
            for story in stories:
                self.logger.info("asxupdate.py - updating story {0}".format(story))
                asx_lib.get_analytics_story(story)
                yield {
                    '_time': time.time(),
                    'sourcetype': "_json",
                    '_raw': story,
                    'status': "successfully updated story"
                }
        # lets update all stories, disabled until spec 3.0 change
        else:
            self.logger.info("asxupdate.py - updating ALL stories")
            stories = asx_lib.list_analytics_stories()
            for story in stories:
                self.logger.info("asxupdate.py - updating story {0}".format(story['name']))
                #asx_lib.get_analytics_story(story)
                yield {
                    '_time': time.time(),
                    'sourcetype': "_json",
                    '_raw': story['name'],
                    'status': "successfully updated story"
                }

        self.logger.info("asxupdate.py - COMPLETED")

    def __init__(self):
        super(ASXUpdate, self).__init__()

dispatch(ASXUpdate, sys.argv, sys.stdin, sys.stdout, __name__)
