import sys, os
import random
from datetime import datetime

PWD = os.path.dirname(os.path.join(os.getcwd(), __file__))
DATAFILENAME = 'tamr_sample.log'
DATAFILEPATH = os.path.join(PWD, DATAFILENAME)

def formatline(line):
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S-08:00') + ' ' + line.replace('\n', '')

with open(DATAFILEPATH) as f:
    loglines = f.readlines()

nlines = len(loglines)
k = 5

randlines = [line for line in loglines if random.random() < float(k) / nlines]

for line in randlines:
    print formatline(line)


