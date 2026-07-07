#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "ASSEMBLY_DOMAIN_NEUTRAL",
    2: "ASSEMBLY_DYNAMIC",
    4: "ASSEMBLY_HAS_NATIVE_IMAGE",
    8: "ASSEMBLY_COLLECTIBLE",
}

bitmask_lookup(lookup_table)
