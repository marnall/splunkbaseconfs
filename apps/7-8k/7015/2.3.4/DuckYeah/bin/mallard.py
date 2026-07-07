#!/usr/bin/env python

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

from datetime import datetime
from splunklib.searchcommands import \
    dispatch, StreamingCommand, Configuration, Option, validators

@Configuration()
class mallard(StreamingCommand):
    """ %(synopsis)

    ##Syntax

    %(syntax)

    ##Description

    %(description)

    """

    quack = Option(require=True, validate=None)

    def stream(self, events):
        for event in events:
            event['APP_HOME'] = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', event['app'])
            if self.quack == 'syscheck':
                if os.path.exists(os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', event['app'], '.git', 'HEAD')):
                    event['isgit'] = True
                else:
                    event['isgit'] = False

                yield event
            if self.quack == 'localconf':
                for file in os.listdir(os.path.join(event['APP_HOME'], 'local')):

                    event['filename'] = file
                    yield event
            if self.quack == 'manifest':
                app_manifest = os.path.join(event['APP_HOME'], 'app.manifest')

                event['supportedDeployments'] = [];

                if not os.path.exists(app_manifest):
                    yield event
                else:
                    with open(app_manifest, 'r') as f:
                        manifest = json.loads(f.read())

                    if 'supportedDeployments' in manifest:
                        for deployment in manifest['supportedDeployments']:
                            event['supportedDeployments'].append(deployment)

                    yield event

                    

dispatch(mallard, sys.argv, sys.stdin, sys.stdout, __name__)
