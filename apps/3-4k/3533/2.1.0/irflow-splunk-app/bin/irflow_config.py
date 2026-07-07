# this is a required import
import os
import sys
import requests
import splunk_common.log as log
import traceback
import json
from irflow_common.irflow_client import IRFlowClient
import splunk.admin as admin # https://answers.splunk.com/answers/7909/where-is-the-python-api-for-splunk-intersplunk.html
import splunk.auth as auth

logger = log.Logs('irflow-splunk-app').get_logger("setup")

SPLUNK_URL = auth.splunk.getLocalServerInfo()


class ConfigApp(admin.MConfigHandler):
    """
    Set up supported arguments
    """

    def setup(self):
        """
        Set up supported arguments
        """
        try:
            if self.requestedAction == admin.ACTION_EDIT:
                for arg in ['api_user', 'api_key', 'disabled', 'address', 'verify_ssl', 'debug', 'verbose',
                            'stage_api_user', 'stage_api_key', 'stage_address', 'stage_verify_ssl', 'arf', 'stage_arf',
                            'index', 'suppress', 'stage_suppress']:
                    self.supportedArgs.addOptArg(arg)
        except:
            logger.error("Argument not known in Setup.")
            logger.debug(traceback.format_exc())
            exit(1)

    def _delete_cred(self, realm, username):
        logger.info("function=_delete_cred ")
        r = self._delete("{}/servicesNS/nobody/irflow-splunk-app/storage/passwords/{}%3A{}%3A?output_mode=json".format(
            SPLUNK_URL, realm, username))
        return r.status_code, r.json()

    def _update_cred(self, realm, username, password):
        logger.info("function=_update_cred")
        r = self._post("{}/servicesNS/nobody/irflow-splunk-app/storage/passwords/{}%3A{}%3A?output_mode=json".format(
            SPLUNK_URL,realm, username), {"password": password})
        return r.status_code, r.json()

    def _create_cred(self, realm, username, password):
        logger.info("function=_create_cred")
        r = self._post("{}/servicesNS/nobody/irflow-splunk-app/storage/passwords?output_mode=json".format(
            SPLUNK_URL, realm, username), {'name': username, 'password': password,
                                'realm': realm})
        return r.status_code, r.json()

    def _update_evtidx(self, idxname):
        if idxname is None:
            idxname = "irflow_action"
        logger.info("function=_update_evtidx")
        r = self._post("{}/servicesNS/nobody/irflow-splunk-app/saved/eventtypes/irflow_action_index?output_mode=json".format(
            SPLUNK_URL
        ), {'search': 'index={}'.format(idxname)})
        return r.status_code, r.json()

    def _get_evtidx(self):
        logger.info("function=_get_evtidx")
        r = self._get(
            "{}/servicesNS/nobody/irflow-splunk-app/saved/eventtypes/irflow_action_index?output_mode=json".format(
                SPLUNK_URL
            ))
        return r.status_code, r.json()

    def _post(self, url, data):
        try:
            return requests.post(url=url, data=data, headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                          verify=False)
        except Exception, e:
            logger.error("function=_post error={}".format(e))

    def _delete(self, url):
        try:
            return requests.delete(url=url, headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                          verify=False)
        except Exception, e:
            logger.error("function=_delete error={}".format(e))

    def _get(self, url):
        try:
            return requests.get(url=url,
                             headers={'Authorization': 'Splunk ' + self.getSessionKey()},
                             verify=False)

        except Exception, e:
            logger.error("function=_get error={}".format(e))

    def _get_cred(self, realm, username):
        try:
            r = self._get("{}/servicesNS/nobody/irflow-splunk-app/storage/passwords/{}%3A{}%3A?output_mode=json".format(
                SPLUNK_URL, realm, username
            ))
            return r.status_code, r.json()
        except Exception, e:
            logger.error("function=_get_cred error={}".format(e))

    def handleList(self, confInfo):
        """
        handleList method: lists configurable parameters in the configuration page
        corresponds to handleractions = list in restmap.conf
        """
        try:
            logger.info("function=handleList status=initial")
            confDict = self.readConf("irflow")
            logger.debug("irflow_config.handleList: " + repr(confDict))
            sc, evt = self._get_evtidx()
            eventtype = evt['entry'][0]['content']['search'].split("=")[1]
            logger.info("action=list_evttype eventtype={}".format(eventtype))
            if confDict is not None:
                for stanza, settings in confDict.items():
                    for key, val in settings.items():
                        confInfo[stanza].append(key, val)
            config = confDict['config']
            config["index"] = eventtype
            confInfo["config"]["index"] = eventtype
            key_type = "prod"
            if "api_user" in config:
                logger.info("function=handleList action=get_production_user_credential user={}".format(
                        config["api_user"]))
                sc, cnt = self._get_cred("irflow-prod", config["api_user"])
                if sc == 200:
                    try:
                        confInfo['config']['api_key'] = cnt['entry'][0]['content']['clear_password']
                    except:
                        confInfo['config']['api_key'] = cnt['entry'][0]['content']['password']
                else:
                    confInfo['config']['api_key'] = ''
                confInfo['config']['api_key_confirm'] = confInfo['config']['api_key']
            key_type = "stage"
            if "stage_api_user" in config:
                if len(config["stage_api_user"]) > 0:
                    logger.info("function=handleList action=get_staging_user_credential user={}".format(
                        config["stage_api_user"]))
                    sc, cnt = self._get_cred("irflow-stage", config["stage_api_user"])
                    if sc == 200:
                        try:
                            confInfo['config']['stage_api_key'] = cnt['entry'][0]['content']['clear_password']
                        except:
                            confInfo['config']['stage_api_key'] = cnt['entry'][0]['content']['password']
                    else:
                        confInfo['config']['stage_api_key'] = ''
                    confInfo['config']['stage_api_key_confirm'] = confInfo['config']['stage_api_key']
        except KeyError, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.info('no user/key found: {} : line_no={} message={}'.format(key_type, exc_tb.tb_lineno, e))
        except Exception, e:
            logger.error("function=handleList error={}".format(e))
        logger.info("function=handleList status=complete")

    def handleEdit(self, confInfo):
        """
        handleEdit method: controls the parameters and saves the values 
        corresponds to handleractions = edit in restmap.conf

        """
        try:
            logger.info("function=handleEdit status=starting")
            name = self.callerArgs.id
            args = self.callerArgs

            address = self.callerArgs.data['address'][0]
            api_user = self.callerArgs.data['api_user'][0]
            api_key = self.callerArgs.data['api_key'][0]
            verify_ssl = self.callerArgs.data['verify_ssl'][0]
            debug = self.callerArgs.data['debug'][0]
            stage_address = self.callerArgs.data['stage_address'][0]
            stage_api_user = self.callerArgs.data['stage_api_user'][0]
            stage_api_key = self.callerArgs.data['stage_api_key'][0]
            stage_verify_ssl = self.callerArgs.data['stage_verify_ssl'][0]
            verbose = self.callerArgs.data['verbose'][0]
            eventtype = self.callerArgs.data['index'][0]
            suppress = self.callerArgs.data['stage_suppress'][0]
            stage_suppress = self.callerArgs.data['stage_suppress'][0]

            sc, r = self._update_evtidx(eventtype)
            if sc == 200:
                del self.callerArgs.data['index']
            else:
                logger.info("action=update_eventtype sc={} r={}".format(sc, json.dumps(r)))
            if api_user is None:
                try:
                    pass
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    logger.error("action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))
            elif len(api_user) > 0:
                try:
                    logger.info("action=edit realm=irflow-prod user={}".format(api_user))
                    sc, cnt = self._get_cred("irflow-prod", api_user)
                    if sc == 200:
                        if api_key is None:
                            # Delete credential
                            sc2, cnt2 = self._delete_cred("irflow-prod", api_user)
                            logger.info("action=delete_cred status={}".format(sc2))
                        elif api_key is not None:
                            # Update in password store via REST interface
                            sc2, cnt2 = self._update_cred("irflow-prod", api_user, api_key)
                            logger.info("action=update_cred status={}".format(sc2))
                        elif len(api_key) < 1:
                            # Delete credential
                            sc2, cnt2 = self._delete_cred("irflow-prod", api_user)
                            logger.info("action=delete_cred status={}".format(sc2))
                    else:
                        # Create in password store via REST interface (Will have no effect if the user exists)
                        # Delete credential
                        sc2, cnt2 = self._create_cred("irflow-prod", api_user, api_key)
                        logger.info("action=create_cred status={}".format(sc2))

                    config_args = {"api_user": api_user,
                                   "api_key": api_key,
                                   "address": address,
                                   "debug": debug,
                                   "protocol": "https",
                                   "verbose": 1}

                    # REMOVED FOR #26
                    # if api_key is not None:
                    #     self.irfc = IRFlowClient(config_args)
                    #     try:
                    #         version = self.irfc.get_version()
                    #     except KeyError:
                    #         raise admin.HandlerSetupException("action=get_version api_user={} version={}".format(api_user, version))
                    #     logger.info("action=get_version api_user={} version={}".format(api_user, version))
                    #     if version is None:
                    #         raise Exception("Failed to get version from {} using {}".format(address, api_user))

                except admin.HandlerSetupException, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    logger.error("action=arg_validation_fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))
                    raise e
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    logger.error("action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))
                    raise e

            logger.info("action=edit realm=irflow-stage user={}".format(stage_api_user))
            if stage_api_user is None:
                try:
                    pass
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    logger.error("action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))
            elif len(stage_api_user) > 0:
                try:
                    if stage_api_key is not None:
                        config_args = {"api_user": stage_api_user,
                                       "api_key": stage_api_key,
                                       "address": stage_address,
                                       "debug": debug,
                                       "protocol": "https",
                                       "verbose": 1}

                        # REMOVED FOR #26
                        # self.irfc = IRFlowClient(config_args)
                        # try:
                        #     version = self.irfc.get_version()
                        # except KeyError:
                        #     raise admin.HandlerSetupException(
                        #         "action=get_version stage_api_user={} version={}".format(stage_api_user, version))
                        # logger.info("action=get_version stage_api_user={} version={}".format(stage_api_user, version))
                        # if version is None:
                        #     raise Exception("Failed to get version from {} using {}".format(address, stage_api_user))

                    logger.info("action=edit realm=irflow-stage user={}".format(stage_api_user))
                    sc, cnt = self._get_cred("irflow-stage", stage_api_user)
                    if sc == 200:
                        if stage_api_key is None:
                            # Delete credential
                            sc2, cnt2 = self._delete_cred("irflow-stage", stage_api_user)
                            logger.info("action=delete_cred status={}".format(sc2))
                        elif len(stage_api_key) < 1:
                            # Delete credential
                            sc2, cnt2 = self._delete_cred("irflow-stage", stage_api_user)
                            logger.info("action=delete_cred status={}".format(sc2))
                        elif stage_api_key is not None:
                            # Update in password store via REST interface
                            sc2, cnt2 = self._update_cred("irflow-stage", stage_api_user, stage_api_key)
                            logger.info("action=update_cred status={}".format(sc2))
                    else:
                        # Create in password store via REST interface (Will have no effect if the user exists)
                        # Delete credential
                        sc2, cnt2 = self._create_cred("irflow-stage", stage_api_user, stage_api_key)
                        logger.info("action=create_cred status={}".format(sc2))
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    logger.error("action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))
                    raise e
            else:
                try:
                    logger.info("action=edit realm=irflow-stage len_stage_user={}".format(len(stage_api_user)))
                except Exception, e:
                    exc_type, exc_obj, exc_tb = sys.exc_info()
                    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
                    logger.error("action=fatal_error line={} file={}  message={}".format(exc_tb.tb_lineno, fname, e))
                    raise e

            # Fix Boolean
            if int(self.callerArgs.data['verify_ssl'][0]) == 1:
                self.callerArgs.data['verify_ssl'][0] = '1'
            else:
                self.callerArgs.data['verify_ssl'][0] = '0'

            if int(self.callerArgs.data['stage_verify_ssl'][0]) == 1:
                self.callerArgs.data['stage_verify_ssl'][0] = '1'
            else:
                self.callerArgs.data['stage_verify_ssl'][0] = '0'

            if int(self.callerArgs.data['arf'][0]) == 1:
                self.callerArgs.data['arf'][0] = '1'
            else:
                self.callerArgs.data['arf'][0] = '0'

            if int(self.callerArgs.data['stage_arf'][0]) == 1:
                self.callerArgs.data['stage_arf'][0] = '1'
            else:
                self.callerArgs.data['stage_arf'][0] = '0'

            if int(self.callerArgs.data['suppress'][0]) == 1:
                self.callerArgs.data['suppress'][0] = '1'
            else:
                self.callerArgs.data['suppress'][0] = '0'

            if int(self.callerArgs.data['stage_suppress'][0]) == 1:
                self.callerArgs.data['stage_suppress'][0] = '1'
            else:
                self.callerArgs.data['stage_suppress'][0] = '0'

            if int(self.callerArgs.data['debug'][0]) == 1:
                self.callerArgs.data['debug'][0] = '1'
            else:
                self.callerArgs.data['debug'][0] = '0'

            if int(self.callerArgs.data['verbose'][0]) == 1:
                self.callerArgs.data['verbose'][0] = '1'
            else:
                self.callerArgs.data['verbose'][0] = '0'

            # Fix Nulls
            for key in self.callerArgs.data.keys():
                if self.callerArgs.data[key][0] is None:
                    self.callerArgs.data[key][0] = ''

                # Strip trailing and leading whitespace
                self.callerArgs.data[key][0] = self.callerArgs.data[key][0].strip()
            logger.info("function=handleEdit status=complete")

            self.callerArgs.data['api_key'] = 'MASKED'
            if self.callerArgs.data['api_user'][0] == '':
                self.callerArgs.data['api_key'] = ''
            self.callerArgs.data['stage_api_key'] = 'MASKED'
            logger.info("action=masking_stage user={}".format(self.callerArgs.data['stage_api_user'][0]))
            if self.callerArgs.data['stage_api_user'][0] == '':
                logger.info("action=masking_stage_zero")
                self.callerArgs.data['stage_api_key'] = ''
            self.writeConf('irflow', 'config', self.callerArgs.data)

        except admin.HandlerSetupException, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error(
                "type={} action=arg_validation_fatal_error line={} file={}  message={}".format(type(e), exc_tb.tb_lineno, fname, e))
            raise e
        except Exception, e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            logger.error("action=handleEdit_fatal_error type={} line={} file={}  message={}".format(type(e), exc_tb.tb_lineno, fname, e))
            raise e


# initialize the handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
