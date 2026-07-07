# Copyright 2018 ForeScout Technologies

from __future__ import absolute_import
from builtins import range
from builtins import object
import splunk
import splunk.admin as admin
import logging.handlers
import os
import os.path
import ipv6utils
import traceback

from fsct_rest_api_wrapper import FSSplunkRestApiWrapper
from fsct_exception import Error
import fsct_defaults
from six.moves import range
import six
from io import open

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path


class CredentialsValidationCodes(object):
    FAILURE, SUCCESS_UPDATE_IP_PASS, SUCCESS_UPDATE_IP, SUCCESS_UPDATE_PASS, SUCCESS_NO_UPDATE = list(range(
        5))


class IndexValidationCodes(object):
    FAILURE, SUCCESS = list(range(2))


# define a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
setup_log_filename = make_splunkhome_path(
    ['var', 'log', 'splunk', fsct_defaults.FS_TA_APP_NAME + '_setup.log'])
handler = logging.handlers.RotatingFileHandler(setup_log_filename,
                                               maxBytes=25000000, backupCount=5)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter(
    '%(asctime)s - %(filename)s:%(lineno)d - %(levelname)s - %(message)s',
    '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
logger.addHandler(handler)

class ConfigApp(admin.MConfigHandler):

    def setup(self):
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ['fsct_emip', 'fsct_password', 'fsct_index']:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        confDict = self.readConf('fsctsetup')
        if None != confDict:
            for stanza, settings in six.iteritems(confDict):
                for key, val in six.iteritems(settings):
                    if key in ['fsct_emip', 'fsct_index'] and val in [None, '']:
                        val = ''
                    confInfo[stanza].append(key, val)

    def handleEdit(self, confInfo):
        config_params = dict(self.callerArgs.data)

        logger.debug('Read EM IP from arg: %s', config_params['fsct_emip'][0])
        # We are setting the emip to its compact format if it is IPv6 before we
        # validate or anything else to ensure the compact format is used
        # on all downstream code.
        config_params['fsct_emip'][0] = self.convertIpv6ToCompactFormat(config_params['fsct_emip'][0])

        validation_result = self.validateSetupConfig(config_params)

        # raise exception if validation failed
        if validation_result[
            'cred_validation'] == CredentialsValidationCodes.FAILURE:
            raise ValueError('Credentials Validation failed.')
        elif validation_result[
            'index_validation'] == IndexValidationCodes.FAILURE:
            raise ValueError('Index Validation failed.')

        # write setup params that need to be updated, to conf file
        if validation_result[
            'cred_validation'] == CredentialsValidationCodes.SUCCESS_UPDATE_IP_PASS:
            try:
                self.updateCredentialsConfig(config_params['fsct_emip'][0],
                                             config_params['fsct_password'][0])
            except Error as err:
                logger.error('Error while updating credentials: %s', err.message)

                # raise exception to ensure that an error is displayed on the setup screen.
                raise Error(err.message)
        elif validation_result[
            'cred_validation'] == CredentialsValidationCodes.SUCCESS_NO_UPDATE:
            logger.debug('No need to update credentials.')
            del config_params['fsct_emip']
        else:
            pass

        # delete 'fsct_password' key from config params retrieved from setup page
        del config_params['fsct_password']

        # write setup fields in fsctsetup.conf file
        self.writeConf('fsctsetup', 'fsct_config', config_params)

    def updateCredentialsConfig(self, fsct_emip_in_setup, fsct_password_in_setup):

        logger.debug('Updating new credentials for EM IP: [%s]', fsct_emip_in_setup)
        # get parameters needed to call Splunk's REST APIs
        local_server = splunk.getLocalServerInfo()
        session_key = self.getSessionKey()
        splunk_rest_handle = FSSplunkRestApiWrapper(logger, local_server,session_key)
        # delete existing password from '/storage/passwords' endpoint
        if os.path.isfile(fsct_defaults.FS_SETUP_STORE_FILE):
            prev_fsct_emip_in_setup = ''
            with open(fsct_defaults.FS_SETUP_STORE_FILE, 'r') as setup_store_fh:
                prev_fsct_emip_in_setup = setup_store_fh.readline()
                logger.info('Read previous EM IP: [%s] from file: [%s]',prev_fsct_emip_in_setup,fsct_defaults.FS_SETUP_STORE_FILE)
            if len(prev_fsct_emip_in_setup):
                splunk_rest_handle.updateStoragePasswords('DELETE',
                                                          prev_fsct_emip_in_setup,
                                                          None)

            # remove the setup store file after deleting credentials from '/storage/passwords' endpoint
            os.remove(fsct_defaults.FS_SETUP_STORE_FILE)

        # store the new credentials in '/storage/passwords' endpoint
        splunk_rest_handle.updateStoragePasswords('POST', fsct_emip_in_setup,
                                                  fsct_password_in_setup)

        # store the new EM IP in the setup store file
        setup_store_fh = open(fsct_defaults.FS_SETUP_STORE_FILE, 'w+')
        setup_store_fh.write(six.text_type(fsct_emip_in_setup))
        setup_store_fh.close()

    def validateSetupConfig(self, configParams):
        logger.debug('Validating setup configuration parameters.')

        # This get call by newly setup EM info and edit.
        # So need to check at IPv6 here as well
        # configParams['fsct_emip'][0] = self.convertIpv6ToCompactFormat(configParams['fsct_emip'][0])

        fsct_emip = configParams['fsct_emip'][0]
        logger.debug('ValidateSetupConfig, EM IP is: %s', fsct_emip)

        fsct_password = configParams['fsct_password'][0]
        fsct_index = configParams['fsct_index'][0]

        ret_cred_validation = CredentialsValidationCodes.FAILURE
        ret_index_validation = IndexValidationCodes.FAILURE

        # Validate credentials fields
        if (fsct_emip in [None, '']) and (fsct_password in [None, '']):
            # both EM IP and password fields blank. Valid case. Update only index field.
            ret_cred_validation = CredentialsValidationCodes.SUCCESS_NO_UPDATE
            logger.info('Credentials validation succeeded.')
        elif (fsct_emip in [None, '']) and (fsct_password not in [None, '']):
            # EM IP is blank but password is specified. Invalid case.
            logger.error(
                'Credentials validation failed! EM IP field cannot be blank when Password field is specified')
        elif (fsct_emip not in [None, '']) and (fsct_password in [None, '']):
            # EM IP specified but password is blank.
            if (os.path.isfile(fsct_defaults.FS_SETUP_STORE_FILE)):
                prev_fsct_emip_in_setup = ''
                with open(fsct_defaults.FS_SETUP_STORE_FILE,
                          'r') as setup_store_fh:
                    prev_fsct_emip_in_setup = setup_store_fh.readline()
                    logger.info(
                        'Credentials validation: Read previous EM IP: [%s] from file: [%s]',
                        prev_fsct_emip_in_setup, fsct_defaults.FS_SETUP_STORE_FILE)
                if (len(prev_fsct_emip_in_setup)) and (
                    fsct_emip == prev_fsct_emip_in_setup):
                    # EM IP matches with existing config. Valid case.
                    ret_cred_validation = CredentialsValidationCodes.SUCCESS_NO_UPDATE
                    logger.info('Credentials validation succeeded.')
                else:
                    # EM IP doesn't match with existing config. User entered a new EM IP field but didn't specify a new password. Invalid case.
                    logger.error(
                        'Credentials validation failed! EM IP specified without providing password.')
            else:
                # No previous config store file found. It means a first-time app set up, but the user provided only EM IP. Invalid case.
                logger.error(
                    'Credentials validation failed! EM IP specified without providing password.')
        else:
            # both EM IP and password fields specified. Valid case.
            ret_cred_validation = CredentialsValidationCodes.SUCCESS_UPDATE_IP_PASS
            logger.info('Credentials validation succeeded.')

        # Validate index field
        if fsct_index not in [None, '']:
            ret_index_validation = IndexValidationCodes.SUCCESS
            logger.info('Index validation succeeded.')
        else:
            logger.error(
                'Index validation failed! Index field cannot be blank.')

        return {'cred_validation': ret_cred_validation,
                'index_validation': ret_index_validation}

    def convertIpv6ToCompactFormat(self, emip_param):
        """
        This method checks if the input value is a valid IPv6. If it is,
        a compact IPv6 value is returned. Otherwise, original value is returned
        :param emip_param: input EM string from splunk GUI
        :return: If emip_param is empty, null, or none IPv6, same value is returned.
                 if emip_param is an IPv6, the compact IPv6 format is returned.
        """

        # Init to emip
        compact_emip = emip_param
        # Skip when the IP is empty or null, skip
        # Skip when the IP is not ipv6 (FQDN, ipv4)
        if (emip_param not in [None, '']) and (ipv6utils.is_valid_ipv6_address(emip_param)):
            # Convert the ipv6 to a compat format. Reason is that the apache server
            # in CounterACT EM uses compact ipv6 format for url calls
            try:
                compact_emip = ipv6utils.get_compact_ipv6(emip_param)
            except ValueError as error:
                self.logger.debug('Not a valid ipv6 address: [%s]. Message: %s',
                                  emip_param, error.message)
            except Exception:
                self.logger.debug(
                    'Problem getting compact format for ipv6 address: [%s]. Stacktrace: %s',
                    emip_param, traceback.format_exc())

        logger.debug('IP is: %s', compact_emip)
        return compact_emip

admin.init(ConfigApp, admin.CONTEXT_NONE)
