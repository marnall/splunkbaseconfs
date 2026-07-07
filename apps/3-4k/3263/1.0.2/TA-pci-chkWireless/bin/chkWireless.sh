#!/bin/bash
# Daniel Wilson 
# Checks if wireless is loaded and echos the results
# Check the path on lspci if you're having trouble. 
# Make sure lspci is installed too. 

isWireless=`lspci | grep wireless | wc -l`
strHost=`hostname`
strWhoami=`whoami`

if [ $isWireless == 0 ]
then
  echo "action=blocked os=Linux command=lspci user=$strWhoami"
else
  echo "action=allowed os=Linux command=lspci user=$strWhoami"
fi

