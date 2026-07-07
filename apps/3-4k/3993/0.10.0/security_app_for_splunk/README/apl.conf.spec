#apl.conf.spec
#'''
# Written by Kyle Smith for Aplura, LLC
# Copyright (C) 2020 Aplura, ,LLC
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
[apl]
* This is how the Security App for Splunk is configured

configuration_guid = <value>
* This is a pointer to an encrypted credential that contains the configuration JSON.

show_wizard = <boolean>
* This determines if the wizard needs to be shown on login.

eula_agree = <value>
* This is a version of the eula that was agreed to, if the User has accepted the EULA.

instanceId = <value>
* This is the instance ID of the app

offline = <boolean>
* This is a flag to indicate if the instance is offline or not.

[eula]
* This is EULA management for the Splunk App

eula_agree = <value>
* This is a version of the eula that was agreed to, if the User has accepted the EULA. Duplicate from APL stanza for legacy.

[checkpoints]
* This is Checkpoints for API operations. Using this file allows for SHC replication to other SH.

searches = <value>
* This is a checkpoint for the last time checkpoints for search content were set.

news = <value>
* This is a checkpoint for the last time checkpoints for news content were set.

lookups = <value>
* This is a checkpoint for the last time checkpoints for lookups content were set.

announcements = <value>
* This is a checkpoint for the last time checkpoints for announcements were set.

[pavo_messages]
* This is the messages that we can't put in messages.conf

message      = <value>
action       = <value>
severity     = <value>
roles = <value>