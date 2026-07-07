# 11/5/2019: Updated print to print()

import csv
import sys
from humanize import intword

def main():
    if len(sys.argv) != 3:
        print("Usage: python int2word.py [int] [word]")
        sys.exit(1)

    input_field = sys.argv[1]
    output_field = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        try:
            result[output_field] = intword(int(result[input_field]))
        except Exception:
            continue
        w.writerow(result)

if __name__ == '__main__':
    main()
