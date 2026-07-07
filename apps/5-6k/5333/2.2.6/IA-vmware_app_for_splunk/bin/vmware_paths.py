"""
Written by Kyle Smith for Aplura, LLC
Copyright (C) 2016-2024 Aplura, LLC

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
"""
# Stub to allow global setting of sys path
import sys
import logging
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from vmware_app_for_splunk_props import __app_name__, __version__ as __app_version__

new_path = make_splunkhome_path(["etc", "apps", __app_name__, "lib"])
logger = logging.getLogger('splunk.rest')
logger.info(f"app=vmware_app_for_splunk. action=HARD_TO_FIND new_path={new_path}")
sys.path.insert(0, new_path)

