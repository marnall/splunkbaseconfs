import sys
import time
import ConfigParser
import socket
from connect import *
from logger import *
from splunklog import *
from sysInfo import *

if __name__ == '__main__':
    params = dict()

    config = ConfigParser.SafeConfigParser(allow_no_value = True)
    config.read('/opt/splunk/etc/apps/lenovo_network_advisor/local/lenovo_inspector.conf')
    hostname = socket.gethostname()
    
    section_name = None
    for section in config.sections() :
	# Not case senstive in config.options, but we did.
	if 'forwarder' in config.options(section):
	    if config.get(section, 'forwarder') == hostname:
		section_name = section
		break;
    if section_name is None:
	sys.exit(0)

    if config.get(section_name, 'Health') != 'Enable':
	sys.exit(0)

    # fixed port 
    params['port'] = '8090'
    params['transport'] = config.get(section_name, 'SwitchProtocol')
    params['ip'] = config.get(section_name, 'SwitchIP')
    if (params['transport'] == 'HTTPS'):
        params['port'] = '443'
    params['user'] = config.get(section_name, 'SwitchUser')
    params['password'] = config.get(section_name, 'SwitchPassword')

    if params['ip'] is None or params['ip'] == 'INVALID':
	sys.exit(0)

    if params['transport'] is None or params['transport'] == 'INVALID':
	sys.exit(0)

    if params['user'] is None or params['user'] == 'INVALID':
	sys.exit(0)

    if params['password'] is None or params['password'] == 'INVALID':
	sys.exit(0)


    defconfig = ConfigParser.SafeConfigParser(allow_no_value = True)
    defconfig.read('/opt/splunk/etc/apps/lenovo_network_advisor/default/lenovo_inspector.conf')
    logfile = defconfig.get('switch_properties', 'Health_Log_File')

    logger =  FieldLogHandler(logfile, 4, 5, INFO, 'SYSTEM_HEALTH')
    conn = Connection(params)
    sys = SystemInfo()

    rpt = sys.get_hostname(conn)
    if (rpt):
	splunk_health_hostname_log(conn.ip, rpt, logger)
    time.sleep(2)

    rpt = sys.get_env_power(conn)
    if (rpt):
	splunk_health_power_log(conn.ip, rpt, logger)
    time.sleep(2)

    rpt = sys.get_env_fans(conn)
    if (rpt):
	splunk_health_fans_log(conn.ip, rpt, logger)
    time.sleep(2)

    rpt = sys.get_env_temperature(conn)
    if (rpt):
	splunk_health_temperature_log(conn.ip, rpt, logger)
    time.sleep(2)
	
    rpt = sys.get_env_resources(conn)
    if (rpt):
	splunk_health_resources_log(conn.ip, rpt, logger)


