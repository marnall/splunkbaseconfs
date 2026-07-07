[opd-banners://<subnet>]
label = <string>
exclusions = <string>
ping = [true|false]

[opd-full://<subnet>]
label = <string>
exclusions = <string>
ping = [true|false|0|1]
proto = [tcp|udp|icmp|all]
log_closed_ports = [true|false|0|1]

[opd-quick://<subnet>]
label = <string>
exclusions = <string>
ping = [true|false|0|1]
proto = [tcp|udp|icmp|all]
ports = <string>
log_closed_ports = [true|false|0|1]

[opd-versions://<subnet>]
label = <string>
exclusions = <string>
ping = [true|false|0|1]
proto = [tcp|udp|icmp|all]
ports = <string>
