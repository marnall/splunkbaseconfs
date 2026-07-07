#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "FILE_ATTRIBUTE_READONLY",
    2: "FILE_ATTRIBUTE_HIDDEN",
    4: "FILE_ATTRIBUTE_SYSTEM",
    16: "FILE_ATTRIBUTE_DIRECTORY",
    32: "FILE_ATTRIBUTE_ARCHIVE",
    64: "FILE_ATTRIBUTE_DEVICE",
    128: "FILE_ATTRIBUTE_NORMAL",
    256: "FILE_ATTRIBUTE_TEMPORARY",
    512: "FILE_ATTRIBUTE_SPARSE_FILE",
    1024: "FILE_ATTRIBUTE_REPARSE_POINT",
    2048: "FILE_ATTRIBUTE_COMPRESSED",
    4096: "FILE_ATTRIBUTE_OFFLINE",
    8192: "FILE_ATTRIBUTE_NOT_CONTENT_INDEXED",
    16384: "FILE_ATTRIBUTE_ENCRYPTED",
}

bitmask_lookup(lookup_table)
