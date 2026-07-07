#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    0: "SERVICE_RUNS_IN_USER_PROCESS_OR_DOWN",
    1: "SERVICE_RUNS_IN_SYSTEM_PROCESS",
}

bitmask_lookup(lookup_table)
