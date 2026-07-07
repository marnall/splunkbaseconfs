import mint.utils as utils
logger = utils.logger

import splunk
import splunk.admin as admin
import splunk.entity as en
import mint.sc_rest as sc_rest
import requests

"""
EAI REST Handler to persist Projects
"""
class ProjectsHandler(sc_rest.BaseRestHandler):

    def __init__(self, *args, **kwargs):
        sc_rest.BaseRestHandler.__init__(self, *args, **kwargs)

"""
allow_extra means allow extra parameters to persist.
"""
class Projects(object):
    endpoint = "configs/conf-projects"
    required_args = ["packages"]
    allow_extra = True

if __name__ == "__main__":
    admin.init(sc_rest.ResourceHandler(Projects, handler=ProjectsHandler), admin.CONTEXT_APP_ONLY)
