from __future__ import print_function
import sys,re
import shutil, os
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, Boolean
import base64
import json
import time
import collections
import logging
from lib import utils

@Configuration(type='reporting', local=True)
class InstallCW(GeneratingCommand):
    dry_run = Option(validate=Boolean(), default=False)
    force = Option(validate=Boolean(), default=False)

    def prepare(self):
        self.logger.setLevel(logging.DEBUG)
        self.logger.debug("Initializing command")
        if self.service is None:
            raise Exception('Configuration requires_srinfo in commands.conf must be true')
            return
        self.logger.debug(self.service.confs)

    def generate(self):
        self.logger.debug("Installing ControlWatch")
        self.logger.debug(self.service.splunk_version)

        is_configured = int(utils.getVariable(self.service, "app", "install", "is_configured"))
        if is_configured != 1 or self.force:
            version = self.service.splunk_version
            if version[0] < 7 or (version[0] == 7 and version[1] < 1):
                shutil.copy(
                        '../appserver/static/css/common/shim_bak.css',
                        '../appserver/static/css/common/shim.css'
                        )
                yield { "jobs": None, "name": "Deploy CSS Shim" }

            self.search_names = []
            self.searches = []
            for search in self.service.saved_searches.list():
                if search.name.startswith("[DEPLOY]"):
                    self.searches.append(search)
                    self.search_names.append({'name': search.name})
            utils.setVariable(self.service, "app", "install", "is_configured", 1)
            for search in self.searches:
                job_id = "Job Not Created"
                if not self.dry_run:
                    job = search.dispatch()
                    job_id = job.content["sid"]
                yield { "jobs": job_id, "name": search.name }
        else:
            yield {"response": "Already Configured"}

if __name__ == '__main__':
   dispatch(InstallCW, sys.argv, sys.stdin, sys.stdout, __name__)
