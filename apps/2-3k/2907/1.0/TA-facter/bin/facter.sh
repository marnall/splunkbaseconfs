#/bin/bash
# Daniel Wilson daniel.p.wilson@live.com


# It will go through and CIM your values using sed. 
# Please keep in mind, not all facts will be in the same in every facter install
# I provided examples for you
cim="no" # set to yes OR no OR both 

# Run facter and get results into a file
strResults=`facter`   #change this if your factor path need setting
echo "$strResults" > temp.out

# null my var out
strResults=""

#Read in the file line by line and build the strResults back up 
while IFS='' read -r line || [[ -n "$line" ]]; do
  line=`sed 's/ => /="/g' <<< $line`
  line=$line"\""
  strResults=$line" "$strResults
done < "temp.out"


if [ "$cim" = "no" ] || [ "$cim" = "both"  ] ; then
  echo "`date` $strResults" >> /var/log/facter.log
fi

# Want to CIM your logs? Do it here! 
if [ "$cim" != "no" ]; then
  # Make your CIM adjustment here
  # In my facter install we call uptime, uptime_seconds
  # However CIM is simply uptime
  # So I sed leaving the "=" to ensure you are not pulling out something else
  strResults=`sed 's/uptime_seconds=/uptime=/g' <<< $strResults`
  strResults=`sed 's/memory_free=/mem_free=/g' <<< $strResults`

  echo "`date` $strResults" >> /var/log/facter.log
fi

# Cleanup
rm temp.out





