#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "ARMEABI",
    2: "ARM_V7A",
    4: "ARM_V8A",
    8: "X86",
    16: "X86_64",
    32: "MIPS",
    64: "MIPS64",
}

bitmask_lookup(lookup_table)
