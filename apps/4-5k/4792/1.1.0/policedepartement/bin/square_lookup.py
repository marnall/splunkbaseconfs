#!/usr/bin/env python

import csv
import sys
import socket

x_gridsize=13
y_gridsize=13
lat_high=42.02271
lat_low=41.64459
lon_high=-87.52453
lon_low=-87.93432

def main():
#    if len(sys.argv) != 3:
#        print "Usage: python external_lookup.py [location] [square]"
#        sys.exit(1)

    location = sys.argv[1]
    square = sys.argv[2]

    infile = sys.stdin
    outfile = sys.stdout

    r = csv.DictReader(infile)
    header = r.fieldnames

    w = csv.DictWriter(outfile, fieldnames=r.fieldnames)
    w.writeheader()

    for result in r:
        lat, lon = eval(result[location])
        if (lat < lat_low or lat > lat_high) or (lon < lon_low or lon > lon_high):
            result[square] = None
        else:
            y_grid_pos = int((lat - lat_low) / (lat_high - lat_low) * y_gridsize)
            x_grid_pos = int((lon - lon_low) / (lon_high - lon_low) * x_gridsize)

            square_num = y_grid_pos * x_gridsize + x_grid_pos

            result[square] = square_num

        w.writerow(result)

main()
