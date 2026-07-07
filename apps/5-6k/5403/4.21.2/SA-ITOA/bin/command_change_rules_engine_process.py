import json
import sys
import time
import urllib.parse
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))

from itsi.itsi_utils import ITOAInterfaceUtils
from ITOA.itoa_common import update_conf_stanza, is_feature_enabled
from SA_ITOA_app_common.splunklib.searchcommands import Configuration, Option, GeneratingCommand, dispatch, validators
from SA_ITOA_app_common.splunklib import results
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from ITOA.setup_logging import setup_logging
from itsi_module.itsi_module_common import ItsiModuleError
from splunk import rest
from ITOA.controller_utils import HTTPError


@Configuration()
class ITSIChangeRulesEngineProcess(GeneratingCommand):
    is_use_adhoc_search = Option(
        doc='''
            **Syntax:** **is_required_adhoc_search=***<Boolean>*
            **Description:** Is the rules engine process switch to adhoc''',
        require=True,
        validate=validators.Boolean(),
    )
    is_use_queue_mode = Option(
        doc='''
                **Syntax:** **is_use_queue_mode=***<Boolean>*
                **Description:** Is the rules engine process switch to use nats jetstream queue''',
        require=True,
        validate=validators.Boolean(),
    )
    is_use_rt_search = Option(
        doc='''
                **Syntax:** **is_use_rt_search=***<Boolean>*
                **Description:** Is the rules engine process switch to real-time search''',
        require=True,
        validate=validators.Boolean(),
    )
    is_disable_all = Option(
        doc='''
                **Syntax:** **is_disable_all=***<Boolean>*
                **Description:** Is disable all the the rules engine processes''',
        require=False,
        validate=validators.Boolean(),
    )
    retries = Option(
        doc='''
            **Syntax:** **retries=***<Integer>*
            **Description:** Number of retries for the java''',
        require=False,
        default=12,
        validate=validators.Integer(),
    )
    encoded_scripted_adhoc_input_name = urllib.parse.quote(
        '$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_adhoc_re_init.py', safe='')
    encoded_scripted_queue_input_name = urllib.parse.quote(
        '$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py', safe='')
    is_rt_search = False
    is_adhoc_search = False
    is_queue_mode = False
    CONF_FILE = 'app_common_flags'
    check_running_rules_engine_process = "search index=_internal source=\"*itsi_rules_engine*\" reMode=RealTime " \
                                         "| stats dc(reId) as process_num"
    logger = setup_logging("itsi_change_rules_engine.log", "itsi.change.rules_engine")

    def enable_or_disable_event_grouping(self, session_key):
        try:
            service = ITOAInterfaceUtils.service_connection(self.service.token, app_name="SA-ITOA")
            if (self.is_use_adhoc_search or self.is_use_queue_mode) and self.is_rt_search:
                rest.simpleRequest('/servicesNS/nobody/SA-ITOA/saved/searches/itsi_event_grouping?disabled=1',
                                   sessionKey=session_key, method='POST', raiseAllErrors=True)

                itsi_event_grouping_search = service.saved_searches["itsi_event_grouping"]
                self.logger.info('Status of itsi_event_grouping search after disabling it : disabled=%s',
                                 itsi_event_grouping_search["disabled"])
            elif not (self.is_use_adhoc_search or self.is_use_queue_mode) and not self.is_rt_search:
                rest.simpleRequest('/servicesNS/nobody/SA-ITOA/saved/searches/itsi_event_grouping?disabled=0',
                                   sessionKey=session_key, method='POST', raiseAllErrors=True)

                itsi_event_grouping_search = service.saved_searches["itsi_event_grouping"]
                self.logger.info('Status of itsi_event_grouping search after enabling it : disabled=%s',
                                 itsi_event_grouping_search["disabled"])
        except Exception as err:
            self.logger.error(
                'Error occurred while disabling/enabling the itsi_event_grouping search: %s', err)

    def enable_event_grouping(self, session_key):
        try:
            service = ITOAInterfaceUtils.service_connection(self.service.token, app_name="SA-ITOA")
            rest.simpleRequest('/servicesNS/nobody/SA-ITOA/saved/searches/itsi_event_grouping?disabled=0',
                               sessionKey=session_key, method='POST', raiseAllErrors=True)

            itsi_event_grouping_search = service.saved_searches["itsi_event_grouping"]
            self.logger.info('Status of itsi_event_grouping search after enabling it : disabled=%s',
                             itsi_event_grouping_search["disabled"])
        except Exception as err:
            self.logger.error(
                'Error occurred while disabling/enabling the itsi_event_grouping search: %s', err)

    def disable_event_grouping(self, session_key):
        try:
            service = ITOAInterfaceUtils.service_connection(self.service.token, app_name="SA-ITOA")
            rest.simpleRequest('/servicesNS/nobody/SA-ITOA/saved/searches/itsi_event_grouping?disabled=1',
                               sessionKey=session_key, method='POST', raiseAllErrors=True)

            itsi_event_grouping_search = service.saved_searches["itsi_event_grouping"]
            self.logger.info('Status of itsi_event_grouping search after disabling it : disabled=%s',
                             itsi_event_grouping_search["disabled"])
        except Exception as err:
            self.logger.error(
                'Error occurred while disabling/enabling the itsi_event_grouping search: %s', err)

    def enable_or_disable_modular_input(self, session_key, is_enable, input_mode, script):
        try:
            if is_enable:
                response, content = rest.simpleRequest(
                    f"/servicesNS/nobody/SA-ITOA/data/inputs/script/{input_mode}?disabled=0",
                    sessionKey=session_key,
                    method="POST",
                    raiseAllErrors=True,
                )
                if response.status != 200:
                    raise Exception("Error while enabling the modular input")
            else:
                response, content = rest.simpleRequest(
                    f"/servicesNS/nobody/SA-ITOA/data/inputs/script/{input_mode}?disabled=1",
                    sessionKey=session_key,
                    method="POST",
                    raiseAllErrors=True,
                )
                if response.status != 200:
                    raise Exception("Error while disabling the modular input")

        except Exception as err:
            self.logger.error('Error occurred while disabling the ' + script + ' scripted input: %s', str(err))

    def wait_for_job(self, searchjob, maxtime=-1):
        """
        Wait up to maxtime seconds for searchjob to finish.  If maxtime is
        negative (default), waits forever.  Returns true, if job finished.
        """
        pause = 0.2
        lapsed = 0.0
        while not searchjob.is_done():
            time.sleep(pause)
            lapsed += pause
            if maxtime >= 0 and lapsed > maxtime:
                break
        return searchjob.is_done()

    def get_search_job(self):
        """
        Creates search job for current episode.
        """
        try:
            current_rules_engine_job = self.service.jobs.create(
                self.check_running_rules_engine_process,
                earliest_time='-30s',
            )
        except HTTPError as e:
            raise Exception('Error when running search Error: {e}'.format(e=e))
        return current_rules_engine_job

    def check_running_java_process(self):
        try:
            while self.retries:
                current_rules_engine_job = self.get_search_job()
                if not self.wait_for_job(current_rules_engine_job, 300):
                    raise Exception("Search for current rules engine process values timed out")
                rr = results.ResultsReader(current_rules_engine_job.results())
                process_num = 0
                # In this type of results_reader object, it is expected that there is only one entry
                # returned as the result, which is the process_num.
                for result in rr:
                    process_num = int(result.get('process_num', None))
                self.logger.info('Checking the number of running java process : %s , retries : %s',
                                 process_num, self.retries)
                if process_num == 0:
                    break
                self.retries -= 1
                time.sleep(10)
        except Exception as e:
            self.logger.error(
                'Error occurred while checking the number of running java process: %s', e)

    def update_feature_flag(self, session_key, is_enable, mode):
        self.is_feature_enabled = is_feature_enabled(mode, session_key, reload=True)
        if is_enable:
            result = update_conf_stanza(session_key, self.CONF_FILE, {'name': mode, 'disabled': '0'}, app='itsi')
            if result["response"]["status"] == '200' or result["response"]["status"] == '201':
                self.logger.info('Successfully updated the feature flag for ' + mode,
                                 'is_feature_enabled : %s', is_feature_enabled)
            else:
                self.logger.error('Error updating the feature flag for ' + mode)
                raise ItsiModuleError(status=400, message='Failed updating feature flag for ' + mode)
        else:
            result = update_conf_stanza(session_key, self.CONF_FILE, {'name': mode, 'disabled': '1'}, app='itsi')
            if result["response"]["status"] == '200' or result["response"]["status"] == '201':
                self.logger.info('Successfully updated the feature flag for ' + mode,
                                 'is_feature_enabled : %s', is_feature_enabled)
            else:
                self.logger.error('Error updating the feature flag for ' + mode)
                raise ItsiModuleError(status=400, message='Failed updating feature flag for ' + mode)

    def check_process(self):
        if self.is_use_adhoc_search and self.is_adhoc_search:
            raise Exception("The adhoc search modular input is already enabled")
        elif self.is_use_queue_mode and self.is_queue_mode:
            raise Exception("The queue mode modular input is already enabled")

    def is_rt_search_mode_enabled(self, session_key):
        try:
            service = ITOAInterfaceUtils.service_connection(session_key, app_name="SA-ITOA")
            itsi_event_grouping_search = service.saved_searches["itsi_event_grouping"]
            if itsi_event_grouping_search["disabled"] == "0":
                return True
            else:
                return False
        except Exception as e:
            self.logger.error('Error while validating the rules engine process : %s', str(e))

    def is_adhoc_or_queue_mode_enabled(self, session_key, input_name):
        try:
            response, content = rest.simpleRequest(
                f"/servicesNS/nobody/SA-ITOA/data/inputs/script/{input_name}?output_mode=json",
                sessionKey=session_key,
                method="GET",
                raiseAllErrors=True,
            )
            parsed_content = json.loads(content)
            if not parsed_content["entry"][0]["content"]["disabled"]:
                return True
            else:
                return False
        except Exception as e:
            self.logger.error('Error while validating the adhoc/queue mode process : %s', str(e))

    def generate(self):
        self.logger.info('Switching the rules engine process start')
        try:
            self.is_rt_search = self.is_rt_search_mode_enabled(self.service.token)
            self.is_adhoc_search = self.is_adhoc_or_queue_mode_enabled(self.service.token,
                                                                       self.encoded_scripted_adhoc_input_name)
            self.is_queue_mode = self.is_adhoc_or_queue_mode_enabled(self.service.token,
                                                                     self.encoded_scripted_queue_input_name)
            self.common_config_queue_flag = is_feature_enabled('itsi-rulesengine-queue', self.service.token, reload=True)
            self.common_config_adhoc_flag = is_feature_enabled('itsi-rulesengine-adhoc', self.service.token, reload=True)
            # option to disable all the rules engine processes.
            # this is helpful in scenarios when multiple JVM processes are running
            if self.is_disable_all:
                if self.is_queue_mode:
                    self.enable_or_disable_modular_input(self.service.token, False,
                                                         self.encoded_scripted_queue_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py]')
                if self.common_config_queue_flag:
                    self.update_feature_flag(self.service.token, False, 'itsi-rulesengine-queue')
                if self.is_adhoc_search:
                    self.enable_or_disable_modular_input(self.service.token, False,
                                                         self.encoded_scripted_adhoc_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_adhoc_re_init.py]')
                if self.common_config_adhoc_flag:
                    self.update_feature_flag(self.service.token, False, 'itsi-rulesengine-adhoc')
                if self.is_rt_search:
                    self.disable_event_grouping(self.service.token)
                return

            # check if all required modes are set to false
            if not self.is_use_rt_search and not self.is_use_adhoc_search and not self.is_use_queue_mode:
                raise Exception(
                    'User needs to enable at least one mode: real-time search, adhoc search, or queue mode.')

            cfm = ConfManager(self.service.token, 'SA-ITOA')
            conf = cfm.get_conf('itsi_nats')
            settings = conf.get('nats_settings')
            skip_check_process = int(settings.get('skip_check_process', 1))
            if not skip_check_process:
                self.check_process()

            # check if more than one modes are set to true
            if sum([self.is_use_rt_search, self.is_use_adhoc_search, self.is_use_queue_mode]) > 1:
                raise Exception('User can enable only one mode: real-time search, adhoc search, or queue mode.')

            # if adhoc search enable request is received, then make sure rt search & queue mode are disabled
            if self.is_use_adhoc_search:
                if self.is_queue_mode:
                    self.enable_or_disable_modular_input(self.service.token, False,
                                                         self.encoded_scripted_queue_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py]')
                if self.common_config_queue_flag:
                    self.update_feature_flag(self.service.token, False, 'itsi-rulesengine-queue')
                if self.is_rt_search:
                    self.disable_event_grouping(self.service.token)

            # if queue mode enable request is received, then make sure rt search & adhoc mode are disabled
            if self.is_use_queue_mode:
                if self.is_adhoc_search:
                    self.enable_or_disable_modular_input(self.service.token, False,
                                                         self.encoded_scripted_adhoc_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_adhoc_re_init.py]')
                if self.common_config_adhoc_flag:
                    self.update_feature_flag(self.service.token, False, 'itsi-rulesengine-adhoc')
                if self.is_rt_search:
                    self.disable_event_grouping(self.service.token)

            # if rt search enable request is received, then make sure adhoc search & queue mode are disabled
            if self.is_use_rt_search:
                if self.is_queue_mode:
                    self.enable_or_disable_modular_input(self.service.token, False,
                                                         self.encoded_scripted_queue_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py]')
                if self.common_config_queue_flag:
                    self.update_feature_flag(self.service.token, False, 'itsi-rulesengine-queue')
                if self.is_adhoc_search:
                    self.enable_or_disable_modular_input(self.service.token, False,
                                                         self.encoded_scripted_adhoc_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_adhoc_re_init.py]')
                if self.common_config_adhoc_flag:
                    self.update_feature_flag(self.service.token, False, 'itsi-rulesengine-adhoc')
                self.check_running_java_process()
                self.enable_event_grouping(self.service.token)
            else:
                self.check_running_java_process()

            if self.is_use_adhoc_search:
                if not self.is_adhoc_search:
                    self.enable_or_disable_modular_input(self.service.token, True,
                                                         self.encoded_scripted_adhoc_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_adhoc_re_init.py]')
                if not self.common_config_adhoc_flag:
                    self.update_feature_flag(self.service.token, True, 'itsi-rulesengine-adhoc')

            if self.is_use_queue_mode:
                if not self.is_queue_mode:
                    self.enable_or_disable_modular_input(self.service.token, True,
                                                         self.encoded_scripted_queue_input_name,
                                                         '[$SPLUNK_HOME/etc/apps/SA-ITOA/bin/itsi_queue_re_init.py]')
                if not self.common_config_queue_flag:
                    self.update_feature_flag(self.service.token, True, 'itsi-rulesengine-queue')

            yield {}
        except Exception as e:
            self.logger.info("Exception while switching the rules engine process")
            self.error_exit(e, message=str(e))


dispatch(ITSIChangeRulesEngineProcess, sys.argv, sys.stdin, sys.stdout, __name__)
