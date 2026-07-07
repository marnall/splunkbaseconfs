#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    16384: "LOGON_OPTIMIZED",
    32768: "LOGON_WINLOGON",
    65536: "LOGON_PKINIT",
    131072: "LOGON_NOT_OPTIMIZED",
}

bitmask_lookup(lookup_table)
