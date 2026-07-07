#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    64: "DYNAMIC_BASE",
    128: "FORCE_INTEGRITY",
    256: "NX_COMPAT",
    512: "NO_ISOLATION",
    1024: "NO_SEH",
    2048: "NO_BIND",
    8192: "WDM_DRIVER",
}

bitmask_lookup(lookup_table)
