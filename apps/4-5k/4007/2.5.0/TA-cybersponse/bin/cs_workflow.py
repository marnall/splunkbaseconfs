from cs import CyberSponseWorkflow
from splunktalib.common import log
import sys
logger = log.Logs('TA-cybersponse').get_logger('cs_workflow')

if __name__ == '__main__':
    try:
        cswf = CyberSponseWorkflow(sys.argv, logger)
    except Exception as e:
        logger.error(e, exc_info=True)