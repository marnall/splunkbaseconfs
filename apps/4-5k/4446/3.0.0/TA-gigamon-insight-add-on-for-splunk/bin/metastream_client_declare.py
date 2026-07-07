# encode = utf-8
import os
import sys
import re

ta_lib_name = 'ta_gigamon_insight_add_on_for_splunk'
metastream_client = 'metastream_client'

pattern = re.compile(r"[\\/]etc[\\/]apps[\\/][^\\/]+[\\/]bin[\\/]metastream_client[\\/]?$")
new_paths = [path for path in sys.path if not pattern.search(path)]
new_paths.insert(0, os.path.sep.join([os.path.dirname(__file__), metastream_client]))

sys.path = new_paths