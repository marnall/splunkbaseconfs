import sys
import json
import traceback
import logging
from splunktalib.common import log
from splunktalib.common import util
from splunktalib.common.util import is_true
from okta_member_operate_command import MemberOperateCommand
import okta_custom_alert_common as ocac

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)

util.remove_http_proxy_env_vars()

if __name__ == "__main__":
    _LOGGER.info('Start to execute the member operate alert action.')
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":
        try:
            raw_payload = sys.stdin.read()
            payload = json.loads(raw_payload)

            oprt = payload.get('configuration', {}).get('action')
            user_id = payload.get('configuration', {}).get('user_id')
            user_name = payload.get('configuration', {}).get('user_name')
            group_id = payload.get('configuration', {}).get('group_id')
            group_name = payload.get('configuration', {}).get('group_name')

            search_name = payload.get('search_name')
            _LOGGER.info('[okta member operate alert] The search name is {}'.format(search_name))

            session_key = payload.get('session_key')

            def _get_session(dummy):
                return session_key
            # Redirect the get_session_key method of UserOperateCommand
            MemberOperateCommand.get_session_key = _get_session

            member_cmd = MemberOperateCommand(oprt)
            if is_true(member_cmd.okta_conf.get("custom_cmd_enabled", "")):
                user = ocac.get_option('user', user_id, user_name)
                group = ocac.get_option('group', group_id, group_name)
                if user and group:
                    alert_result = member_cmd.single_member_operate((user, group))
                    if alert_result.get('update_status') == 'success':
                        _LOGGER.info('[okta member operate alert] The member operate alert action executes successfuly.'
                                     ' {0} the user {1} in group {2} successfully.'.format(oprt, user_id or
                                                                                           user_name, group_id or
                                                                                           group_name))
                    else:
                        _LOGGER.error('[okta member operate alert] The member operate alert action failed. Action: '
                                        '{0}, user: {1}, group:{2}'.format(oprt, user_id or user_name, group_id or group_name))
                else:
                    error_msg = '[okta member operate alert] The user or group configured is empty or can not be ' \
                                'found in the events. Please try again.'
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
            print >> sys.stderr, "ERROR Unexpected internal error: {}".format(
                traceback.format_exc())
            sys.exit(3)
    else:
        print >> sys.stderr, ("FATAL Unexpected internal error: Unsupported execution mode "
                              "(expected --execute flag)")
        sys.exit(1)



