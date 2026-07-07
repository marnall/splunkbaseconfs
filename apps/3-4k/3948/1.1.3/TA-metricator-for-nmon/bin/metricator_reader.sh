#!/bin/sh

# set -x

# Program name: metricator_reader.sh
# Compatibility: Shell
# Purpose - read nmon data from fifo file and output to stdout
# Author - Guilhem Marchand

# Version 2.0.0

# For AIX / Linux / Solaris

#################################################
## 	Your Customizations Go Here            ##
#################################################

# fifo to be read (valid choices are: fifo1 | fifo2
FIFO=$1

####################################################################
#############		Main Program 			############
####################################################################

while IFS= read line
do
    echo $line
done <$FIFO

exit 0
