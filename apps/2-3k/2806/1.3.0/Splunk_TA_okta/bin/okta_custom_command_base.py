import urllib2, sys
import re
import logging
import okta_config
from splunktalib.common import log
import splunk.clilib.cli_common as scc
import splunk.Intersplunk
import time
import traceback
from splunktalib import rest
from collections import OrderedDict


THREADS_COUNT = 30

oprt_dic = {'add': 'PUT',
            'remove': 'DELETE',
            'deactivate': 'POST',
            'activate': 'POST'}

endpoint_dict = {'add':  '/api/v1/groups/{0}/users/{1}',
            'remove': '/api/v1/groups/{0}/users/{1}',
            'deactivate': '/api/v1/users/{0}/lifecycle/deactivate',
            'activate': '/api/v1/users/{0}/lifecycle/activate?sendEmail=false'}

spl_commands = {'user': 'search index=* sourcetype=okta:im source=okta:user|dedup id|search profile.login="{0}"|fields '
                        'id',
                'group': 'search index=* sourcetype=okta:im source=okta:group|dedup id|search profile.name="{'
                         '0}"|fields id'}

_LOGGER = log.Logs().get_logger("ta_okta", level=logging.DEBUG)



class Option(object):
    def __init__(self, option_id, option_name, type='user'):
        self.type = str(type)

        if option_id is not None:
            self.option_id = str(option_id)
        else:
            self.option_id = None
        if option_name is not None:
            self.option_name = str(option_name)
        else:
            self.option_name = None

    def is_token(self, id_name):
        if id_name=='id':
            return self.option_id is not None and len(self.option_id) > 1 and self.option_id[0] == '$' \
                and self.option_id[-1] == '$'
        elif id_name=='name':
            return self.option_name is not None and len(self.option_name) > 1 and self.option_name[0] == '$' \
                and self.option_name[-1] == '$'

    def is_token_option(self):
        if self.is_token('id'):
            return True
        else:
            return (self.option_id is None or self.option_id.strip() is '') and self.is_token('name')

    def get_option_value(self, id_name):
        if not self.is_token(id_name=id_name):
            return self.option_id if id_name=='id' else self.option_name
        else:
            return self.option_id[1:-1] if id_name=='id' else self.option_name[1:-1]

    def is_empty(self):
        option_id = self.get_option_value('id')
        option_name = self.get_option_value('name')
        return (option_id is None or option_id.strip() is '') and \
                (option_name is None or option_name.strip() is '')

    def __eq__(self, other):
        return type(self) == type(other) and self.option_id == other.option_id \
                and self.type == other.type  and self.option_name==other.option_name


