#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "CS_VALID",
    2: "CS_ADHOC",
    4: "CS_GET_TASK_ALLOW",
    8: "CS_INSTALLER",
    16: "CS_FORCED_LV",
    32: "CS_INVALID_ALLOWED",
    256: "CS_HARD",
    512: "CS_KILL",
    1024: "CS_CHECK_EXPIRATION",
    2048: "CS_RESTRICT",
    4096: "CS_ENFORCEMENT",
    8192: "CS_REQUIRE_LV",
    16384: "CS_ENTITLEMENTS_VALIDATED",
    32768: "CS_NVRAM_UNRESTRICTED",
    65536: "CS_RUNTIME",
    1048576: "CS_EXEC_SET_HARD",
    2097152: "CS_EXEC_SET_KILL",
    4194304: "CS_EXEC_SET_ENFORCEMENT",
    8388608: "CS_EXEC_INHERIT_SIP",
    16777216: "CS_KILLED",
    33554432: "CS_DYLD_PLATFORM",
    67108864: "CS_PLATFORM_BINARY",
    134217728: "CS_PLATFORM_PATH",
    268435456: "CS_DEBUGGED",
    536870912: "CS_SIGNED",
    1073741824: "CS_DEV_CODE",
    2147483648: "CS_DATAVAULT_CONTROLLER",
}

bitmask_lookup(lookup_table)
