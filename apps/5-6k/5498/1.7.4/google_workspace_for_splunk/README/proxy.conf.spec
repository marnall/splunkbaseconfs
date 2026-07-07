#proxy.conf.spec
#'''
# Written by Kyle Smith for Aplura, LLC
# Copyright (C) 2021 Aplura, ,LLC
##
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
##
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
##
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
# '''
[<proxy_stanza>]
*This is how the Proxy is configured

guid = <value>
* The proxy guid

proxy_url = <value>
* The Proxy Host and port

proxy_user = <value>
*The Proxy User for autnehnticated proxies.

use_ssl = <bool>
* This flag true to use SSL

verify_ssl = <bool>
* This flag to verify

proxy_name = <value>
* This is the name of the proxy for readability
