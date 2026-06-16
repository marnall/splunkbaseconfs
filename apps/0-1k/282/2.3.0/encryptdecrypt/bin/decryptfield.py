# Author: Nimish Doshi
# This file is only used for testing

#from __future__ import print_function
import sys
import string
import re
import base64
from pyDes import *
from io import open

if len(sys.argv) < 3:
    print ('Usage: python decryptfield.py filename escaped-regex key')
    sys.exit()

extension=".de.txt"

filename=sys.argv[1]
filenameout=filename + extension
regex=sys.argv[2]
key=sys.argv[3]

file = open(filename, "r")
fileout = open(filenameout, "w")

k = des(key, CBC, "\0\0\0\0\0\0\0\0", "\0", padmode=PAD_NORMAL)
m = re.compile(regex)
for line in file:
    mymatch = m.search(line)
    if mymatch:
        value = mymatch.group(1)
        data = base64.b64decode(value)
        printdata = k.decrypt(data)
        #newline = string.replace(line, value, printdata, 1)
        newline=line.replace(value, printdata.decode("utf-8"))
        fileout.write(newline)
    else:
        fileout.write(line)
file.close()
fileout.close()


    
