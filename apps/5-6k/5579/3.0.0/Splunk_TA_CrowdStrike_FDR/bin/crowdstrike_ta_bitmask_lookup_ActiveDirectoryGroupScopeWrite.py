#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "UNIVERSAL",  # 0x00000001
    2: "GLOBAL",  # 0x00000002
    4: "LOCAL",  # 0x00000004
}

bitmask_lookup(lookup_table)
