"""Setup script called when Save is used on App config."""
from __future__ import absolute_import
import os
import json
import re
import logging
import splunk.admin as admin
import splunk.rest
import splunk.version as ver
import splunk.entity as entity
from logging.handlers import RotatingFileHandler

APP_NAME = "TA-intsights"
SPLUNK_PASSWORD_ENDPOINT = "/servicesNS/nobody/" + APP_NAME + "/storage/passwords"

VERSION = float(re.search(r"(\d+.\d+)", ver.__version__).group(1))
MAXBYTES = 2000000

try:
    if VERSION >= 6.4:
        from splunk.clilib.bundle_paths import make_splunkhome_path
    else:
        from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
except ImportError:
    raise ImportError("Import splunk sub libraries failed\n")

log_path = make_splunkhome_path(["var", "log", "intsights"])
if not os.path.isdir(log_path):
    os.makedirs(log_path)

handler = RotatingFileHandler(
    os.path.join(
        log_path + '/intsights.log'
    ),
    maxBytes=MAXBYTES,
    backupCount=20
)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
LOGGER = logging.getLogger("intsights_setup")
LOGGER.setLevel(logging.INFO)
LOGGER.addHandler(handler)


class ConfigApp(admin.MConfigHandler):
    """Class to create a config object."""

    def setup(self):
        """Method to determine which action the use has taken."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in [
                    'ispp_name',
                    'ispp_password',
                    'tenant_name',
                    'tenant_password',
                    'intsights-HTTPS_PROXY_ADDRESS',
                    'intsights-HTTPS_PROXY_USERNAME',
                    'intsights-HTTPS_PROXY_PASSWORD'
            ]:
                self.supportedArgs.addOptArg(arg)

    def set_password(self, apitoken, apiid, account_type):
        """Method to call endpoint to set password."""
        old_username = ""
        realm = ""
        save_name = apiid
        current_password = False

        # verify username field is not blank
        if save_name:
            # check if account exists
            try:
                entities = splunk.entity.getEntities(
                    ['admin', 'passwords'],
                    namespace=APP_NAME,
                    owner='nobody',
                    sessionKey=self.getSessionKey()
                )

                if entities:
                    for title in entities:
                        if entities[title].get("realm") == "{}-{}".format(APP_NAME, account_type):
                            current_password = True
                            old_username = entities[title]['username']
                            realm = entities[title]['realm']

            except Exception as e:
                raise Exception("Could not get {} credentials from splunk. Error: {}".format(APP_NAME, e))

            # Delete entry in storage passwords if it exists
            if current_password:
                post_args = {
                    "name": old_username,
                    "output_mode": 'json'
                }

                # attempt to delete password
                try:
                    splunk_response = splunk.rest.simpleRequest(
                        SPLUNK_PASSWORD_ENDPOINT + "/" + APP_NAME + "-{}%3A{}%3A".format(account_type, old_username),
                        self.getSessionKey(),
                        postargs=post_args,
                        method='DELETE'
                    )

                    LOGGER.debug(
                        "Response code from app password end point in handleEdit " +
                        "for updating the password is :" + str(splunk_response[0]['status'])
                    )

                    LOGGER.info("Username {} was deleted since new credentials were provided".format(old_username))

                except splunk.AuthorizationFailed as ex:
                    LOGGER.exception(
                        'User don\'t have sufficient permissions in Splunk ' +
                        'to store the password. Make sure that this ' +
                        'user has admin permissions and advice with your Splunk admin' +
                        str(ex)
                    )

                    raise Exception(
                        'User don\'t have sufficient permissions in Splunk ' +
                        'to store the password. Make sure that this ' +
                        'user has admin permissions and advice with your Splunk admin' +
                        str(ex)
                    )

            # Store password into passwords.conf file
            LOGGER.debug("Password not found, setting a new password...")

            post_args = {
                "name": save_name,
                "password": apitoken,
                "realm": "{}-{}".format(APP_NAME, account_type),
                "output_mode": 'json'
            }

            # attempt to save password
            try:
                splunk_response = splunk.rest.simpleRequest(
                    SPLUNK_PASSWORD_ENDPOINT,
                    self.getSessionKey(),
                    postargs=post_args,
                    method='POST'
                )

                LOGGER.debug(
                    "response from app password end point for setting " +
                    "a new password in handleEdit is :" +
                    str(splunk_response[0]["status"])
                )

                LOGGER.info("New credentials were created for {} account".format(account_type))

            except splunk.AuthorizationFailed as ex:
                LOGGER.exception('User does not have sufficient permissions in Splunk to store the password. ' +
                                 'Make sure that this user has admin permissions and ' +
                                 'advice with your Splunk admin' +
                                 str(ex)
                                 )

                raise Exception(
                    'User does not have sufficient permissions in Splunk to store the password. ' +
                    'Make sure that this user has admin permissions and ' +
                    'advice with your Splunk admin' +
                    str(ex)
                )
        else:
            LOGGER.info("Username {} for account type {} was not found".format(save_name, account_type))

    def handleList(self, confinfo):
        """Method to list available config, if any."""
        # attempt to read rest saved configs and present to UI
        try:
            config_dict = self.readConf("intsights")
            LOGGER.debug("Config dict is : %s", json.dumps(config_dict))

            for stanza, settings in list(config_dict.items()):
                for key, val in list(settings.items()):
                    confinfo[stanza].append(key, val)

        except Exception as e:
            LOGGER.exception(
                "Exception while listing Intsights Add-on, perhaps something is wrong " +
                "with your credentials. The error was: " + str(e)
            )

            post_args = {
                'severity': 'error',
                'name': 'IntSights',
                'value': 'Error happened while listing IntSights Add-on, ' +
                         'perhaps something is wrong with your credentials. ' +
                         'The error was: ' + str(e)
            }
            splunk.rest.simpleRequest(
                '/services/messages',
                self.getSessionKey(),
                postargs=post_args
            )
            raise Exception("Error happened while listing IntSights Add-on , error was: " + str(e))

    def handleEdit(self, confinfo):
        """Method to init the edit functions of the setup page."""
        # After user clicks Save on setup screen, take updated parameters,
        # normalize them, and save them
        try:
            """add passwords to storage/passwords and delete IntSights accountID
            and API Key from being store in cleartext in intsights.conf."""
            creds_found = 1
            proxy_found = 1
            # update tenant creds
            if "tenant_name" in self.callerArgs.data.keys():
                LOGGER.info("Adding tenant password")

                self.set_password(
                    apiid=self.callerArgs.data['tenant_name'][0],
                    apitoken=self.callerArgs.data['tenant_password'][0],
                    account_type='tenant'
                )

                # delete from config object so as to not store in plaintext rest endpoint for ta
                del self.callerArgs.data['tenant_name']
                del self.callerArgs.data['tenant_password']
            else:
                creds_found = 0
                LOGGER.info("No tenant credentials were found")

            # update ispp creds
            if "ispp_name" in self.callerArgs.data.keys():
                creds_found = 1
                LOGGER.info("Adding ispp password")

                self.set_password(
                    apiid=self.callerArgs.data['ispp_name'][0],
                    apitoken=self.callerArgs.data['ispp_password'][0],
                    account_type='ispp'
                )

                # delete from config object so as to not store in plaintext rest endpoint for ta
                del self.callerArgs.data['ispp_name']
                del self.callerArgs.data['ispp_password']
            else:
                creds_found = 0
                LOGGER.info("No ispp credentials were found")

            # update proxy creds
            if "intsights-HTTPS_PROXY_ADDRESS" in self.callerArgs.data.keys():
                creds_found = 1
                LOGGER.info("Adding proxy password")

                self.set_password(
                    apiid=self.callerArgs.data['intsights-HTTPS_PROXY_USERNAME'][0],
                    apitoken=self.callerArgs.data['intsights-HTTPS_PROXY_PASSWORD'][0],
                    account_type='proxy'
                )

                # delete from config object so as to not store in plaintext rest endpoint for ta
                del self.callerArgs.data['intsights-HTTPS_PROXY_USERNAME']
                del self.callerArgs.data['intsights-HTTPS_PROXY_PASSWORD']

                # if proxy address was not entered, save it as null string
                if self.callerArgs.data['intsights-HTTPS_PROXY_ADDRESS'][0] is None:
                    self.callerArgs.data['intsights-HTTPS_PROXY_ADDRESS'] = ''

                # Always update intsights-config when setup is saved
                self.writeConf('intsights', 'intsights-config', self.callerArgs.data)
            else:
                proxy_found = 0
                LOGGER.info("No proxy credentials were found")

            # check if we did anything and update logs
            if creds_found == 1 or proxy_found == 1:
                LOGGER.info("Intsight's Add-on setup was successful")
            else:
                LOGGER.info("Intsight's Add-on setup was not successful")

        except Exception as e:

            LOGGER.exception(
                "Exception while setting up Intsights Add-on, perhaps something is wrong " +
                "with your credentials. The error was: " + str(e)
            )

            post_args = {
                'severity': 'error',
                'name': 'IntSights',
                'value': 'Error happened while setting up IntSights Add-on, ' +
                         'perhaps something is wrong with your credentials. ' +
                         'The error was: ' + str(e)
            }
            splunk.rest.simpleRequest(
                '/services/messages',
                self.getSessionKey(),
                postargs=post_args
            )
            raise Exception("Error happened while setting up IntSights Add-on , error was: " + str(e))

    def handleReload(self, confinfo=None):
        """Handle refresh/reload of the configuration options."""


# initialize the handler
if __name__ == '__main__':
    admin.init(ConfigApp, admin.CONTEXT_APP_AND_USER)
