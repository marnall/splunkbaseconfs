#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "ECP_SRV_OPEN",
    2: "ECP_CS_SENSOR_OPEN",
    4: "ECP_CS_SENSOR_FILE_CHARACTERISTICS",
}

bitmask_lookup(lookup_table)
