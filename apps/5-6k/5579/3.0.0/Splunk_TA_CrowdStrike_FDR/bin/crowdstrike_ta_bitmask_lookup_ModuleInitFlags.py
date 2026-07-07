#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "MODULE_INIT_IGNORE_MODVERSIONS",
    2: "MODULE_INIT_IGNORE_VERMAGIC",
}

bitmask_lookup(lookup_table)
