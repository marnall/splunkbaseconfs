# @File  : _paths.py.py
# @Author: ksmith
# @Date  : 6/15/23
# @Desc  : 
# @license: Copyright(c) 2020-2023, Aplura, LLC
import sys
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from app_properties import __app_name__

sys.path.insert(0, make_splunkhome_path(["etc", "apps", __app_name__, "lib"]))
