#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "RELOCS_STRIPPED",
    2: "EXECUTABLE_IMAGE",
    4: "LINE_NUMS_STRIPPED",
    8: "LOCAL_SYMS_STRIPPED",
    16: "AGGRESSIVE_WS_TRIM",
    32: "LARGE_ADDRESS_AWARE",
    128: "BYTES_RESERVED_LO",
    256: "_32BIT_MACHINE",
    512: "DEBUG_STRIPPED",
    1024: "REMOVABLE_RUN_FROM_SWAP",
    2048: "NET_RUN_FROM_SWAP",
    4096: "FILE_SYSTEM",
    8192: "FILE_DLL",
    16384: "UP_SYSTEM_ONLY",
    32768: "BYTES_RESERVED_HI",
}

bitmask_lookup(lookup_table)
