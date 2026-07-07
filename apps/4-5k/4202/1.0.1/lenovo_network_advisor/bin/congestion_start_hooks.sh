#!/bin/sh

#python -V                                 >> /home/splunk/test
#set                                       >> /home/splunk/test
#echo "PYTHONHOME        : $PYTHONHOME \n" >> /home/splunk/test
#echo "PYTHONPATH        : $PYTHONPATH \n" >> /home/splunk/test
#echo "LD_LIBRARY_PATH   : $LD_LIBRARY_PATH \n" >> /home/splunk/test

# We don't want splunk forwarder trigger scripts with splunk libarary as long as the script is not
# intent to using splunk python API, but the default libary of docker iamge itself.  As the docker
# image is easy to control.  if one day in the future, we are using python scripts to interact with
# splunk directly, please note splunk enterprise sever release with python, but it's hard to customise
# on top of that.
#
# options:
#       a. find out splunk python build package enviroment
#       b. create seperate python execution enviroment with pyevn or python virtual evn
#       c. Manually compile/insall the same version and then copy necessary packages/files to splunk python
#          untill it's possible to manapulating the packages (like with pip)
#
#
export LD_LIBRARY_PATH=


python  /opt/splunk/etc/apps/lenovo_network_advisor/bin/congestion_check.py
