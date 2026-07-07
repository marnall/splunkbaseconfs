#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "GLOBAL",
    2: "PRIVILEGED",
    4: "NEEDS_SOURCE_SIGNED",
    8: "NEEDS_TARGET_SIGNED",
    16: "NEEDS_SOURCE_MS_SIGNED",
    32: "NEEDS_TARGET_MS_SIGNED",
    64: "SENSOR_ONLY",
    128: "AMSI_PROVIDER",
    256: "FIREWALL_RULE_V2",
    512: "AMSI_PROVIDER_V2",
    1024: "ANTI_TAMPERING_V2",
    2048: "ANTI_TAMPERING_V3",
}

bitmask_lookup(lookup_table)
