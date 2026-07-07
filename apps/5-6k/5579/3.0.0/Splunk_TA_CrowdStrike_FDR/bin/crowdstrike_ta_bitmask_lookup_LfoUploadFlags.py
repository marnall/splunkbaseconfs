#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "CLOUD_REQUEST",
    2: "FILE_IS_QUARANTINED",
    4: "UNKNOWN_PRIMARY_IMAGE",
    8: "EMPOWER",
    16: "ANDROID_APK",
    32: "ANDROID_EAPKS",
    64: "ANDROID_MANIFEST_XML",
    128: "SENSOR_LOGS",
    256: "PREEMPT_APPLICATION",
    512: "PREEMPT_TROUBLESHOOTING",
}

bitmask_lookup(lookup_table)
