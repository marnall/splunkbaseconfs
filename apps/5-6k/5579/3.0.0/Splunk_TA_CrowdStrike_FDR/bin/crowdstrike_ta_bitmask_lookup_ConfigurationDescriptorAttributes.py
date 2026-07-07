#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {32: "REMOTE_WAKEUP", 64: "SELF_POWERED", 128: "RESERVED"}

bitmask_lookup(lookup_table)
