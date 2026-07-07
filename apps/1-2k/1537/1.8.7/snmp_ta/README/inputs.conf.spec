[snmp://<name>]

* If you require an encrypted credential in your configuration , then you can enter it on the App's setup page.

* Then in your configration stanza refer to it in the format {encrypted:somekey}

* Where "somekey" is any value you choose to enter on the setup page

* EXAMPLES
* communitystring = {encrypted:somekey}


*You require an activation key to use this App. Visit http://www.baboonbones.com/#activation to obtain a non-expiring key
activation_key = <value>

*attributes | traps
snmp_mode = <value>

*IP or hostname of the device you would like to query, or a comma delimited list
destination= <value>

*Whether or not this is an IP version 6 address. Defaults to false.
ipv6= <value>

*The SNMP port. Defaults to 161
port= <value>

*The SNMP Version , 1 / 2C / 3 . Defaults to 2C
snmp_version= <value>

* 1 or more Objects Names , comma delimited , in either textual(iso.org.dod.internet.mgmt.mib-2.system.sysDescr.0) or numerical(1.3.6.1.2.1.1.3.0) format. By default a GET operation will be executed. If you require bulk operations , then select a SNMP Walking option.
object_names= <value>

*Perform a SNMPWALK using GETNEXT. Defaults to false.
do_get_subtree= <value>

*Perform a SNMPWALK using GETBULK. Defaults to false.
do_bulk_get= <value>

*Whether or not to split up bulk output into individual events
split_bulk_output= <value>

*For GETBULK operations , the number of objects that are only expected to return a single GETNEXT instance, not multiple instances.Defaults to 0. 
non_repeaters= <value>

*For GETBULK operations, the number of objects that should be returned for all the repeating OIDs.Defaults to 25.
max_repetitions= <value>

*Walk SNMP agent’s MIB till the end (if True), otherwise (if False) stop iteration when all response MIB variables leave the scope of initial MIB variables in varBinds. Default is False.
lexicographic_mode= <value>

*Community String used for SNMP version 1 and 2C authentication.Defaults to "public"
communitystring= <value>

*The following "v3_" parameters allow you to setup a single SNMPv3 USM User for polling attributes or receiving traps
*For receiving traps , v3_securityName and v3_securityEngineId must match what is configured in the Trap sending device
*If you need to setup multiple USM Users for receiving traps on the same port , then you can do so in the snmpv3_usm_users.conf file

*SNMPv3 USM username
v3_securityName= <value>

*SNMPv3 Engine ID , only needed for receiving traps , must match the sending device's engineID.
v3_securityEngineId= <value>

*SNMPv3 secret authorization key used within USM for SNMP PDU authorization. Setting it to a non-empty value implies MD5-based PDU authentication (defaults to usmHMACMD5AuthProtocol) to take effect. Default hashing method may be changed by means of further authProtocol parameter
v3_authKey= <value>

*SNMPv3 secret encryption key used within USM for SNMP PDU encryption. Setting it to a non-empty value implies MD5-based PDU authentication (defaults to usmHMACMD5AuthProtocol) and DES-based encryption (defaults to usmDESPrivProtocol) to take effect. Default hashing and/or encryption methods may be changed by means of further authProtocol and/or privProtocol parameters. 
v3_privKey= <value>

*may be used to specify non-default hash function algorithm. Possible values include usmHMACMD5AuthProtocol (default) / usmHMACSHAAuthProtocol / usmNoAuthProtocol / usmHMAC128SHA224AuthProtocol / usmHMAC192SHA256AuthProtocol / usmHMAC256SHA384AuthProtocol / usmHMAC384SHA512AuthProtocol
v3_authProtocol= <value> 

*may be used to specify non-default ciphering algorithm. Possible values include usmDESPrivProtocol (default) / usmAesCfb128Protocol / usm3DESEDEPrivProtocol / usmAesCfb192Protocol / usmAesCfb256Protocol / usmNoPrivProtocol
v3_privProtocol= <value>

*How often to run the SNMP query (in seconds). Defaults to 60 seconds
snmpinterval= <value>

*SNMP attribute polling timeout (in seconds). Defaults to 1 second. NOTE: timer resolution is about 0.5 seconds
timeout= <value>

*Number of times to automatically retry polling before giving up. Defaults to 5
retries= <value>

*Whether or not to listen for TRAP messages. Defaults to false
listen_traps= <value>

*The TRAP port to listen on. Defaults to 162
trap_port= <value>

*The trap host. Defaults to localhost. Ensure that you set this to the Hostname or IP  that the trap client is sending to.
trap_host= <value>

*Whether or not to perform reverse DNS on Trap Sending Host IP. Defaults to false 
trap_rdns = <value>

*Comma delimited list of MIB names to be applied ie: IF-MIB,DNS-SERVER-MIB,BRIDGE-MIB
*Any custom MIB text files can be dumped in the SPLUNK_HOME/etc/apps/snmp_ta/bin/mibs/user_plaintext_mibs directory
mib_names = <value>

*Python classname of custom response handler
response_handler= <value>

*Response Handler arguments string ,  key=value,key2=value2
response_handler_args= <value>

* Modular Input script python logging level for messages written to $SPLUNK_HOME/var/log/splunk/snmpmodinput_app_modularinput.log , defaults to 'INFO'
log_level= <value>

* whether or not to use a System python runtime vs Splunk's built in python runtime. Defaults to false.
use_system_python= <value>

* defaults to /usr/bin/python
system_python_path= <value>

* Whether or not to autonomously manage the script's running state.Defaults to true
run_process_checker= <value>
