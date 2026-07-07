#!/usr/bin/env python

import csv
import sys
import binascii
import chardet

def main():
    if len(sys.argv) != 3:
        print("Usage: python checkhexstringencoding_lookup.py [Hex-STRING field] [Encoding field]")
        sys.exit(1)

    hexstring_field = sys.argv[1]
    encoding_field = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        encoding = result[encoding_field] if result[encoding_field] else chardet.detect(binascii.unhexlify(result[hexstring_field]))["encoding"]
        result[encoding_field] = encoding
        w.writerow(result)

main()
