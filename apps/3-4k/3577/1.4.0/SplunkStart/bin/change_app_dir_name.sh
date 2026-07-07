#!/bin/sh

# If you make a copy of the SplunkStart Directory and put it in
# $SPLUNK_HOME/etc/apps, you"ll need to run this script to change the
# hard coded SplunkStart name to the name of your new directory for SplunkStart

# Example usage:
# ./change_app_dir_name.sh SplunkStart1



if [ $# -ne 1 ]
then
    echo "usage: $0 new_directory_name"
    exit
fi

# Syntax for SED is different for MacOS
if [ `uname` == "Darwin" ]
    then
    
    LC_CTYPE=C && LANG=C && find ./controller_services -type f -exec sed -i '' "s/SplunkStart/$1/g"  {} \;
    LC_CTYPE=C && LANG=C && find ../default -type f -exec sed -i '' "s/SplunkStart/$1/g"  {} \;
    LC_CTYPE=C && LANG=C && find ../appserver -type f -exec sed -i '' "s/SplunkStart/$1/g"  {} \;
else
    LC_CTYPE=C && LANG=C && find ./controller_services -type f -exec sed -i "s/SplunkStart/$1/g"  {} \;
    LC_CTYPE=C && LANG=C && find ../default -type f -exec sed -i "s/SplunkStart/$1/g"  {} \;
    LC_CTYPE=C && LANG=C && find ../appserver -type f -exec sed -i "s/SplunkStart/$1/g"  {} \;
fi

