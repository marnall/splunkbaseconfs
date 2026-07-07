#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "SIGNATURE_REQUIRED",
    2: "SECURE_DESKTOP",
    4: "SPLIT_TOKEN",
    8: "HYBRID_PROMPT",
    16: "FOREGROUND_REQUESTOR",
    32: "NO_SIGNATURE_REQUIRED",
    64: "WINDOWS_DIRECTORY_IMAGE",
    128: "AUTO_APPROVED_MICROSOFT_SIGNED_IMAGE",
    256: "EXE_AUTO_APPROVAL",
}

bitmask_lookup(lookup_table)
