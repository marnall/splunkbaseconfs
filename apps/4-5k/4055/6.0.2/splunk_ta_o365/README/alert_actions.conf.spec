##
## SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
[splunk_ta_o365_add_member_to_group]
python.version = python3
python.required = 3.9, 3.13
param.tenant_name = <list>, The Tenant name configured in Splunk Add-on for Microsoft Office 365.
param.group_id = <string>, Id of the group to which the member should be added.
param.member_id = <string>, The Id of the member to be added to the group.
