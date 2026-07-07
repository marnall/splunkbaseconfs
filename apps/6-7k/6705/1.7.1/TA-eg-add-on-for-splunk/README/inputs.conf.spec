[showtestsdetails://<name>]
global_account = 
hostname_ip_address = eG manager IP: xxx.xxx.xxx.xxx
port = 
component_type = 
component_name = 
test_type = 
test_name = 

[showcomponents://<name>]
global_account = 
hostname_ip_address = eG manager FQDN/IP, xxx.xxx.xxx.xxx
port = 
component_type = 

[getalerts://<name>]
global_account = 
hostname_ip_address = eG manager FQDN / IP, xxx.xxx.xxx.xxx
port = 
type = <zone/segment/service/componentType>
name_ = <comma-separated list of zone/segment/service/componentType>

[input_1://<name>]
hostname_ip_address = 
port = 
username = 
password = Base64 encoded password
component_type = Technology monitored by eG, e.g. Oracle Database
component_name_and_test_port = Hostname of the server monitored by eG and its corresponding test port separated comma, e.g. <hostname1>:<testPort1>, <hostname2>:<testPort2>
category = 
test_type = 
checkpoint_initial_value = checkpoint for metric / test data, %Y-%m-%d %H:%M:%S

[input_3://<name>]
global_account = 
hostname_ip_address = 
port = 
component_type = 
component_name_and_test_port = 
category = 
test_type = 
checkpoint_initial_value = 

[showtests://<name>]
global_account = 
hostname_ip_address = eG manager FQDN / IP, xxx.xxx.xxx.xxx
port = 
component_type = 
category = 
test_type = 

[input_2://<name>]
hostname_ip_address = eG manager
port = eG manager REST API port
username = eG manager username
password = Base64 encoded password
component_name_list = Host / Component Name with its Test Port, Comma separated, e.g. host1:port1, host3:port3, host4:port4
test_name_list = Comma separated, e.g. Memory Usage, System Details
checkpoint_initial_value = %Y-%m-%d %H:%M:%S

[gettestdata://<name>]
global_account = 
hostname_ip_address = eG manager FQDN / IP, xxx.xxx.xxx.xxx
port = 
test_name = e.g. Memory Usage, System Details etc.
component_name = 
checkpoint_initial_value = %Y-%m-%d %H:%M:%S

[getlivemeasure://<name>]
global_account = 
hostname_ip_address = 
port = 
server_type = 
server_name = 

[getcomponentmapping://<name>]
global_account = 
hostname_ip_address = 
port = 

[getalllivedata://<name>]
global_account = 
hostname_ip_address = 
port = 
zone = 

[getzonemapping://<name>]
global_account = 
hostname_ip_address = 
port = 

[getzonedetails://<name>]
global_account = 
hostname_ip_address = 
port = 
zone = 

[getalllivedata_v2://<name>]
global_account = 
hostname_ip_address = 
port = 

[getzonelivemeasure://<name>]
global_account = 
hostname_ip_address = 
port = 
zone =