class CustomCommand(object):
    """
    Base class of Custom Command
    """
    def __init__(self):
        self.session_key =  self.get_session_key()
        self.okta_conf = self.get_okta_server_config()
        self.options = self._get_options()
        self.results = self._get_results()

    def _get_options(self):
        _, options = splunk.Intersplunk.getKeywordsAndOptions()
        return options

    def _get_results(self):
        results, _, _ = splunk.Intersplunk.getOrganizedResults()
        return results

    def get_session_key(self):
        """
        When called as custom search script, splunkd feeds the following
        to the script as a single line
        'authString:<auth><userId>(your user id)</userId><username>(your username)</username>\
            <authToken>(your session key)</authToken></auth>'

        When called as an alert callback script, splunkd feeds the following
        to the script as a single line
        sessionKey=(your session key)
        """
        _LOGGER.info('call get_session_key()')
        session_key = sys.stdin.readline()
        m = re.search("authToken>(.+)</authToken", session_key)
        if m:
            session_key = m.group(1)
        else:
            session_key = session_key.replace("sessionKey=", "").strip()
        session_key = urllib2.unquote(session_key.encode("ascii"))
        session_key = session_key.decode("utf-8")
        return session_key

    def get_okta_server_config(self):
        """
        get the configuration of Okta server for custom command.
        :param session_key:

        """
        try:
            sk = self.session_key
            try:
                splunk_uri = scc.getMgmtUri()
            except Exception as ex:
                _LOGGER.error("Internal error occurs: Failed to get the splunk_uri: %s", ex.message)
                raise
            config = okta_config.OktaConfig(splunk_uri, sk, "")

            okta_conf = config.get_okta_conf()
            config.update_okta_conf(okta_conf)
            return okta_conf
        except Exception as ex:
            _LOGGER.error("Internal error occurs: Failed to get config of Okta server for custom command and alert:  "
                          "%s Please go to setup page to reconfigure the okta server and token.",
                          ex.message)
            _LOGGER.error(traceback.format_exc())
            raise

    def _do_spl_search(self, command):
        """
        execute the SPL command and return the userid/groupid
        :param command: SPL command
        """
        splunk_uri = scc.getMgmtUri(
        ) + '/servicesNS/admin/search/search/jobs/export?output_mode=json'
        data = {"search": command}
        resp, content = rest.splunkd_request(splunk_uri,
                                             self.session_key,
                                             method="POST",
                                             data=data,
                                             retry=3)
        if content:
            cont = '[' + ','.join(content.strip().split('\n')) + ']'
            import json

            cont = json.loads(cont)
            result = cont[0].get("result")
            if result:
                return result.get("id", None)
        return None

    def get_user_or_group(self, type):
        """
        Get user/group Option Object
        :param type: <string> 'user' OR 'group'
        :return: Option object
        """
        option_id = self.options.get(type + 'id', None)
        option_name = self.options.get(type + 'name', None)

        return Option(option_id=option_id, option_name=option_name, type=type)


    def search_token(self, option, max):
        """
        get the token value in the result events
        :param option: Option object
        :param max: The top max events in the results which the custom command applies to.
        :return: list of Option object whose option_value corresponds to the token value in results
        """
        opt_list=[]
        for result in self.results[:max]:
                opt_id = result.get(option.get_option_value(id_name='id'), None)
                if opt_id:
                    opt_list.append(Option(option_id=opt_id,option_name=None, type=option.type))
                elif option.is_token(id_name='name'):
                    opt_list.append(Option(option_id=None, option_name=result.get(option.get_option_value(
                        id_name='name'), None), type=option.type))
                else:
                    opt_list.append(Option(option_id=None,option_name=option.option_name,type=option.type))
        return opt_list





    def search_option_id(self, option):
        """
        Search userid/groupid according to the username/groupname
        :param option: Option object
        :return: userid/groupid <string>
        """
        if not option.option_id:
            command = spl_commands.get(option.type).format(option.option_name)
            return self._do_spl_search(command)
        return option.option_id

    def gen_result(self, status, detail):
        """
        Generate the results of custom command
        :param status: <string> 'success' or 'fail'
        :param detail: The detail result of executing the custom command
        :return: dict
        """
        result = OrderedDict()
        result['_time'] = time.time()
        result['update_status'] = status
        result['detail'] = detail
        return result

    def process_error(self, error_msg):
        """
        Process errors: logger and parse error to the UI
        :param error_msg: error message <string>
        """
        _LOGGER.error('[Okta customer command] ' + error_msg)
        splunk.Intersplunk.parseError(error_msg)

    def _get_max(self):
        """
        Get the max parameter from the options. If the max parameter is not provided by user,
        use the size of results if results is not empty, otherwise, set max to be 1
        :return: <int>
        """
        max = 0
        error_msg = ''
        try:
            max = int(self.options.get('max', 0))
            assert  max>=0
        except (ValueError, AssertionError):
            error_msg = 'Value of the "max" is invalid. It must be 0 or positive number. Set it to 0 if you want to ' \
                       'retrieve all data.'
            self.process_error(error_msg)
        return max or len(self.results)

    def gen_argument_list(self, max, user, group=None):
        """
        generate user Option list and group Option list to be executed  in custom command execution.
        :param max: The top max events in the results which the custom command applies to.
        :param user: Option object
        :param group: Option object
        :return: user Option list and group Option list (The options are all not tokenized)
        """
        if group is None:
            group_list = None
            if user.is_token_option():
                user_list = self.search_token(user,max)
            else:
                user_list = [user]

        else:
            if user.is_token_option() and group.is_token_option():
                user_list = self.search_token(user, max)
                group_list = self.search_token(group, max)
            elif user.is_token_option():
                user_list = self.search_token(user, max)
                group_list = [group for _ in self.results[:max]]
            elif group.is_token_option():
                group_list = self.search_token(group, max)
                user_list = [user for _ in self.results[:max]]
            else:
                user_list = [user]
                group_list = [group]

        return user_list, group_list






