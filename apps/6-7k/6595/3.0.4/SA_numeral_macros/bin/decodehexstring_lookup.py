#!/usr/bin/env python

import csv
import sys
import binascii

def main():
    if len(sys.argv) != 4:
        print("Usage: python decodehexstring_lookup.py [Hex-STRING field] [Encoding field] [Decoded-STRING field]")
        sys.exit(1)

    hexstring_field = sys.argv[1]
    encoding_field = sys.argv[2]
    decodedstring_field = sys.argv[3]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        encoding = result[encoding_field]
        if not encoding:
            encoding = 'utf-8'
        result[encoding_field] = encoding
        if result[hexstring_field]:
            try:
                result[decodedstring_field] = binascii.unhexlify(result[hexstring_field]).decode(encoding)
            except:
                pass
            w.writerow(result)

main()
