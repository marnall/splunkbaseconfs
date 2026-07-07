==FMS==

fm1.gigamon.com

fmDemoMode: false
vmDemoMode: false
licensedVms: 10
MAC: 00:00:00:AF:FE:ED
FM IP: 172.168.10.10

Cluster #1

Cluster ID/IP: 192.168.20.10
 Ports: 5/2/x1-x16
 	5/3/g1-g24
	5/4/x1-x16

 Cards:
	1AT0-01FB192.168.20.10,192.168.20.10,fm1.gigamon.com,A0-5,SMT-HC0/R,card,132-00AT,port,5
	1500-1001,192.168.20.10,192.168.20.10,fm1.gigamon.com,1.0,TA10-48X4Q,card,132-00CC,port,1
	

fm2.gigamon.com
fmDemoMode: true
vmDemoMode: true
licensedVMs: 100
MAC: 00:30:39:94:03:AF
FM IP:172.168.10.15

Cluster #1
Cluster ID/IP: 192.168.20.15
 Ports: 17/1/x1-x24
	17/4/x1-x16
 Cards:
	serialNumber,clusterId,deviceIp,host,hwRevision,hwType,interfaceType,productCode,service,slotId
	1AF0-0911,192.168.20.15,192.168.20.15,fm2.gigamon.com,E0-0,HB1-X04G16,card,132-00AF,port,1
	1AT0-0029,192.168.20.15,192.168.20.15,fm2.gigamon.com,3.0-5,HC2-GigaSMART,card,132-00AT,port,5

fm3.gigamon.com
fmDemoMode: false
vmDemoMode: true
licensedVMs: 10,00:00:00:39:49:2A
FM IP: 172.168.10.20

Cluster #1
Cluster ID/IP: 192.168.20.20
 Ports: 10/1/g1-g16
	10/1/x1-x4

 Cards:
	1AN0-0067,192.168.20.20,192.168.20.20,fm3.gigamon.com,3.2-25,HC2-Main-Board,card,132-00AN,port,cc1
	1BD0-0035,192.168.20.20,192.168.20.20,fm3.gigamon.com,2.2-a2,HC2-X24,card,132-00BD,port,1


fm4.gigamon.com
fmDemoMode: true
vmDemoMode: false
licensedVms: 30
MAC: 00:00:00:FA:DE:DC
FM IP: 172.168.10.25

Cluster #1
Cluster ID/IP: 192.168.20.25
 Ports: 1/1/g1-g16
	1/1/x1-x4
	2/1/x1-x32
	2/3/x1-x32
	3/1/g1-g16
	3/1/x1-x4

 Cards:
	1870-0118,192.168.20.25,192.168.20.25,fm4.gigamon.com,B2-a2,GigaPORT-Q02X32,card,132-0087,port,1
	1870-0175,192.168.20.25,192.168.20.25,fm4.gigamon.com,1.0-0,GigaPORT-Q02X32/32x,card.132-0087,port,2
	1870-0122,192.168.20.25,192.168.20.25,fm4.gigamon.com,B1-a0,GigaPORT-Q02x32,card,132-0087,port,3
