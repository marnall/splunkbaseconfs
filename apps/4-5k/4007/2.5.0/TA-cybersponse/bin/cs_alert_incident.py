from cs import CyberSponseAlertActionIncident
from splunktalib.common import log
import sys
logger = log.Logs('TA-cybersponse').get_logger('cs_alert_incident')

if __name__ == '__main__':
    
    try:
        csaa = CyberSponseAlertActionIncident(sys.argv, logger)
    except Exception as e:
        logger.error(e, exc_info=True)