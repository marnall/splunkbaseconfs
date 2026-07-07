#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    0: "INVALID",
    1: "AX",
    2: "CX",
    4: "SP",
    8: "IP",
    2147483648: "CONTEXT",
}

bitmask_lookup(lookup_table)
