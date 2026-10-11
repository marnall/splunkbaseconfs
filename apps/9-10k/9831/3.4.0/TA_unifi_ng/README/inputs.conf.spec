[unifi_ingest://<name>]
account = Select the controller account to poll.
collect_clients = Collect connected client list for each site.  Default: True
collect_devices = Collect device inventory for each site. Sites are always collected.  Default: True
collect_networks = Collect network configurations for each site.  Default: True
collection_timeout = Timeout for each API request in seconds. Default: 120.  Default: 120
index = Default: default
interval = How often to collect data from the controller, in seconds.  Default: 300
page_size = Number of objects per API page (1–200). Default: 200.  Default: 200
site_ids = Comma-separated site UUIDs to collect. Leave empty to collect all sites.

[unifi_inventory://<name>]
account = Select the controller account to poll.
interval = How often to poll configuration/inventory lists, in seconds.  Default: 180
index = Default: default
collect_devices = Collect adopted devices (sourcetype=unifi:device).  Default: True
collect_clients = Collect connected clients (sourcetype=unifi:client).  Default: True
collect_networks = Collect networks (sourcetype=unifi:network).  Default: True
collect_device_tags = Collect device tags (sourcetype=unifi:device_tag).  Default: True
collect_firewall = Collect firewall zones, policies, ACL rules (sourcetypes=unifi:firewall:zone, unifi:firewall:policy, unifi:acl_rule).  Default: True
collect_wifi = Collect WiFi broadcasts (sourcetype=unifi:wifi:broadcast).  Default: True
collect_wan = Collect WAN interfaces (sourcetype=unifi:wan).  Default: True
collect_pending_devices = Collect devices pending adoption (sourcetype=unifi:device:pending).  Default: True
collect_info = Collect controller application info (sourcetype=unifi:info).  Default: True
collect_vpn = Collect VPN servers and site-to-site tunnels (sourcetypes=unifi:vpn:server, unifi:vpn:tunnel).  Default: False
collect_switching = Collect LAGs, MC-LAG domains, switch stacks (sourcetypes=unifi:switching:lag, unifi:switching:mc_lag_domain, unifi:switching:switch_stack).  Default: False
collect_dns = Collect DNS policies (sourcetype=unifi:dns:policy).  Default: False
collect_traffic_lists = Collect traffic matching lists (sourcetype=unifi:traffic_matching_list).  Default: False
collect_radius = Collect RADIUS profiles (sourcetype=unifi:radius:profile).  Default: False
collect_vouchers = Collect hotspot vouchers (sourcetype=unifi:hotspot:voucher).  Default: False
collect_network_detail = Collect full per-network detail and references: ipv4/DHCP config, isolation, internet access (sourcetypes=unifi:network:detail, unifi:network:reference). 1-2 extra API calls per network.  Default: False
collection_timeout = Timeout for each API request in seconds. Default: 120.  Default: 120
page_size = Number of objects per API page (1–200). Default: 200.  Default: 200
site_ids = Comma-separated site UUIDs to collect. Leave empty to collect all sites.

[unifi_telemetry://<name>]
account = Select the controller account to poll.
interval = How often to poll per-device telemetry, in seconds. One API call per device per enabled collector. Default: 60
index = Default: default
collect_device_stats = Collect per-device performance statistics: CPU, memory, load, uptime, uplink rates (sourcetype=unifi:device:stats).  Default: True
collect_device_detail = Collect full per-device detail: ports, radios, uplink, provisionedAt (sourcetype=unifi:device:detail).  Default: True
collection_timeout = Timeout for each API request in seconds. Default: 120.  Default: 120
page_size = Number of objects per API page (1–200). Default: 200.  Default: 200
site_ids = Comma-separated site UUIDs to collect. Leave empty to collect all sites.

[unifi_reference://<name>]
account = Select the controller account to poll.
interval = How often to refresh static reference data, in seconds. Default: 86400 (daily).
index = Default: default
collect_countries = Collect country code reference list (sourcetype=unifi:ref:country).  Default: True
collect_dpi_applications = Collect DPI application reference list (sourcetype=unifi:ref:dpi_application).  Default: True
collect_dpi_categories = Collect DPI application category reference list (sourcetype=unifi:ref:dpi_category).  Default: True
collection_timeout = Timeout for each API request in seconds. Default: 120.  Default: 120
page_size = Number of objects per API page (1–200). Default: 200.  Default: 200
