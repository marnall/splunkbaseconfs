import logging
from splunktalib.common import log
from splunktalib.common import util
from okta_member_operate_command import  MemberOperateCommand

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)

util.remove_http_proxy_env_vars()

def remove_member():
    _LOGGER.info("call add_member()")
    remove_member_cmd = MemberOperateCommand('remove')
    remove_member_cmd.member_operate()

if __name__ == "__main__":
    remove_member()