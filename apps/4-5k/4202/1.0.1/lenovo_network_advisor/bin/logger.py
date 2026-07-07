import logging
from logging import DEBUG, INFO, WARNING, ERROR, CRITICAL
from cloghandler import ConcurrentRotatingFileHandler

class FieldLogHandler():
    """log wrapper class for log """
    def __init__(self, logfile, log_size_limit=10, log_rotate_num=10, log_level=INFO, domain="NONE"):
        self.logger = logging.getLogger()
	logging.getLogger("requests").setLevel(logging.WARNING)
        try:
            self.rotateHandler = ConcurrentRotatingFileHandler(logfile, "a", log_size_limit*1024*1024, log_rotate_num)
        except Exception, e:
            print 'INTERNAL_ERR'
        formatter = logging.Formatter('%(asctime)-25s %(funcName)-25s %(levelname)-6s %(message)s')
        self.rotateHandler.setFormatter(formatter)

        if log_level == "DEBUG":
            self.logger.setLevel(DEBUG)
        elif log_level =="INFO":
            self.logger.setLevel(INFO)
        elif log_level =="WARNING":
            self.logger.setLevel(WARNING)
        elif log_level =="ERROR":
            self.logger.setLevel(ERROR)
        elif log_level =="CRITICAL":
            self.logger.setLevel(CRITICAL)
        else:
            self.logger.setLevel(INFO)

	self.api_version = "1.0.1"

	self.domain = domain

	self.counter = 0

    def splunk_log(self, switch_ip, sub_type, field_list):
	splunk_msg = "COMPANY=LENOVO, MSG_VERSION=%s" % (self.api_version)
	
	if len(field_list):	
	    for field_dict in field_list:
		if field_dict.has_key("name") and field_dict.has_key("value"):
	            splunk_msg = splunk_msg + ", %s=\"%s\"" % (field_dict['name'], field_dict['value'])

       	    self.logger.addHandler(self.rotateHandler)
	    #self.logger.info("counter = %d SWITCH_IP=%s, DOMAIN=%s, SUB_TYPE=%s, %s" % (self.counter, switch_ip, self.domain, sub_type, splunk_msg))
	    self.logger.info("SWITCH_IP=%s, DOMAIN=%s, SUB_TYPE=%s, %s" % (switch_ip, self.domain, sub_type, splunk_msg))
	    #self.counter = self.counter + 1
	    self.logger.removeHandler(self.rotateHandler)

	else:
	    return	
