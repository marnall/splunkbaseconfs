#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "LOGON_IS_SYNTHETIC",
    2: "USER_IS_ADMIN",
    4: "USER_IS_LOCAL",
    8: "USER_IS_BUILT_IN",
    16: "USER_IDENTITY_MISSING",
}

bitmask_lookup(lookup_table)
