#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    0: "NO_DRIVERS_BLOCKED",
    1: "PREVENTED_STARTUP",
    2: "READING_KEY_FAILED",
    4: "MISSING_SIGNATURE_DATA",
    8: "CORRUPT_SIGNATURE_DATA",
    16: "DISABLED_BY_TAG",
    32: "DRIVERS_BLOCKED",
    64: "DRIVERS_NOT_BLOCKABLE",
    128: "ATTESTATION_REVOKED",
    256: "MISSING_TELEMETRY_DATA",
    512: "CORRUPT_TELEMETRY_DATA",
    1024: "ENVIRONMENT_TAMPERING",
}

bitmask_lookup(lookup_table)
