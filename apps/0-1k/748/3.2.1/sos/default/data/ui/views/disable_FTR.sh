#!/bin/bash

# move all .xml.bak files to .xml
for i in `ls -1 *.xml.bak`
do
	mv $i `echo $i | sed 's/\.xml\.bak/\.xml/'`
done
