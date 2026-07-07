#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    0: "UNTRUSTED",
    4096: "LOW",
    8192: "MEDIUM",
    8448: "MEDIUM_PLUS",
    12288: "HIGH",
    16384: "SYSTEM",
    20480: "PROTECTED",
}

bitmask_lookup(lookup_table)
