#!/usr/bin/env python

"""
    This takes a CSV of DNS wire protocol data (RDATA) and the type
    (record_type or RTYPE) and uses the
    dnslib library to translate this information into readable text

    The RTYPEs included in the library are CNAME, A, AAAA, TXT,
    MX, PTR, SOA, NS, NAPTR, SRV,
    DNSKEY, RRSIG, NSEC, CAA

    It is based on the external_lookup.py that is shipped with
    Splunk Enterprise.
"""

import csv
import sys
import re
import binascii
import dnslib


def replace(string, substitutions):
    """
    Replaces multiple patterns in a string
    :param string: string to replace sequences in
    :param substitutions: dictionary of things to subsititute
    :return:
    """
    substrings = sorted(substitutions, key=len, reverse=True)
    regex = re.compile('|'.join(map(re.escape, substrings)))
    return regex.sub(lambda match: substitutions[match.group(0)], string)


def generic_parse(rdata, rtype):
    """
    Translates the RDATA based on RTYPE
    :param rdata: untranslate DNS wire data
    :param rtype: type of the untranslated DNS wire data
    :return: translated RDATA
    """
    unhex_rdata = binascii.unhexlify(str.encode(rdata))
    b = dnslib.DNSBuffer(unhex_rdata)
    module = getattr(dnslib, rtype)
    translation = str(module.parse(b, len(b)))
    if str(rtype) != "A" and str(rtype) != "AAAA":
        match = re.search(r'\\\d{3}\\\d{3}(?P<domain>.*)\.', translation)
        substitutions = {"\\005": ".", "\\003": ".", "\\004": "."}
        translation = replace(str(match.group('domain')), substitutions)
    return translation


def backup_parse(rdata):
    """
    Tries to unhexify rdata
    :param rdata: hex string
    :param rtype: dns record type string
    :return: ascii string
    """
    translation = rdata.decode("hex")
    translation = translation.lstrip()
    if translation.endswith('.'):
        translation = translation[:-1]
    return translation


def main():
    """
    Get results from Splunk and translate the RDATA field
    :return: Splunk results via stdout
    """
    if len(sys.argv) != 4:
        print("Usage: external_protocol_translation_lookup.py "
              "[RDATA field] [record_type field] [translation field]")
        sys.exit(1)

    # Setup file paths. Main input and output will be via stdin/stdout.
    infile = sys.stdin
    outfile = sys.stdout

    # Shortnames for all of the field names we are using. See the usage line
    # for details.
    rdata_field = sys.argv[1]
    rtype_field = sys.argv[2]
    translation = "translation"

    # Tie stdin to the CSV reader to process the incoming CSV from Splunk
    records = csv.DictReader(infile)
    header = records.fieldnames # pylint: disable=unused-variable

    # Tie stdout to a CSV Writer to dump results back to Splunk.
    w = csv.DictWriter(outfile, fieldnames=records.fieldnames)
    w.writeheader()

    # Process each original line from Splunk, one line per IP address
    for record in records:
        # Perform the lookup if necessary
        if record[rdata_field] and record[rtype_field]:
            try:
                record[translation] = generic_parse(record[rdata_field], record[rtype_field])
            except Exception as err: # pylint: disable=broad-except
                record[translation] = backup_parse(record[rdata_field], record[rtype_field]) # pylint: disable=too-many-function-args
                print("Error in execution: %s" % str(err)) # pylint: disable=consider-using-f-string
                pass # pylint: disable=unnecessary-pass
            if record[translation]:
                w.writerow(record)

if __name__ == "__main__":
    main()
