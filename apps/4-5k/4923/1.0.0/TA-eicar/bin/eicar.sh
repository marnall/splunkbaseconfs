#!/bin/bash
# When run selects a random critical Linux dirtectory and places the test file down
# Test file uses the epoch time as a signture to help you find it with your AV tools
# ver 1.0.0

# TODO(daniel): Verify directories exist 
# TODO(daniel): fail gracefully
# TODO(daniel): must be run as root logic

# Globals
  declare -r ipaddress=$(hostname -I)
  declare -r intNow=$(date +'%s')
  declare -r filename="EICAR.test.malware.$intNow"
  declare -r intNum=$(( RANDOM % 25 ))

# Which critical linux directory should we use? 
case $intNum in
  "1") 
  strDir="/bin";;

  "2") 
  strDir="/boot";;

  "3")
  strDir="/dev";;

  "4")
  strDir="/etc";;

  "5")
  strDir="/etc/init.d";;

  "6")
  strDir="/etc/profile.d";;

  "7")
  strDir="/etc/rc.d/init.d";;

  "8")
  strDir="/etc/skel";;

  "9")
  strDir="/etc/X11";;

  "10")
  strDir="/home";;

  "11") 
  strDir="/lib";;

  "12")
  strDir="/mnt";;

  "13") 
  strDir="/proc";;

  "14")
  strDir="/root";;

  "15") 
  strDir="/sbin";;

  "16") 
  strDir="/tmp";;

  "17") 
  strDir="/usr";;

  "18")
  strDir="/usr/bin";;
  
  "19")
  strDir="/usr/bin/X11";;

  "20")
  strDir="/usr/include";;

  "21")
  strDir="/usr/share";;

  "22")
  strDir="/usr/lib";;

  "23") 
  strDir="/usr/local/bin";;

  "24") 
  strDir="/usr/sbin";;

  "25")
  strDir="/var";;

  *)
  echo "nothing";;
esac

mypath="$strDir/$filename"

# Log what we did using the CHANGE Model
echo "$(date +'%B %d %Y %H:%M:%S') app=eicar signature=$intNow dest_ip=$ipaddress dest_file=$filename dest_dir=$strDir dest=$(hostname) object=file object_type=file user=$(whoami) vendor=eicar product=\"Malware Test App for Splunk\" vendor_message=\"This script created a malware test string that should make a change  on your filesystem that your antimalware solution believe there is an attack\""  

# Create the fake malware
echo  "X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*" > $mypath
