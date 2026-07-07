import sys
import ConfigParser
import socket
from connect import *
from sysInfo import *
from logger import *
from splunklog import *
from traffic_utlization import *

if __name__ == '__main__':
    params = dict()

    config = ConfigParser.SafeConfigParser(allow_no_value = True)
    config.read('/opt/splunk/etc/apps/lenovo_network_advisor/local/lenovo_inspector.conf')
    hostname = socket.gethostname()

    section_name = None
    for section in config.sections() :
	if 'forwarder' in config.options(section):
	    if config.get(section, 'forwarder') == hostname:
		section_name = section
		break;
    if section_name is None:
	sys.exit(0)

    if config.get(section_name, 'Traffic') != 'Enable':
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

    logfile = defconfig.get('switch_properties', 'Traffic_Log_File')
    interval = defconfig.get('switch_properties', 'Traffic_Interval')


    logger =  FieldLogHandler(logfile, 4, 5, INFO, 'TRAFFIC_UTILIZATION')
    conn = Connection(params)
    rpt = get_device_iface_traffic_instance(conn, None)
    if (rpt):
	splunk_device_iface_traffic_utilization(conn.ip, rpt, logger)

