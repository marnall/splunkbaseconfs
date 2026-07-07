#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "BASE_SXS_HAS_MANIFEST",
    2: "BASE_SXS_HAS_POLICY",
    8: "BASE_SXS_HAS_ASSEMBLY",
    32: "BASE_SXS_NO_ISOLATION",
    64: "BASE_SXS_LOCAL",
    256: "BASE_SXS_USING_OVERRIDE_MANIFEST",
}

bitmask_lookup(lookup_table)
