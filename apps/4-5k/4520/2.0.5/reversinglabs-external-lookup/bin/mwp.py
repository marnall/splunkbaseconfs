#!/usr/bin/env python

import sys
from shared import *
from ReversingLabs.SDK.ticloud import FileReputation

'''
ReversingLabs File Reputation External Lookup for Splunk
To be used in the Search & Reporting Splunk app as a "lookup" parameter.
Adds the ReversingLabs File Reputation API analysis results for a given hash to the Splunk Search & Reporting results.

Splunk Web usage example:
| lookup RL_filereputation hash_value AS <hash_field_in_results>
'''


def main():
    if len(sys.argv) != 2:
        print("Usage: python mwp.py [hash field]")
        sys.exit(1)

    hash_value = sys.argv[1]

    infile = sys.stdin
    outfile = sys.stdout

    fieldnames = [
        "hash_value",
        "RL_ERROR_message",
        "RL_status",
        "RL_threat_level",
        "RL_threat_name",
        "RL_trust_factor",
        "RL_first_seen",
        "RL_last_seen",
        "RL_md5",
        "RL_sha1",
        "RL_sha256",
        "RL_scanner_count",
        "RL_scanner_match",
        "RL_scanner_percent",
        "RL_classification_family_name",
        "RL_classification_is_generic",
        "RL_classification_type",
        "RL_classification_platform",
        "RL_classification_subplatform",
        "RL_cve_is_candidate",
        "RL_cve_number",
        "RL_cve_year"
    ]

    r = csv.DictReader(infile)
    w = csv.DictWriter(outfile, fieldnames=fieldnames)
    w.writeheader()

    for result in r:
        try:
            lookup_result = lookup(result[hash_value], FileReputation, "malware_presence")
        except Exception:
            continue

        if lookup_result.get("RL_ERROR_message"):
            result["RL_ERROR_message"] = lookup_result.get("RL_ERROR_message", "")
            w.writerow(result)
            continue

        result["RL_status"] = lookup_result.get("status", "")
        result["RL_threat_level"] = lookup_result.get("threat_level", "")
        result["RL_threat_name"] = lookup_result.get("threat_name", "")
        result["RL_trust_factor"] = lookup_result.get("trust_factor", "")
        result["RL_first_seen"] = lookup_result.get("first_seen", "")
        result["RL_last_seen"] = lookup_result.get("last_seen", "")
        result["RL_md5"] = lookup_result.get("md5", "")
        result["RL_sha1"] = lookup_result.get("sha1", "")
        result["RL_sha256"] = lookup_result.get("sha256", "")
        result["RL_scanner_count"] = lookup_result.get("scanner_count", "")
        result["RL_scanner_match"] = lookup_result.get("scanner_match", "")
        result["RL_scanner_percent"] = lookup_result.get("scanner_percent", "")
        classification = lookup_result.get("classification")
        if classification:
            result["RL_classification_family_name"] = classification.get("family_name", "")
            result["RL_classification_is_generic"] = classification.get("is_generic", "")
            result["RL_classification_type"] = classification.get("type", "")
            if classification.get("platform"):
                result["RL_classification_platform"] = classification.get("platform", "")
            if classification.get("subplatform"):
                result["RL_classification_subplatform"] = classification.get("subplatform", "")
            cve = classification.get("cve")
            if cve:
                result["RL_cve_is_candidate"] = cve.get("is_candidate", "")
                result["RL_cve_number"] = cve.get("number", "")
                result["RL_cve_year"] = cve.get("year", "")
        w.writerow(result)


if __name__ == "__main__":
    main()


