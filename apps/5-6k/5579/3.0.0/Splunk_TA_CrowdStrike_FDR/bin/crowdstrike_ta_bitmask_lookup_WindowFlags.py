#
# SPDX-FileCopyrightText: 2021 Splunk, Inc. <sales@splunk.com>
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

from crowdstrike_ta_bitmask_lookup import bitmask_lookup

lookup_table = {
    1: "STARTF_USESHOWWINDOW",
    2: "STARTF_USESIZE",
    4: "STARTF_USEPOSITION",
    8: "STARTF_USECOUNTCHARS",
    16: "STARTF_USEFILLATTRIBUTE",
    32: "STARTF_RUNFULLSCREEN",
    64: "STARTF_FORCEONFEEDBACK",
    128: "STARTF_FORCEOFFFEEDBACK",
    256: "STARTF_USESTDHANDLES",
    512: "STARTF_USEHOTKEY",
    1024: "STARTF_MONITOR",
    2048: "STARTF_TITLEISLINKNAME",
    4096: "STARTF_TITLEISAPPID",
    8192: "STARTF_PREVENTPINNING",
    32768: "STARTF_UNTRUSTEDSOURCE",
    2147483648: "STARTF_SCREENSAVER",
}

bitmask_lookup(lookup_table)
