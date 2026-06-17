#!/bin/bash

# move all .xml files to .xml.bak
for i in `ls -1 *.xml`
do
	mv $i `echo $i | sed 's/\.xml/\.xml\.bak/'`
done

# move home.xml.ftr to home.xml
cp home.xml.FTR home.xml
