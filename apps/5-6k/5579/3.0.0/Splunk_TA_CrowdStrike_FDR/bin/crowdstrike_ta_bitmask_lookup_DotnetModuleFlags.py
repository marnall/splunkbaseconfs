#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "DOTNET_MODULE_DOMAIN_NEUTRAL",
    2: "DOTNET_MODULE_HAS_NATIVE_IMAGE",
    4: "DOTNET_MODULE_DYNAMIC",
    8: "DOTNET_MODULE_MANIFEST",
}

bitmask_lookup(lookup_table)
