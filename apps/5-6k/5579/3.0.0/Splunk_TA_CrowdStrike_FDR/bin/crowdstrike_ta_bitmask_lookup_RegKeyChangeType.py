#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "SECURITY_DESCRIPTOR_REMOVED",
    2: "DACL_NULLED",
    4: "OWNER_CHANGED",
    8: "USER_ADDED",
    16: "USER_PERMISSION_CHANGED",
}

bitmask_lookup(lookup_table)
