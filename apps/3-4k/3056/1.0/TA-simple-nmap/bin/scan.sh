#/bin/bash


START=$(date +%s)

# Just add your hosts you want to monior here
wholist=(
  'localhost'
  '127.0.0.1'
  '192.168.1.1' 
  '172.16.1.1'
  )


# does stuff
for i in "${wholist[@]}"
do

/usr/bin/nmap $i | grep -v "Starting" | grep -v "Nmap scan" | grep -v "Host is up" | grep -v "Not shown" | grep -v "Other" | grep -v "Nmap done" | grep -v "PORT" | grep '\S' | grep -v "MAC Address" | grep -v "Note" | grep '[0-9].*'  > tmp.txt

  filename="tmp.txt"
  while read -r line
  do
  strDate=`date`
      name=$line
      echo "$i nmap $name" >> /var/log/nmap
  done < "$filename"

done

END=$(date +%s);
strwho=`whoami`

strVersion=`nmap --version | grep -i version | awk '{print $3}'` 


echo "severity=informational type=event app=nmap version=$strVersion user=$strwho status=stopped duration=$((END-START)) unit=seconds message=\"Scan completed\""

intnmap=`rpm -qa | grep -i nmap | wc -l`

if [ $intnmap == '0' ]
then
echo "app=nmap status=\"not installed\" "
fi


 
