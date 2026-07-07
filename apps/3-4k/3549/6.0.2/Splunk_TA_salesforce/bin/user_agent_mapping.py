#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#

"""
This file contains certain ignores for certain linters.

* isort ignores:
- isort: skip = Particular import must be the first import.

* flake8 ignores:
- noqa: F401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path
"""

import import_declare_test  # isort: skip # noqa: F401
import csv
import sys
import traceback
import sfdc_log_helper


logger = sfdc_log_helper.Log().get_logger("user_agent_mapping_lookup")


def main():
    """
    This scripted lookup will map the ID of USER_AGENT
    to the value of USER_AGENT based on Salesforce mapping
    """

    # prints usage of the lookup script if wrong number of arguments provided
    if len(sys.argv) != 4:
        logger.error(
            "Usage: python user_agent_mapping.py [USER_AGENT] [http_user_agent] [http_user_agent_length]"
        )
        logger.error("Lookup script stopped..")
        sys.exit(1)

    # Lookup Field names
    # USER_AGENT = sys.argv[1]
    http_user_agent = sys.argv[2]
    # http_user_agent_length = sys.argv[3]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)

    w.writeheader()

    BROWSER_CODE_MAPPING = {
        "10": "Internet Explorer {}",
        "11": "Firefox {}",
        "13": "Chrome {}",
        "14": "Safari {}",
        "15": "Opera {}",
        "16": "Android {}",
        "17": "Netscape {}",
        "18": "Webkit {}",
        "19": "Gecko {}",
        "23": "Blackberry {}",
        "24": "Good Access {}",
    }

    for result in r:
        try:

            # Logic to convert USER_AGENT ID (13008491) to appropriate user agent string
            if result["USER_AGENT"].isdigit():

                # The first two digits are reserved for browser family/name.
                browser_code = result["USER_AGENT"][:2]

                # The next three digits are for user agent version numbers, such as "008" for version 8.
                browser_version = result["USER_AGENT"][2:5]

                http_user_agent = BROWSER_CODE_MAPPING.get(
                    browser_code, "vendor_unknown"
                ).format(browser_version.lstrip("0"))

                # Updating values into result
                result["http_user_agent"] = http_user_agent
                result["http_user_agent_length"] = len(http_user_agent)

                # Writing back to the event
                w.writerow(result)

            else:
                # Default case when valid USER_AGENT string is present.
                result["http_user_agent"] = result["USER_AGENT"]
                result["http_user_agent_length"] = len(result["USER_AGENT"])
                w.writerow(result)

        except Exception as e:
            logger.error(
                f"Error faced in lookup mapping for USER_AGENT {result['USER_AGENT']} \n"
                f"Traceback = {traceback.format_exc()}"
            )


if __name__ == "__main__":
    main()
