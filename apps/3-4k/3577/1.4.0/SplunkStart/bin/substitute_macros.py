#!/usr/bin/python

# Author: Nimish Doshi

import sys

num=len(sys.argv)

if num!=3:
    print ('Usage: substitute_macros <name of macros file> <savesearches.conf>')
    exit()

macrofile=sys.argv[1]
savedsearchesfile=sys.argv[2]

fm = open(macrofile, 'r')
fs = open(savedsearchesfile, 'r')

target = open("local_savedsearches.conf", 'w')

# Build an array of macros to substitute
macro_list = []
for line in fm:
    if not line.strip() or line.startswith('#'):
        continue
    line = line.rstrip('\n')
    macro_list.append(line)


# for each line in savedsearches.conf, find the search to substitute
for line in fs:
    line = line.rstrip('\n')
    if line.startswith('search =') or line.startswith('search='):
        foundsearch=False
        for macro in macro_list:
            mac=macro.partition('(')[0]
            if mac in line:
                target.write('search = `' + macro + '`\n')
                foundsearch=True
                break
        if foundsearch==False:
            target.write(line + '\n')
    else:
        target.write(line + '\n')

fm.close()
fs.close()
target.close()




