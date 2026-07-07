#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "RAW_SOCKET",
    2: "PROMISCUOUS_MODE_SIO_RCVALL",
    4: "PROMISCUOUS_MODE_SIO_RCVALL_IGMPMCAST",
    8: "PROMISCUOUS_MODE_SIO_RCVALL_MCAST",
}

bitmask_lookup(lookup_table)
