#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    0: "CREATED",  # 0x00000000
    1: "DELETED",  # 0x00000001
    2: "MODIFIED",  # 0x00000002
    4: "GROUP_MEMBER_ADDED",  # 0x00000004
    8: "GROUP_MEMBER_REMOVED",  # 0x00000008
    16: "PASSWORD_CHANGE",  # 0x00000010
    32: "PASSWORD_RESET",  # 0x00000020
    64: "ENABLED",  # 0x00000040
    128: "DISABLED",  # 0x00000080
    256: "LOCKED",  # 0x00000100
    512: "UNLOCKED",  # 0x00000200
    1024: "UNDELETED",  # 0x00000400
    2048: "MOVED",  # 0x00000800
    4096: "GPO_SETTINGS_VERSION_CHANGED",  # 0x00001000
}

bitmask_lookup(lookup_table)
