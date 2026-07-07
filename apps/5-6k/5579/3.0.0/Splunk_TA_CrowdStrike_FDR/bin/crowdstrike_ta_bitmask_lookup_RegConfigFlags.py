#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "GLOBAL",
    4: "NEEDS_SOURCE_SIGNED",
    16: "NEEDS_SOURCE_MS_SIGNED",
    64: "SUSPICIOUS",
}

bitmask_lookup(lookup_table)
