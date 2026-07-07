import logging
from splunktalib.common import log
from splunktalib.common import util
from okta_user_operate_command import  UserOperateCommand

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)

util.remove_http_proxy_env_vars()

def deactivate_user():
    """
    The entrance method to deactivate a user account.
    """
    _LOGGER.info("call deactivate_user()")
    deactivate_user_cmd = UserOperateCommand('deactivate')
    deactivate_user_cmd.user_operate()

if __name__ == "__main__":
    deactivate_user()
