import sys
import json
import traceback
import logging
from splunktalib.common import log
from splunktalib.common import util
from splunktalib.common.util import is_true
from okta_user_operate_command import UserOperateCommand
import okta_custom_alert_common as ocac

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)

util.remove_http_proxy_env_vars()

if __name__ == "__main__":
    _LOGGER.info('Start to execute the deactivate user alert action.')
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)
            user_id = payload.get('configuration', {}).get('user_id')
            user_name = payload.get('configuration', {}).get('user_name')
            search_name = payload.get('search_name')
            _LOGGER.info('[okta deactivate user alert] The search name is {}'.format(search_name))

            session_key = payload.get('session_key')

            def _get_session(dummy):
                return session_key
            # Redirect the get_session_key method of UserOperateCommand
            UserOperateCommand.get_session_key = _get_session

            user_cmd = UserOperateCommand(oprt='deactivate')
            if is_true(user_cmd.okta_conf.get("custom_cmd_enabled", "")):
                user = ocac.get_option('user', user_id, user_name)
                if user:
                    alert_result = user_cmd.single_user_operate(user)
                    if alert_result.get('update_status') == 'success':
                        _LOGGER.info('[okta deactivate user alert] The deactivate user alert action executes '
                                     'successfully. The user {0} is deactivated successfully.'.format(user_id or user_name))
                    else:
                        _LOGGER.error('[okta deactivate user alert] The deactivate user alert action failed (user: {'
                                        '}).'.format(user_id or user_name))
                else:
                    error_msg = '[okta deactivate user alert] The configured user is empty or can not be found in ' \
                                'the events. Please try again.'
                    print >> sys.stderr, error_msg
                    _LOGGER.error(error_msg)
                    sys.exit(1)
            else:
                error_msg = '[okta member operate alert] Okta server for custom alert is not configured. Please ' \
                            'configure the Okta server in the Setup page and try again.'
                print >> sys.stderr, error_msg
                _LOGGER.error(error_msg)
                sys.exit(1)
        except Exception:
            print >> sys.stderr, "ERROR Unexpected error: {}".format(
                traceback.format_exc())
            sys.exit(3)
    else:
        print >> sys.stderr, ("FATAL Unsupported execution mode "
                              "(expected --execute flag)")
        sys.exit(1)



