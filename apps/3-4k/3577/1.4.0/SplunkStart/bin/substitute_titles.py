#!/usr/bin/python

import sys

from shutil import move
from os import remove, close


def replace(file_path, kv):
    lines=[]

    # First replace ttiles for each line and append to a temporary array
    with open(file_path) as old_file:
        for line in old_file:
            for key in kv:
                if key in line:
                    line = line.replace(key, kv[key])
                    break
            lines.append(line)

    # Next, for each line in the temporary array, write it back to the file
    with open(file_path, 'w') as new_file:
        for line in lines:
            new_file.write(line)
#            print(line, end='')


num = len(sys.argv)

if num != 3:
    print ('Usage: substitute_titles.py <name of titles csv file> <view.xml>')
    exit()

import csv

d = {}
with open(sys.argv[1], 'r') as csvfile:
    reader = csv.reader(csvfile, delimiter=',', quotechar='"')
    # Read the titles.csv file load into d. k is the key and d[k] is the value.
    for row in reader:
        if len(row) > 1:
            k, v = row
            k = row[0]
            if row[1]:
                v = row[1]
            else:
                v = None
            d[k] = v

# for key in d:
#    print key, d[key]

replace(sys.argv[2], d)
