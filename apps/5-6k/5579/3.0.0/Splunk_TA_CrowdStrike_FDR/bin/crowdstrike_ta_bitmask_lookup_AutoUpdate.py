#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "AUTOMATIC_CHECK",
    2: "AUTOMATIC_DOWNLOAD",
    4: "AUTOMATIC_INSTALL",
    8: "INSTALL_CONFIG",
    16: "INSTALL_CRITICAL_UPDATE",
}

bitmask_lookup(lookup_table)
