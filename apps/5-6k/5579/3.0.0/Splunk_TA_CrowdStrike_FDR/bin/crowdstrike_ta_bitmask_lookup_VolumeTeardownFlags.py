#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "FLTFL_INSTANCE_TEARDOWN_MANUAL",
    2: "FLTFL_INSTANCE_TEARDOWN_FILTER_UNLOAD",
    4: "FLTFL_INSTANCE_TEARDOWN_MANDATORY_FILTER_UNLOAD",
    8: "FLTFL_INSTANCE_TEARDOWN_VOLUME_DISMOUNT",
    16: "FLTFL_INSTANCE_TEARDOWN_INTERNAL_ERROR",
}

bitmask_lookup(lookup_table)
