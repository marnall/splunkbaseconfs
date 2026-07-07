[azure_security_center://<name>]
tenant_id = 
subscription_id = 
collect_security_center_alerts = 
security_alert_sourcetype = 
collect_security_center_tasks = 
security_task_sourcetype = 

[azure_resource_groups://<name>]
tenant_id = 
subscription_id = 

[azure_subscriptions://<name>]
tenant_id = This parameter is used for authentication.
subscription_sourcetype = 

[azure_virtual_networks://<name>]
tenant_id = 
subscription_id = 
collect_virtual_networks_data = 
virtual_network_sourcetype = 
collect_network_interface_data = 
network_interface_sourcetype = 
collect_security_group_data = 
security_group_sourcetype = 
collect_public_ip_address_data = 
public_ip_sourcetype = 

[azure_compute://<name>]
tenant_id = 
subscription_id = 
collect_managed_disk_data = 
managed_disk_sourcetype = 
collect_image_data = 
image_sourcetype = 
collect_snapshot_data = 
snapshot_sourcetype = 
collect_virtual_machine_data = 
virtual_machine_sourcetype = 

[azure_topology_manual://<name>]
subscription_id = 
tenant_id = 
network_watcher_name = Network Watchers provide access to topology data.
network_watcher_resource_group = Specify the Resource Group containing the Network Watcher.
target_resource_group = Specify the Resource Group to enumerate topology. This Resource Group should be in the same region as the Network Watcher.

[azure_topology_auto://<name>]
subscription_id = 
tenant_id =