from okta_custom_command_base import CustomCommand
from multiprocessing.pool import ThreadPool
from splunktalib.common.util import is_true
import okta_rest_client as oac
import splunk.Intersplunk
import okta_custom_command_base as occb

_LOGGER = occb._LOGGER

oprt_cmd = {'deactivate': 'oktadeactivateuser'}

class UserOperateCommand(CustomCommand):
    def __init__(self, oprt):
        """
        :param oprt: 'deactivate' for deactivate okta user
        """
        super(UserOperateCommand, self).__init__()
        self.oprt = oprt

    def user_operate_in_batch(self, user_list):
        """
        The method to do user operation with multi-threads
        :param user_list: list of user Option
        :return: results: list of <dict>
        """
        pool = ThreadPool(occb.THREADS_COUNT)
        func = lambda x,y: x if y in x else x + [y]
        res = pool.map(self.single_user_operate, reduce(func, [[],]+list(user_list)))
        pool.close()
        pool.join()
        return res

    def single_user_operate(self, user):
        """
        The method to deactivate user
        :param: user: user Option object
        :return: dict
        """
        result = {}
        if not user.is_empty():
            user_id = self.search_option_id(user)
            if user_id is not None:
                error_msg, result = self._do_user_operate(user_id)
            else:
                error_msg = 'The command can not be processed. Make sure you enter the valid username and ' \
                            'ensure the user data is indexed.'
        else:
            error_msg = 'The configured fields(s) can not be found in the events or it is empty. The userid: {0}, username: {1}'.format(
                user.option_id, user.option_name, )
        if error_msg:
            result = self.gen_result('fail', error_msg)
            _LOGGER.error(error_msg)
        return result

    def _do_user_operate(self, user_id):
        """
        The detail implementation to deactivate one user_id
        :return: error_msg <string>  and  result <dict>
        """
        server_url = self.okta_conf.get('okta_server_url', '')
        server_token = self.okta_conf.get('okta_server_token', '')
        error_msg = ''
        result = {}
        method = occb.oprt_dic.get(self.oprt)
        if server_url and server_token:
            client = oac.OktaRestClient(self.okta_conf)
            endpoint = occb.endpoint_dict.get(self.oprt).format(user_id)
            response = client.request(endpoint, None, method,
                                      'okta_server_url',
                                      'okta_server_token')
            if response.get("error"):
                error_msg = "Failed to {0} the user {1}. The user does not exist or the user is already {2}ed. " \
                            "Error: {3}".format(self.oprt, user_id, self.oprt, response.get('error'))
            else:
                detail = self.oprt + " the user {0} successfully.".format(user_id)
                result = self.gen_result('success', detail)
                _LOGGER.info(detail)
        else:
            error_msg = 'Okta server is not configured. Please configure the Okta server in the Setup page and try again.'
        return error_msg, result

    def check_empty(self, option):
        if option.is_empty():
            error_msg = 'Please enter the "{0}id" or "{0}name". Usage: {1} userid|username=<value>|$<field_name>$ ' \
                         '[ max=<count of max events to process> ]'.format(option.type, oprt_cmd.get(self.oprt,''))
            self.process_error(error_msg)
            return False
        return True

    def user_operate(self):
        """
        The entrance method of user operation custom command.
        """
        if is_true(self.okta_conf.get("custom_cmd_enabled", "")):
            max = self._get_max()
            user = self.get_user_or_group('user')
            if self.check_empty(user):
                user_list, _ = self.gen_argument_list(max,user)
                user_oprt_results = self.user_operate_in_batch(user_list)
                splunk.Intersplunk.outputResults(user_oprt_results)
                return user_oprt_results
        else:
            error_msg = "The custom command is not enabled. Please enable it in the Setup page."
            return self.process_error(error_msg)


