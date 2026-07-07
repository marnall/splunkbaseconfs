[<connection_name>]
fw_version = OPSEC LEA version which can be R76, R77 and R80
lea_app_name = Application name created on OPSEC LEA Smart Dashboard
lea_object_name = Object name which is part of opsec_entity_sic_name and opsec_sic_name field when the lea_server_type is secondary or dedicated
lea_server_auth_port = OPSEC LEA server port and default value is 18184
lea_server_auth_type = Authentication method used by loggrabber. sslca and sslca_clear are the supported methods
lea_server_ip = OPSEC LEA server ip
lea_server_type = OPSEC LEA server type, supported values are primary, secondary and dedicated
opsec_entity_sic_name = Entity SIC name
opsec_sic_name = SIC Name from the SmartDashboard OPSEC Application Properties dialog DN window
cert_name = the name of the certificate file pulled by pull-cert.sh, which should locate under $SPLUNK_HOME/etc/apps/$OPSEC_APP/cert
certificate = <Reused connection name>
management_server_ip = <OPSEC Management Server IP address>
lea_action_map = The dictioanary map the action to action_id. (Optional)
