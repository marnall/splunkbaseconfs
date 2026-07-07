'''
Class for generating and rotating logs for Splunk app.
'''
import logging
import logging.handlers
import os

class SplunkLogger:
    def __init__(self, logname, max_bytes, backup_count):
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)
        handler = logging.handlers.RotatingFileHandler(
                    logname, maxBytes=int(max_bytes), backupCount=int(backup_count))
        self.logger.addHandler(handler)

    def info(self, msg):
        self.logger.info(msg)

def test():
    print 'SplunkLogger class testing:'
    APPNAME        = 'Splunk_TA_cisco-ips'
    TA_BIN_DIR     = os.path.join(os.environ['SPLUNK_HOME'], 'etc', 'apps', APPNAME, 'bin')
    TEST_OUTFILE   = os.path.join(TA_BIN_DIR, 'ips_test.log')
    logger         = SplunkLogger(TEST_OUTFILE, 1024, 5)
    print ''.join(['outputting to logfile => ',TEST_OUTFILE])
    for i in range(2000):
        logger.info('This is a test %d' % i)
    print 'Finished testing!'

if __name__ == '__main__':
    test()
