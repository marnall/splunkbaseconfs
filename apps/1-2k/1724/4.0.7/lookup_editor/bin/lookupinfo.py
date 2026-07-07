import json

import splunk.Intersplunk
from splunk.rest import simpleRequest

from lookup_editor_rest_handler import LookupEditorHandler

results,dummy,settings = splunk.Intersplunk.getOrganizedResults()
sessionKey = settings.get("sessionKey")

url = "/services/data/lookup_edit/file_size?output_mode=json"
response, data = simpleRequest(url, method="GET", sessionKey=sessionKey)
res = json.loads(data)

splunk.Intersplunk.outputResults(res)