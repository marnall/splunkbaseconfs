from okta_custom_command_base import CustomCommand
from multiprocessing.pool import ThreadPool
from itertools import izip
from splunktalib.common.util import is_true
import okta_rest_client as oac
import splunk.Intersplunk
import okta_custom_command_base as occb

_LOGGER = occb._LOGGER

oprt_cmd = {'add': 'oktaaddmember',
            'remove': 'oktaremovemember',
            }


class MemberOperateCommand(CustomCommand):

    def __init__(self, oprt):
        """
        :param oprt: 'add' OR 'remove'
                     'add' for add member
                     'remove' for remove member
        """
        super(MemberOperateCommand, self).__init__()
        self.oprt = oprt

    def check_empty(self, option):
        if option.is_empty():
            error_msg = 'Please enter the "{0}id" or "{0}name". Usage: {1} userid|username=<value>|$<field_name>$ ' \
                        'groupid|groupname=<value>|$<field_name>$ [ max=<count of max events to process> ]'.format(
                option.type, oprt_cmd.get(self.oprt, ''))
            self.process_error(error_msg)
            return False
        return True

    def member_operate(self):
        """
        The entrance method of member operation custom command.
        """
        if is_true(self.okta_conf.get("custom_cmd_enabled", "")):
            user = self.get_user_or_group('user')
            group = self.get_user_or_group('group')
            max = self._get_max()
            if self.check_empty(user) and self.check_empty(group):
                user_list, group_list = self.gen_argument_list(max, user, group)

                member_oprt_results = self.member_operate_in_batch(user_list, group_list)
                splunk.Intersplunk.outputResults(member_oprt_results)
                return member_oprt_results
        else:
            error_msg = "The custom command is not enabled. Please enable it in the Setup page."
            return self.process_error(error_msg)

    def member_operate_in_batch(self, user_list, group_list):
        """
        The method to do member operation with multi-threads
        :param user_list: list of user Option
        :param group_list: list of group Option
        :return: results: list of <dict>
        """
        pool = ThreadPool(occb.THREADS_COUNT)
        func = lambda x,y: x if y in x else x + [y]
        res = pool.map(self.single_member_operate, reduce(func, [[],]+list(izip(user_list, group_list))))
        pool.close()
        pool.join()
        return res

    def single_member_operate(self, (user, group)):
        """
        The method to add/remove single user to/from single group
        :param: user: user Option object
        :param: group: group Option object
        :return: dict
        """
        result = {}
        if not user.is_empty() and not group.is_empty():
            user_id = self.search_option_id(user)
            group_id = self.search_option_id(group)
            if user_id is not None and group_id is not None:
                error_msg, result = self._do_member_operate(user_id, group_id)
            else:
                error_msg = 'The command can not be processed. Make sure you enter the valid username/groupname and ' \
                            'ensure the user and group data is indexed.'
        else:
            error_msg = 'The configured fields(s) can not be found in the events or it is empty. The userid: {0}, ' \
                        'username: {1}, groupid: {2}, groupname: {3}.'.format(user.option_id, user.option_name,
                                                                              group.option_id, group.option_name)
        if error_msg:
            result = self.gen_result('fail', error_msg)
            _LOGGER.error(error_msg)
        return result

    def _do_member_operate(self, user_id, group_id):
        """
        The detail implementation to add/remove one user_id to/from one group_id
        :return: error_msg <string>  and  result <dict>
        """
        server_url = self.okta_conf.get('okta_server_url', '')
        server_token = self.okta_conf.get('okta_server_token', '')
        error_msg = ''
        result = {}
        method = occb.oprt_dic.get(self.oprt)
        if server_url and server_token:
            client = oac.OktaRestClient(self.okta_conf)
            endpoint = occb.endpoint_dict.get(self.oprt).format(group_id,user_id)
            response = client.request(endpoint, None, method,
                                      'okta_server_url',
                                      'okta_server_token')
            if response.get("error"):
                error_msg = 'Failed to {0} the user {1} in the group {2}. Error: {3}'.\
                    format(self.oprt, user_id, group_id,response.get('error'))
            else:
                detail = self.oprt + " the user {0} in the group {1} successfully.".format(user_id, group_id)
                result = self.gen_result('success', detail)
                _LOGGER.info(detail)
        else:
            error_msg = 'Okta server is not configured. Please configure the Okta server in the Setup page and try again.'
        return error_msg, result