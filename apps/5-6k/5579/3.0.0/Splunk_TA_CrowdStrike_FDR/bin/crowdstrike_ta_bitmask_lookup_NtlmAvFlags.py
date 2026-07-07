#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "CONSTRAINED_AUTHENTICATION",
    2: "MESSAGE_INTEGRITY",
    4: "UNTRUSTED_SPN_SOURCE",
}

bitmask_lookup(lookup_table)
