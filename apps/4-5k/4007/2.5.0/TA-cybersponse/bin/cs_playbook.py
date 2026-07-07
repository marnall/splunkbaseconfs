from cs import CyberSponseRunPlaybook
from splunktalib.common import log
import sys

logger = log.Logs('TA-cybersponse').get_logger('cs_playbook')

if __name__ == '__main__':
    try:
        csag = CyberSponseRunPlaybook(sys.argv, logger)
    except Exception as e:
        logger.error(e, exc_info=True)