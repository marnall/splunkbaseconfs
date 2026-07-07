
[udp://514]
connection_host = ip
sourcetype = DriveLock
source = DriveLock (UDP)
disabled = 1

[tcp://514]
connection_host = ip
sourcetype = syslog
source = DriveLock (TCP)
disabled = 1

[tcp-ssl://6514]
connection_host = ip
sourcetype = DriveLock
source = DriveLock (TCP-SSL)
disabled = 1

[SSL]
serverCert = <path to certificate>
requireClientCert = 1
