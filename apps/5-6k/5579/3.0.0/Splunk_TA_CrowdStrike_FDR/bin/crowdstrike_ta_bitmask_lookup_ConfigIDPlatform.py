#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "AGENT_PLATFORM_WIN7_X86",
    2: "AGENT_PLATFORM_WIN7_X64",
    4: "AGENT_PLATFORM_MACOS",
    8: "AGENT_PLATFORM_LINUX",
    16: "AGENT_PLATFORM_ANDROID",
    32: "AGENT_PLATFORM_IOS",
    128: "AGENT_PLATFORM_LINUX_AARCH64",
    256: "AGENT_PLATFORM_LINUX_LUMOS_X64",
}

bitmask_lookup(lookup_table)
