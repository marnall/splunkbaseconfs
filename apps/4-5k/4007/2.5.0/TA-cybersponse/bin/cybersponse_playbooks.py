from splunk.persistconn.application import PersistentServerConnectionApplication
import sys
import os

lib_path = os.path.dirname(os.path.abspath(__file__))
if lib_path not in sys.path:
    sys.path.append(lib_path)
from splunktalib.common import log
logger = log.Logs('TA-cybersponse').get_logger('cybersponse_playbooks')

from cs import CyberSponse

if sys.platform == "win32":
    import msvcrt
    # Binary mode is required for persistent mode on Windows.
    msvcrt.setmode(sys.stdin.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stdout.fileno(), os.O_BINARY)
    msvcrt.setmode(sys.stderr.fileno(), os.O_BINARY)


class PlaybooksHandler(PersistentServerConnectionApplication):
    def __init__(self, *args):
        logger.info('init')
        PersistentServerConnectionApplication.__init__(self)

    def handle(self, arg):
        logger.info('handle')
        try:
            return {'payload': CyberSponse(arg, logger, isARaction=True).fetchPlaybooks(), 'status': 200}
        except Exception as e:
            logger.exception('exception')
            return {
                'payload': str(e),
                'status': 400,
            }
