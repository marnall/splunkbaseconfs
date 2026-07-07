#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "ENABLED",
    2: "TIMER",
    4: "VALID_PID",
    8: "NO_PID",
    16: "EXPIRED_PID",
    32: "CORRELATOR_1",
    64: "CORRELATOR_2",
    128: "CORRELATOR_3",
    256: "RUNDOWN_FAILURE",
    512: "PRIOR_TRIGGER_EXISTS",
}

bitmask_lookup(lookup_table)
