'''
This script triggers the Event Analytics Rules Engine Java process, collects parameters from inputs.conf,
detects the environment and provides all the arguments to itsirulesengine script.

'''
import sys
import subprocess
from builtins import str
from builtins import range
import splunk.rest as rest
import xml.dom.minidom
import json
import time
import logging
import os
from semantic_version import Version as SemVersion
from future.moves.urllib.parse import quote_plus
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
import itsi_path
from ITOA.itoa_common import modular_input_should_run, is_feature_enabled, is_shc_member, is_shcluster_restarting, \
    is_noah_enabled
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager

# initialize logging
sys.path.insert(0, make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))
from solnlib import log
log.Logs.set_context(log_format='%(asctime)s %(levelname)s %(message)s')
logger = log.Logs().get_logger('itsi_queue_re_init')
logger.setLevel(logging.INFO)
SPLUNK_HOME = os.environ.get("SPLUNK_HOME")


def get_args(conf):
    arguments = []
    cwd = os.path.abspath(SPLUNK_HOME + '/etc/apps/SA-ITOA/bin')
    command = os.path.abspath(SPLUNK_HOME + '/etc/apps/SA-ITOA/bin/itsirulesengine')
    bash_command = []

    for key, value in conf.items():
        if key.startswith('command.arg.'):
            arguments.append(value)

    if os.name == 'nt':
        command = command + '.bat'
        for args in arguments:
            params = args.split('=')
            if (len(params) == 2):
                params[1] = os.path.abspath(params[1])
                args = params[0] + '=' + params[1]

    bash_command.append(command)
    bash_command = bash_command + arguments
    return bash_command, cwd


def is_shcluster_status_check_enabled(conf):
    shcluster_status_check_enabled = conf.get('shcluster_status_check', '1') == '1'
    if not shcluster_status_check_enabled:
        logger.info('SHCluster status check is disabled.')
    return shcluster_status_check_enabled


def is_valid_jvm(session_token):
    """
    Validates if Java version 1.8 and above is installed and running.
    @type session_token: string
    @param session_token: Session token.

    @returns True if installed Java is 1.8 or above or else False.
    """
    try:
        response, content = rest.simpleRequest(path='/servicesNS/nobody/SA-ITOA/metric_ad/jvm', method='GET',
                                               sessionKey=session_token)
        if response.status != 200:
            logger.error('Failed to retrieve Java metrics information: %s', content)
            return False

        content = json.loads(content)

        if content.get('active') and content.get('activeRunnable'):
            path = content.get('availableJVMs', {}).get('PATH', {})
            status = path.get('status', {})
            supported = status.get('supported', False)
            runnable = status.get('runnable', False)

            try:
                java_version_str = path.get('version', '1.0')
                java_version = SemVersion(java_version_str, partial=True)
                min_java_version = SemVersion("1.8", partial=True)
            except Exception as e:
                logger.error('Error parsing Java version: %s', e)
                return False

            if supported and runnable and java_version >= min_java_version:
                return True

    except Exception as e:
        logger.error('Error retrieving installed Java information: %s', e)
    return False


def run_script():
    session_key = sys.stdin.readline().strip()
    cfm = ConfManager(session_key, 'SA-ITOA')
    conf = cfm.get_conf('inputs')
    script_settings = conf.get('script://$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py')
    is_enabled_java_check = script_settings.get('enable_java_version_check', '1') == '1'

    if is_enabled_java_check and not is_valid_jvm(session_key):
        logger.error('Java version 8.x - 11.x or Java 17 is required in order to start the Rules Engine.')
        exit(1)

    server_uri = rest.makeSplunkdUri()

    # log the message for restartless upgrade testing which can be useful while debugging.
    logger.info('Restartless upgrade - Reloaded modular input '
                'script://$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py')

    if len(session_key) == 0:
        logger.error("Did not receive a session key from splunkd. "
                     + "Must enable passAuth in inputs.conf for this "
                     + "script to run.\n")
        exit(2)

    shcluster_status_check_enabled = is_shcluster_status_check_enabled(script_settings)
    pulse_frequency = int(script_settings.get('pulse_frequency', 20))

    try:
        if ( shcluster_status_check_enabled
             and is_shc_member(session_key, logger)
             and is_shcluster_restarting(session_key, logger) ):
            exit(0)
    except Exception as e:
        logger.error('SHCluster status check failed with error: %s', e)
        exit(1)

    try:
        if not modular_input_should_run(session_key, logger=logger):
            logger.info("The modular input won't be executed on this node as it's not a Captain of SHC.")
            return

        logger.info('Rules Engine script has started.')

        bash_command, cwd = get_args(script_settings)

        logger.info('Generated bash_command=%s and cwd=%s' % (str(bash_command), str(cwd)))

        data = dict()
        search_info = dict()
        search_info['splunkd_uri'] = server_uri
        search_info['session_key'] = session_key
        data['action'] = 'getinfo'
        data['searchinfo'] = search_info

        with subprocess.Popen(
            bash_command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            cwd=cwd
        ) as process:
            while process.poll() is None:
                if ( shcluster_status_check_enabled
                     and not modular_input_should_run(session_key, logger=logger) ):
                    logger.info('SH Captain check failed. Exiting Rules Engine script.')
                    break
                string = json.dumps(data) + '\n'
                process.stdin.write(string.encode())
                process.stdin.flush()
                time.sleep(pulse_frequency)

    except Exception as e:
        logger.error(str(e))


if __name__ == '__main__':
    run_script()
    sys.exit(0)
