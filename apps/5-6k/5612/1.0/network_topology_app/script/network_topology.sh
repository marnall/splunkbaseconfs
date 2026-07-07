#!/bin/bash 
community="public" 		# SNMP community
workingdir="/opt/topology" # script`s directory
date=`date +"%Y_%m_%d"` 
LOG=$workingdir/log/network_topology_$date.csv # path for storing script results
infile=$workingdir/hostip.txt # file with a list of IP to be scanned by the script
#
echo Host,HostName,Version,Product_Name,Product_Name2,Serial_Num,Serial_Num2,cdp_hostname,cdp_port,cdp_ios,cdp_product_name >> $LOG
snmp="snmpwalk -Oqv -v 2c -c $community"
snmp2="snmpwalk -v 2c -c $community"
#
while read device
do
	$snmp $device sysName.0 #> /dev/null
	if [ "$?" = "0" ] ; then
		echo "************** $n ************************"
		intf=$($snmp2 $device .1.3.6.1.4.1.9.9.23.1.2.1.1.6 | cut -c 42- | cut -f1 -d\=  | wc -l)
		echo "no of interface= $intf "
		IPacketperDev=0
		OPacketperDev=0
		for i in $($snmp2 $device 1.3.6.1.4.1.9.9.23.1.2.1.1.6 | cut -c 42- | cut -f1 -d\= )
		do
			host=$device
			devname=`$snmp $device   1.3.6.1.2.1.1.5 | cut -f2 -d\" `
			ios=`$snmp $device   .1.3.6.1.4.1.9.9.25.1.1.1.2.5 | cut -f2 -d$ | grep -v "No Such Instance currently exists at this OID" | grep -v "No Such Object available on this agent at this OID" `
			model=`$snmp $device   .1.3.6.1.2.1.47.1.1.1.1.13.1 | cut -f2 -d\" | grep -v "StackPort1/1" | grep -v "No Such Instance currently exists at this OID" | grep -v "No Such Object available on this agent at this OID" `
			model2=`$snmp $device  mib-2.47.1.1.1.1.2.1001 | cut -f2 -d\" | grep -v "StackPort1/1" | grep -v "No Such Instance currently exists at this OID" | grep -v "No Such Object available on this agent at this OID" | grep -v "Network Interface Module Subslot" | grep -v "Chassis 1 Cisco Systems" | grep -v "CPU of Module" | grep -v "CPU of Switching Processor 5" | grep -v "PSOC-MB_0: VOU" | grep -v "Power Supply A Container" `
			serial1=`$snmp $device   .1.3.6.1.2.1.47.1.1.1.1.11.1 | cut -f2 -d\" | grep -v "No Such Instance currently exists at this OID" | grep -v "No Such Object available on this agent at this OID" | grep -v "slot Physical Slot" `
			serial2=`$snmp $device   .1.3.6.1.4.1.9.5.1.2.19 | cut -f2 -d\" | grep -v "No Such Instance currently exists at this OID" | grep -v "No Such Object available on this agent at this OID" | grep -v "Network Interface Module Subslot" | grep -v "Power Supply A Container" | grep -v "CPU of Switching Processor" | grep -v "CPU of Module" `
			cdpname=`$snmp2 $device .1.3.6.1.4.1.9.9.23.1.2.1.1.6.$i | cut -f2 -d\" `
			cdpport=`$snmp2 $device .1.3.6.1.4.1.9.9.23.1.2.1.1.7.$i | cut -f2 -d\" `
			cdpios=`$snmp $device .1.3.6.1.4.1.9.9.23.1.2.1.1.5.$i | cut -f3 -d\, | grep -v "Cisco Systems, Inc" | grep -v "prod_rel_team" | grep -v "www.cisco.com" ` 
			cdpmodel=`$snmp2 $device .1.3.6.1.4.1.9.9.23.1.2.1.1.8.$i | cut -f2 -d\" `
			echo  $host,$devname,Version $ios,$model,$model2,$serial1,$serial2,$cdpname,$cdpport,$cdpios,$cdpmodel | grep -v "Port 1" | grep -v "mgmt0" | grep -v "Abonentskiy" | grep -v " br_31" | grep -v "br0" | grep -v "br1" | grep -v "br2" | grep -v "br3" | grep -v "br5" | grep -v "bridge" | grep -v "eth0"  | grep -v "ETH1-WAN" >> $LOG  
		done
	fi
done < $infile
