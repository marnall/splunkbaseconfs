#!/usr/bin/env python

import sys
from shared import *
from ReversingLabs.SDK.ticloud import FileAnalysis


'''
ReversingLabs File Analysis External Lookup for Splunk
To be used in the Search & Reporting Splunk app as a "lookup" parameter.
Adds the ReversingLabs File Analysis API analysis results for a given hash to the Splunk Search & Reporting results.

Splunk Web usage example:
| lookup RL_fileanalysis hash_value AS <hash_field_in_results>
'''


def main():
    if len(sys.argv) != 2:
        print("Usage: python rldata.py [hash field]")
        sys.exit(1)

    hash_value = sys.argv[1]

    infile = sys.stdin
    outfile = sys.stdout

    fieldnames = [
        "hash_value",
        "RL_ERROR_message",
        "RL_sha1",
        "RL_md5",
        "RL_sha256",
        "RL_sha384",
        "RL_sha512",
        "RL_ripemd160",
        "RL_ssdeep",
        "RL_sample_size",
        "RL_first_seen",
        "RL_last_seen",
        "RL_sample_type",
        "RL_story",
        "RL_file_type",
        "RL_file_subtype"
    ]

    r = csv.DictReader(infile)
    w = csv.DictWriter(outfile, fieldnames=fieldnames)
    w.writeheader()

    for result in r:
        try:
            lookup_result = lookup(result[hash_value], FileAnalysis, "sample")
        except Exception:
            continue

        if lookup_result.get("RL_ERROR_message"):
            result["RL_ERROR_message"] = lookup_result.get("RL_ERROR_message", "")
            w.writerow(result)
            continue

        result["RL_sha1"] = lookup_result.get("sha1", "")
        result["RL_md5"] = lookup_result.get("md5", "")
        result["RL_sha256"] = lookup_result.get("sha256", "")
        result["RL_sha384"] = lookup_result.get("sha384", "")
        result["RL_sha512"] = lookup_result.get("sha512", "")
        result["RL_ripemd160"] = lookup_result.get("ripemd160", "")
        result["RL_ssdeep"] = lookup_result.get("ssdeep", "")
        result["RL_sample_size"] = lookup_result.get("sample_size", "")

        xref = lookup_result.get("xref")
        if xref:
            result["RL_first_seen"] = xref.get("first_seen", "")
            result["RL_last_seen"] = xref.get("last_seen", "")
            result["RL_sample_type"] = xref.get("sample_type", "")

        analysis = lookup_result.get("analysis")
        if analysis:
            entries = analysis.get("entries")

            if entries:
                try:
                    entry = entries[0]
                except IndexError:
                    w.writerow(result)
                    continue

                tc_report = entry.get("tc_report")
                result["RL_story"] = tc_report.get("story")
                info = tc_report.get("info")
                file = info.get("file")
                result["RL_file_type"] = file.get("file_type")
                result["RL_file_subtype"] = file.get("file_subtype")

        w.writerow(result)


if __name__ == "__main__":
    sys.stderr = open(os.path.join(os.path.dirname(os.getcwd()), "lookups", "debug.log"), "a")
    main()
