#!/bin/sh

of=/tmp/mm_$$.out

# List of ClearPass servers
svrs="changeme_servers_list"

for cphost in $svrs
do
wget  -q -O $of  --http-password=xxxxxx --http-user=apisplunk --no-check-certificate https://$cphost/tipsapi/config/fetch/Endpoint

# Converting xml output to syslog format
ddd=`date +"%d-%m-%Y %H:%M:%S"`
host=`hostname -i`
pri=100
hdr="$ddd,$pri $host CPPM_MDM_Attributes 1 0 1 "

cat $of | sed "s/<Endpoints>/\n<Endpoints>/g" | sed "s/<\/Endpoints>/\n<\/Endpoints>/g" |  sed "s/<TagDiction/\n<TagDiction/g" | sed "s/<Endpoint /\n<Endpoint /g" | sed -n '/Endpoints/,/Endpoints/p' |head -n -1 |tail -n +2 |  sed "s/<Endpoint //g" | sed 's/\/>$//g' | sed 's/<\/Endpoint>$//g' |  sed 's/><EndpointTags tagName=\"/ \"/g'| sed 's/\" tagValue=\"/\"=\"/g' |  sed 's/\/>$//g' | sed 's|/||g' |sed "s/^/${hdr}/" > ${of}_1

# Remove spaces and quotes from attribute names
cat ${of}_1 | sed "s/\"Encryption Enabled\"/Encryption_Enabled/g" | sed 's/\"Ownership\"=/Ownership=/g' | sed 's/\"Compromised\"=/Compromised=/g' | sed 's/\"IMEI\"=/IMEI=/g' | sed 's/\"Owner\"=/Owner=/g' | sed 's/\"MDM Enabled\"=/MDM_Enabled=/g' | sed 's/\"Manufacturer\"=/Manufacturer=/g' | sed 's/\"Model\"=/Model=/g' | sed 's/\"Source\"=/Source=/g' | sed 's/\"UDID\"=/UDID=/g' | sed 's/\"OS Version\"=/OS_Version=/g' | sed 's/\"Phone Number\"=/Phone_Number=/g' | sed 's/\"Display Name\"=/Display_Name=/g' | sed 's/\"MDM Identifier\"=/MDM_Identifier=/g' | sed 's/\"Last Check In\"=/Last_Check_In=/g' | sed 's/\"Blacklisted App\"=/Blacklisted_App=/g' | sed 's/\"Required App\"=/Required_App=/g' | sed 's/\"Carrier\"=/Carrier=/g' | sed 's/\"Serial Number\"=/Serial_Number=/g' | sed 's/\"Device Name\"=/Device_Name=/g' | sed 's/\"Device Full Name\"=/Device_Full_Name=/g' | sed 's/\"Description\"=/Description=/g' | sed 's/\"Device Folder\"=/Device_Folder=/g' | sed 's/\"Username\"=/Username=/g' | sed 's/\"Last_Known_Location\"=/Last_Known_Location=/g' | sed 's/\"Guest Role ID\"=/"Guest_Role_ID=/g' | sed 's/\"Device Type\"=/"Device_Type=/g' | sed 's/\"Product Name\"=/"Product_Name=/g' | sed 's/\"Product Version\"=/"Product_Version=/g' | sed 's/\"Device UDID\"=/"UDID=/g' | sed 's/\"Device IMEI\"=/"IMEI=/g' > ${of}_2 
  
cat ${of}_2

done
rm -f $of ${of}_1 ${of}_2
