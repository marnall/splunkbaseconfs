[asset_data://<name>]
global_account = 
host_name = Hostname or IP of the Dragos Platform.
port_number = Port number that the Dragos Platform is listening on for HTTP connections. Typically 443 but may vary based on your environment.
certificate_file_name = Certificate chain file in the "./local/data" directory of the Add-On to verify the server identity. File name must be alphanumeric, '_'', and '-' with a '.pem extension.
use_global_proxy = Use global proxy in "Configuration -> Proxy" for this input. The global proxy must be enabled for this setting to work.

[notifications://<name>]
global_account = 
host_name = Hostname or IP of the Dragos Platform.
port_number = Port number that the Dragos Platform is listening on for HTTP connections. Typically 443 but may vary based on your environment.
timestamp_bookmark = Leave empty to retrieve all events. If you you would like to only retrieve events after a specific date, then please specify the date in ISO 8601 format. For example 1970-01-01T00:00:00Z
certificate_file_name = Certificate chain file in the "./local/data" directory of the Add-On to verify the server identity. File name must be alphanumeric, '_'', and '-' with a '.pem extension.
use_global_proxy = Use global proxy in "Configuration -> Proxy" for this input. The global proxy must be enabled for this setting to work.

[asset_zones://<name>]
global_account = 
host_name = Hostname or IP address of the Dragos Platform.
port_number = Port number that the Dragos Platform is listening on for HTTP connections. Typically 443 but may vary based on your environment.
certificate_file_name = Certificate chain file in the "./local/data" directory of the Add-On to verify the server identity. File name must be alphanumeric, '_'', and '-' with a '.pem extension.
use_global_proxy = Use global proxy in "Configuration -> Proxy" for this input. The global proxy must be enabled for this setting to work.

[vulnerabilities://<name>]
global_account = 
host_name = Hostname or IP the Dragos Platform.
port_number = Port number that the Dragos Platform is listening on for HTTP connections. Typically 443 but may vary based on your environment.
certificate_file_name = Certificate chain file in the "./local/data" directory of the Add-On to verify the server identity. File name must be alphanumeric, '_'', and '-' with a '.pem extension.
use_global_proxy = Use global proxy in "Configuration -> Proxy" for this input. The global proxy must be enabled for this setting to work.

[addresses://<name>]
global_account = 
host_name = Hostname or IP of the Dragos Platform.
port_number = Port number that the Dragos Platform is listening on for HTTP connections. Typically 443 but may vary based on your environment.
certificate_file_name = Certificate chain file in the "./local/data" directory of the Add-On to verify the server identity. File name must be alphanumeric, '_'', and '-' with a '.pem extension.
use_global_proxy = Use global proxy in "Configuration -> Proxy" for this input. The global proxy must be enabled for this setting to work.

[iocs://<name>]
global_account = 
full_replacement_interval = Optional. In order to make sure your local copy of the Dragos IOCs stays consistent and up to date the input will can perform a full replacement of all IOCs. Please specify this interval in days.
certificate_file_name = Certificate chain file in the "./local/data" directory of the Add-On to verify the server identity. File name must be alphanumeric, '_'', and '-' with a '.pem extension.
use_global_proxy = Use global proxy in "Configuration -> Proxy" for this input. The global proxy must be enabled for this setting to work.