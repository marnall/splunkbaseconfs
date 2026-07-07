import splunk.entity as entity
import splunk.admin as admin
import re
import json
import os
import sys
import time
import xml.sax.saxutils as xss
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
from splunk.clilib import cli_common as cli
import requests
import base64
import mso_session
import logger_manager

try:
    from urllib import unquote
except Exception:
    from urllib.parse import unquote

cert_lib_name = "cert_lib"
sys.path.insert(0, os.path.sep.join([os.path.dirname(__file__), cert_lib_name]))
import rsa

APPNAME = os.path.abspath(__file__).split(os.sep)[-3]

cisco_aci_server_setup_local = make_splunkhome_path(["etc", "apps", APPNAME, "local", "cisco_aci_server_setup.conf"])

logging = logger_manager.get_logger("apic_server_setup")

VERIFY_SSL = True
TIMEOUT_VAL = 180


class ConfigApp(admin.MConfigHandler):
    """Configuration Handler."""

    def setup(self):
        """Set up supported arguments."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in [
                "cisco_aci_host",
                "cisco_aci_port",
                "cisco_aci_username",
                "password",
                "is_password_authentication",
                "is_remote_user_authentication",
                "remote_user_domain_name",
                "remote_user_password",
                "is_cert_authentication",
                "cert_name",
                "cert_private_key_path",
                "cisco_mso_host",
                "cisco_mso_port",
                "cisco_mso_username",
                "is_password_authentication_mso",
                "is_remote_user_authentication_mso",
                "password_mso",
                "remote_user_domain_name_mso",
                "remote_user_password_mso",
                "configure_mso",
                "configure_apic",
                "site_details",
                "authentication_type_mso",
            ]:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """Read the initial values of the parameters from the custom conf and write them to the setup screen."""
        confDict = self.readConf("cisco_aci_server_setup")
        if None != confDict:
            for stanza, settings in list(confDict.items()):
                for key, val in list(settings.items()):
                    if (
                        key
                        in [
                            "cisco_aci_host",
                            "cisco_aci_port",
                            "cisco_aci_username",
                            "password",
                            "remote_user_domain_name",
                            "remote_user_password",
                            "cert_name",
                            "cert_private_key_path",
                            "site_details",
                        ]
                        and val is None
                    ):
                        val = ""
                    confInfo[stanza].append(key, val)
        confInfo["cisco_aci_server_setup_settings"].append("cisco_aci_show_settings", "To avoid warning on Splunk side")

    def convert_to_list(self, cisco_aci_host):
        """Return list of unique hosts provided in comma separated string."""
        cisco_aci_host_list = cisco_aci_host.split(",")
        cisco_aci_host_list = [each.strip() for each in cisco_aci_host_list if each.strip()]
        cisco_aci_host_list_unescaped = [
            str(xss.unescape(each.strip())) for each in cisco_aci_host_list if each.strip()
        ]

        unique_hosts = list(set(cisco_aci_host_list + cisco_aci_host_list_unescaped))
        return unique_hosts

    def get_configured_by_cert(self, cisco_aci_host):
        """Return list of hosts already configured by cert base authentication."""
        cisco_aci_host_list = self.convert_to_list(cisco_aci_host)
        common_host = []
        saved_host = []
        if os.path.exists(cisco_aci_server_setup_local):
            credentials = cli.readConfFile(cisco_aci_server_setup_local)
            for _, settings in list(credentials.items()):
                host = (settings.get("cisco_aci_host", "")).split(",")
                saved_host += [each.strip() for each in host if each.strip()]

            common_host += [host for host in cisco_aci_host_list if host in saved_host]

        return common_host

    def get_configured_by_pass_or_remote(self, cisco_aci_host):
        """Return lit of hosts already configured by pass or remote based auth."""
        cisco_aci_host_list = self.convert_to_list(cisco_aci_host)
        common_host = []
        saved_host = []
        try:
            entities = entity.getEntities(
                "storage/passwords",
                search="eai:acl.app=TA_cisco-ACI",
                sessionKey=self.getSessionKey(),
                count=-1,
            )
            for _, c in list(entities.items()):
                host = (c.get("realm", "")).split(",")
                saved_host += [each.strip() for each in host if each.strip()]

            common_host += [host for host in cisco_aci_host_list if host in saved_host]

            return common_host
        except Exception:
            raise admin.ArgValidationException("Failed to search for existing Cisco ACI credential in passwords.conf!")

    def configure_mso(self):
        """Configure MSO as per the authentication method selected."""
        parameter = {"is_configured": 1}
        authentication_type = str(self.callerArgs.data["authentication_type_mso"][0])

        if self.callerArgs.data["cisco_mso_host"][0] == "None":
            cisco_aci_host = ""
        else:
            cisco_aci_host = xss.escape(self.callerArgs.data["cisco_mso_host"][0])

        if self.callerArgs.data["cisco_mso_port"][0] == "None":
            cisco_aci_port = ""
        else:
            cisco_aci_port = self.callerArgs.data["cisco_mso_port"][0]

        if self.callerArgs.data["cisco_mso_username"][0] == "None":
            cisco_aci_username = ""
        else:
            cisco_aci_username = xss.escape(self.callerArgs.data["cisco_mso_username"][0])

        if self.callerArgs.data["password_mso"][0] == "None":
            password = ""
        else:
            password = self.callerArgs.data["password_mso"][0]

        if self.callerArgs.data["is_password_authentication_mso"][0] == "1":
            is_password_authentication = "1"
        else:
            is_password_authentication = "0"

        if self.callerArgs.data["is_remote_user_authentication_mso"][0] == "1":
            is_remote_user_authentication = "1"

            if self.callerArgs.data["remote_user_domain_name_mso"][0] == "None":
                remote_user_domain_name = ""
            else:
                remote_user_domain_name = xss.escape(self.callerArgs.data["remote_user_domain_name_mso"][0])

            if self.callerArgs.data["remote_user_password_mso"][0] == "None":
                remote_user_password = ""
            else:
                remote_user_password = self.callerArgs.data["remote_user_password_mso"][0]

        else:
            is_remote_user_authentication = "0"
            remote_user_password = ""
            remote_user_domain_name = ""
        # INPUT VALIDATION
        containsSlashRegex = re.compile(r".*[/\\]$")
        containsSpaceRegex = re.compile(r"\s+")
        hostnameList = cisco_aci_host.split(",")
        for hostname in hostnameList:
            invalidHostname = re.search(containsSlashRegex, hostname)
            if invalidHostname:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Hostname or IP address specified for MSO: {mso}. "
                    "Must be a valid IPv4 or IPv6 or Hostname.".format(mso=hostname)
                )

        if cisco_aci_port:
            try:
                cisco_aci_port_num = int(cisco_aci_port)
                if cisco_aci_port_num < 0 or cisco_aci_port_num > 65535:
                    raise admin.ArgValidationException(
                        "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Port specified for MSO: {mso}. "
                        "Must be in range 0-65535".format(mso=cisco_aci_host)
                    )
            except ValueError:
                raise admin.ArgValidationException(
                    "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Port specified for MSO: {mso}. "
                    "Must be a Valid Port number".format(mso=cisco_aci_host)
                )

        if is_password_authentication == "1":
            # Username: make sure it is a string with no spaces
            invalidUsername = re.search(containsSpaceRegex, cisco_aci_username)
            if not cisco_aci_username or invalidUsername:
                raise admin.ArgValidationException(
                    "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Username specified for MSO: {mso}. "
                    "Must be a string without spaces.".format(mso=cisco_aci_host)
                )
            # Password: make sure it is a string with no spaces
            invalidPassword = re.search(containsSpaceRegex, password)
            if not password or invalidPassword:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid password specified for MSO: {mso}. "
                    "Must be a string without spaces.".format(mso=cisco_aci_host)
                )

        elif is_remote_user_authentication == "1":
            # Username: make sure it is a string with no spaces
            invalidUsername = re.search(containsSpaceRegex, cisco_aci_username)
            if not cisco_aci_username or invalidUsername:
                raise admin.ArgValidationException(
                    "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Username specified for MSO: {mso}. "
                    "Must be a string without spaces.".format(mso=cisco_aci_host)
                )
            # Password: make sure it is a string with no spaces
            invalidPassword = re.search(containsSpaceRegex, remote_user_password)
            if not remote_user_password or invalidPassword:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid password specified for MSO: {mso}. "
                    "Must be a string without spaces.".format(mso=cisco_aci_host)
                )
            invalidDomainName = re.search(containsSpaceRegex, remote_user_domain_name)
            if not remote_user_domain_name or invalidDomainName:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Domain Name specified for MSO: {mso}. "
                    "Must be a string without spaces.".format(mso=cisco_aci_host)
                )

        sessionKey = self.getSessionKey()
        common_host_pass_remote = self.get_configured_by_pass_or_remote(cisco_aci_host)
        if common_host_pass_remote:
            common_host_pass_remote = [str(xss.unescape(each)) for each in common_host_pass_remote]
            raise admin.ArgValidationException(
                "TA_cisco-ACI: Cisco MSO server credential for "
                + ", ".join(common_host_pass_remote)
                + " already exists in passwords.conf (configured through Password Based or Remote Based Authentication)"
                " To re-configure the same, first remove it from local/passwords.conf, restart Splunk, and try again."
            )

        cert_common_host = self.get_configured_by_cert(cisco_aci_host)
        if cert_common_host:
            cert_common_host = [str(xss.unescape(each)) for each in cert_common_host]
            raise admin.ArgValidationException(
                "TA_cisco-ACI: Cisco MSO server credential for "
                + ", ".join(cert_common_host)
                + " already exists in cisco_aci_server_setup.conf (configured through Certificate Based Authentication)"
                " To re-configure the same, first remove it from local/cisco_aci_server_setup.conf, restart Splunk,"
                " and try again."
            )

        mso_or_nd_auth = "nd_auth" if authentication_type == "is_nd_based_authentication_id" else "mso"
        if is_password_authentication == "1":
            # Validate MSO Credentials before saving
            self.validate_mso_creds(
                host=str(cisco_aci_host),
                port=str(cisco_aci_port),
                user=str(cisco_aci_username),
                passwd=str(password),
                authentication_type=mso_or_nd_auth,
            )

            # Create Encrypted Credential in app.conf via REST API for aci
            try:
                creds = entity.getEntity("/storage/passwords/", "_new", sessionKey=sessionKey)
                creds["name"] = (
                    mso_or_nd_auth + "," + str(cisco_aci_port) + "," + str(cisco_aci_username) + "," + str(VERIFY_SSL)
                )
                creds["password"] = password
                creds["realm"] = str(cisco_aci_host)
                creds.namespace = APPNAME
                entity.setEntity(creds, sessionKey=sessionKey)

            except Exception:
                raise admin.ArgValidationException("Failed to create credential!")
            else:
                self.writeConf("app", "install", parameter)
            time.sleep(5)

        elif is_remote_user_authentication == "1":
            # Validate MSO Credentials before saving
            self.validate_mso_creds(
                host=str(cisco_aci_host),
                port=str(cisco_aci_port),
                user=str(cisco_aci_username),
                passwd=str(remote_user_password),
                authentication_type=mso_or_nd_auth,
                remote=True,
                domain=str(remote_user_domain_name),
            )

            # Create Encrypted Credential in app.conf via REST API for aci
            try:
                creds = entity.getEntity("/storage/passwords/", "_new", sessionKey=sessionKey)
                remote_username = str(remote_user_domain_name) + "\\\\" + str(cisco_aci_username)
                creds["name"] = (
                    mso_or_nd_auth + "," + str(cisco_aci_port) + "," + str(remote_username) + "," + str(VERIFY_SSL)
                )
                creds["password"] = remote_user_password
                creds["realm"] = str(cisco_aci_host)
                creds.namespace = APPNAME
                entity.setEntity(creds, sessionKey=sessionKey)
            except Exception:
                raise admin.ArgValidationException("Failed to create credential!")
            else:
                self.writeConf("app", "install", parameter)
            time.sleep(5)

    def configure_apic(self, apic_site):
        """Configure APIC as per the authentication method selected."""
        parameter = {"is_configured": 1}

        if apic_site["cisco_aci_host"][0] == "None":
            cisco_aci_host = ""
        else:
            cisco_aci_host = xss.escape(apic_site["cisco_aci_host"][0])

        if apic_site["cisco_aci_port"][0] == "None":
            cisco_aci_port = ""
        else:
            cisco_aci_port = apic_site["cisco_aci_port"][0]

        if apic_site["cisco_aci_username"][0] == "None":
            cisco_aci_username = ""
        else:
            cisco_aci_username = xss.escape(apic_site["cisco_aci_username"][0])

        if apic_site["password"][0] == "None":
            password = ""
        else:
            password = apic_site["password"][0]

        if apic_site["is_password_authentication"][0] == "1":
            is_password_authentication = "1"
        else:
            is_password_authentication = "0"

        if apic_site["is_remote_user_authentication"][0] == "1":
            is_remote_user_authentication = "1"

            if apic_site["remote_user_domain_name"][0] == "None":
                remote_user_domain_name = ""
            else:
                remote_user_domain_name = xss.escape(apic_site["remote_user_domain_name"][0])

            if apic_site["remote_user_password"][0] == "None":
                remote_user_password = ""
            else:
                remote_user_password = apic_site["remote_user_password"][0]

        else:
            is_remote_user_authentication = "0"
            remote_user_password = ""
            remote_user_domain_name = ""

        if apic_site["is_cert_authentication"][0] == "1":
            is_cert_authentication = "1"
            if apic_site["cert_name"][0] == "None":
                cert_name = ""
            else:
                cert_name = xss.escape(apic_site["cert_name"][0])

            if apic_site["cert_private_key_path"][0] == "None":
                cert_private_key_path = ""
            else:
                cert_private_key_path = apic_site["cert_private_key_path"][0]
        else:
            is_cert_authentication = "0"
            cert_private_key_path = ""
            cert_name = ""

        # INPUT VALIDATION
        containsSlashRegex = re.compile(r".*[/\\]$")
        containsSpaceRegex = re.compile(r"\s+")

        hostnameList = cisco_aci_host.split(",")
        for hostname in hostnameList:
            invalidHostname = re.search(containsSlashRegex, hostname)
            if invalidHostname:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Hostname or IP address specified for ACI device: {apic}. "
                    "Must be a valid IPv4 or IPv6 or Hostname.".format(apic=cisco_aci_host)
                )

        if cisco_aci_port:
            try:
                cisco_aci_port_num = int(cisco_aci_port)
                if cisco_aci_port_num < 0 or cisco_aci_port_num > 65535:
                    raise admin.ArgValidationException(
                        "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Port specified for ACI device: {apic}. "
                        "Must be in range 0-65535".format(apic=cisco_aci_host)
                    )
            except ValueError:
                raise admin.ArgValidationException(
                    "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Port specified for ACI device: {apic}. "
                    "Must be a Valid Port number".format(apic=cisco_aci_host)
                )

        if is_password_authentication == "1":
            # Username: make sure it is a string with no spaces
            invalidUsername = re.search(containsSpaceRegex, cisco_aci_username)
            if not cisco_aci_username or invalidUsername:
                raise admin.ArgValidationException(
                    "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Username specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )
            # Password: make sure it is a string with no spaces
            invalidPassword = re.search(containsSpaceRegex, password)
            if not password or invalidPassword:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid password specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )

        elif is_remote_user_authentication == "1":
            # Username: make sure it is a string with no spaces
            invalidUsername = re.search(containsSpaceRegex, cisco_aci_username)
            if not cisco_aci_username or invalidUsername:
                raise admin.ArgValidationException(
                    "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Username specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )
            # Password: make sure it is a string with no spaces
            invalidPassword = re.search(containsSpaceRegex, remote_user_password)
            if not remote_user_password or invalidPassword:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid password specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )
            invalidDomainName = re.search(containsSpaceRegex, remote_user_domain_name)
            if not remote_user_domain_name or invalidDomainName:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Domain Name specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )

        elif is_cert_authentication == "1":
            # Validate Certificate Name and Private Key Path
            invalidCertName = re.search(containsSpaceRegex, cert_name)
            invalidUsername = re.search(containsSpaceRegex, cisco_aci_username)
            if not cisco_aci_username or invalidUsername:
                raise admin.ArgValidationException(
                    "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Invalid Username specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )
            if not cert_name or invalidCertName:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Certificate Name specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )
            if not cert_private_key_path:
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Path of Private Key specified for ACI device: {apic}. "
                    "Must be a string without spaces.".format(apic=cisco_aci_host)
                )
            if not (os.path.exists(cert_private_key_path) and os.path.isfile(cert_private_key_path)):
                raise admin.ArgValidationException(
                    "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Path of Private Key specified for ACI device: {apic}. "
                    "Private key doesn't exists or Invalid Private key path.".format(apic=cisco_aci_host)
                )
            with open(cert_private_key_path, "r") as f:
                file_contents = f.read()
                if file_contents == "":
                    raise admin.ArgValidationException(
                        "CISCO_aci_SETUP-INPUT_ERROR-xxx: Invalid Path of Private Key specified for ACI device: {apic}."
                        " Invalid Private Key.".format(apic=cisco_aci_host)
                    )
                f.close()

        # Get session key so we can talk to REST API

        sessionKey = self.getSessionKey()

        if is_cert_authentication == "1":
            cert_common_host = self.get_configured_by_cert(cisco_aci_host)
            if cert_common_host:
                cert_common_host = [str(xss.unescape(each)) for each in cert_common_host]
                raise admin.ArgValidationException(
                    "TA_cisco-ACI: Cisco ACI server credential for "
                    + ", ".join(cert_common_host)
                    + " already exists in cisco_aci_server_setup.conf (configured through Certificate Based "
                    "Authentication). To re-configure the same, first remove it from local/cisco_aci_server_setup.conf,"
                    " restart Splunk, and try again."
                )

            common_host_pass_remote = self.get_configured_by_pass_or_remote(cisco_aci_host)
            if common_host_pass_remote:
                common_host_pass_remote = [str(xss.unescape(each)) for each in common_host_pass_remote]
                raise admin.ArgValidationException(
                    "TA_cisco-ACI: Cisco ACI server credential for "
                    + ", ".join(common_host_pass_remote)
                    + " already exists in passwords.conf (configured through Password Based or Remote Based "
                    "Authentication). To re-configure the same, first remove it from local/passwords.conf, "
                    "restart Splunk, and try again."
                )

            self.validate_apic_cert(
                host=cisco_aci_host,
                port=cisco_aci_port,
                user=cisco_aci_username,
                cert_name=cert_name,
                private_key=file_contents,
            )

            cred = dict()
            cred["cisco_aci_host"] = cisco_aci_host
            cred["cisco_aci_port"] = cisco_aci_port
            cred["cisco_aci_username"] = cisco_aci_username
            cred["password"] = password
            cred["cisco_aci_ssl"] = str(VERIFY_SSL)
            cred["is_password_authentication"] = is_password_authentication
            cred["is_cert_authentication"] = is_cert_authentication
            cred["cert_name"] = cert_name
            cred["cert_private_key_path"] = cert_private_key_path
            cred["is_remote_user_authentication"] = is_remote_user_authentication
            cred["remote_user_domain_name"] = remote_user_domain_name
            cred["remote_user_password"] = remote_user_password

            self.writeConf(
                "cisco_aci_server_setup",
                "cisco_aci_server_setup_settings," + cisco_aci_host,
                cred,
            )
            self.writeConf("app", "install", parameter)

        else:
            common_host_pass_remote = self.get_configured_by_pass_or_remote(cisco_aci_host)
            if common_host_pass_remote:
                common_host_pass_remote = [str(xss.unescape(each)) for each in common_host_pass_remote]
                raise admin.ArgValidationException(
                    "TA_cisco-ACI: Cisco ACI server credential for "
                    + ", ".join(common_host_pass_remote)
                    + " already exists in passwords.conf (configured through Password Based or Remote Based "
                    "Authentication). To reconfigure the same, first remove it from local/passwords.conf, "
                    "restart Splunk, and try again."
                )

            cert_common_host = self.get_configured_by_cert(cisco_aci_host)
            if cert_common_host:
                cert_common_host = [str(xss.unescape(each)) for each in cert_common_host]
                raise admin.ArgValidationException(
                    "TA_cisco-ACI: Cisco ACI server credential for "
                    + ", ".join(cert_common_host)
                    + " already exists in cisco_aci_server_setup.conf (configured through Certificate Based "
                    "Authentication). To re-configure the same, first remove it from local/cisco_aci_server_setup.conf,"
                    " restart Splunk, and try again."
                )
            if is_password_authentication == "1":
                # Validate the credentials before saving.
                self.validate_apic_creds(
                    host=str(cisco_aci_host),
                    port=str(cisco_aci_port),
                    user=str(cisco_aci_username),
                    passwd=str(password),
                )

                # Create Encrypted Credential in app.conf via REST API for aci
                try:
                    creds = entity.getEntity("/storage/passwords/", "_new", sessionKey=sessionKey)
                    creds["name"] = (
                        "apic," + str(cisco_aci_port) + "," + str(cisco_aci_username) + "," + str(VERIFY_SSL)
                    )
                    creds["password"] = password
                    creds["realm"] = str(cisco_aci_host)
                    creds.namespace = APPNAME
                    entity.setEntity(creds, sessionKey=sessionKey)
                except Exception:
                    raise admin.ArgValidationException("Failed to create credential!")
                else:
                    self.writeConf("app", "install", parameter)
                time.sleep(5)

            elif is_remote_user_authentication == "1":
                # Validate the credentials before saving.
                self.validate_apic_creds(
                    host=str(cisco_aci_host),
                    port=str(cisco_aci_port),
                    user=str(cisco_aci_username),
                    passwd=str(remote_user_password),
                    remote=True,
                    domain=str(remote_user_domain_name),
                )

                # Create Encrypted Credential in app.conf via REST API for aci
                try:
                    creds = entity.getEntity("/storage/passwords/", "_new", sessionKey=sessionKey)
                    remote_username = str(remote_user_domain_name) + "\\\\" + str(cisco_aci_username)
                    creds["name"] = "apic," + str(cisco_aci_port) + "," + str(remote_username) + "," + str(VERIFY_SSL)
                    creds["password"] = remote_user_password
                    creds["realm"] = str(cisco_aci_host)
                    creds.namespace = APPNAME
                    entity.setEntity(creds, sessionKey=sessionKey)
                except Exception:
                    raise admin.ArgValidationException("Failed to create credential!")
                else:
                    self.writeConf("app", "install", parameter)
                time.sleep(5)

    def validate_apic_creds(self, host, port, user, passwd, remote=None, domain=None):
        """Validate the Pass and Remote auth credentials for APIC."""
        msgs = []
        msg = None
        hosts = host.split(",")
        session = requests.Session()
        for host in hosts:
            host = host.strip()
            if port:
                host = "{}:{}".format(host, port)
            if remote:
                user = "apic#{}\\\\{}".format(domain, user)
            try:
                login_url = "https://{}/api/aaaLogin.json".format(host)
                data = {"aaaUser": {"attributes": {"name": user, "pwd": passwd}}}
                logging.info("Making an API call to the url %s.", login_url)

                resp = session.post(login_url, data=json.dumps(data), verify=VERIFY_SSL, timeout=TIMEOUT_VAL)
                if not resp.ok:
                    try:
                        msg = resp.json().get("imdata", [{}])[0].get("error", {}).get("attributes", {}).get("text")
                        if not msg:
                            msg = "{}. {}".format(
                                resp.json().get("message"), "May be you are configuring MSO in APIC tab."
                            )
                    except Exception:
                        pass
                    resp.raise_for_status()
                else:
                    logging.info("Successfully received the response for the url %s.", login_url)
            except Exception as e:
                m = "Could not login with provided credentials for APIC {}. Error: {}. Message: {}".format(
                    str(host), str(e), msg
                )
                msgs.append(m)
        if msgs:
            raise admin.ArgValidationException("{}".format("\n Error: ".join(msgs)))

    def validate_apic_cert(self, host, port, user, cert_name, private_key):
        """Validate signature based auth for APIC."""
        msgs = []
        msg = None
        try:
            private_key = rsa.PrivateKey.load_pkcs1(private_key)
            session = requests.Session()
            info_url = "/api/node/mo/info.json"
            cookie = self.create_cookie(info_url, user, cert_name, private_key)
        except Exception as e:
            raise admin.ArgValidationException(
                "Error while loading RSA Private key for APIC : {}. Error: {}.".format(str(host), str(e))
            )
        hosts = host.split(",")
        for host in hosts:
            host = host.strip()
            if port:
                host = "{}:{}".format(host, port)
            try:
                get_url = "https://{}{}".format(host, info_url)
                logging.info("Making an API call to the url %s.", get_url)

                resp = session.get(get_url, cookies=cookie, verify=VERIFY_SSL, timeout=TIMEOUT_VAL)
                if not resp.ok:
                    try:
                        msg = resp.json().get("message")  # will get message if MSO
                        if msg:
                            msg = "{}. {}".format(msg, "May be you are configuring MSO in APIC tab.")
                        else:
                            msg = resp.json().get("imdata", [{}])[0].get("error", {}).get("attributes", {}).get("text")
                    except Exception:
                        pass
                    resp.raise_for_status()
                else:
                    logging.info("Successfully received the response for the url %s.", get_url)
            except Exception as e:
                m = "Certificate authentication failed for APIC {}. ".format(str(host))
                m += "Please check all settings are correct. Error: {}. Message: {}".format(str(e), msg)
                msgs.append(m)

        if msgs:
            raise admin.ArgValidationException("{}".format("\n Error: ".join(msgs)))

    def create_cookie(self, info_url, user, cert_name, private_key):
        """Create X509 header for cert based auth."""
        info_url = unquote(info_url)
        cert_dn = "uni/userext/user-{}/usercert-{}".format(user, cert_name)
        payload = "{}{}".format("GET", info_url)

        payload = payload.encode("utf-8")
        signature = base64.b64encode(rsa.sign(payload, private_key, "SHA-256"))

        if sys.version_info >= (3, 0, 0):
            signature = signature.decode("utf-8")

        cookie = {
            "APIC-Request-Signature": signature,
            "APIC-Certificate-Algorithm": "v1.0",
            "APIC-Certificate-Fingerprint": "fingerprint",
            "APIC-Certificate-DN": cert_dn,
        }
        return cookie

    def validate_mso_creds(self, host, port, user, passwd, authentication_type, remote=None, domain=None):
        """Validate the Pass and Remote auth credentials for MSO."""
        msgs = []
        hosts = host.split(",")

        for host in hosts:
            host = host.strip()
            if port:
                host = "{}:{}".format(host, str(port))
            msoUrl = "https://{}".format(str(host))
            try:
                session = mso_session.Session(
                    msoUrl, user, passwd, domain, TIMEOUT_VAL, authentication_type, str(VERIFY_SSL), logger=logging
                )
                resp = session.login()
                if not resp.ok:
                    resp.raise_for_status()

            except Exception as e:
                m = (
                    "Could not login with provided credentials for MSO {}. Error: {}."
                    " Either you have not selected the right Authentication Type i.e (MSO or Nexus Dashboard)"
                    " for the given credentials or you are configuring APIC in MSO tab.".format(str(host), str(e))
                )
                msgs.append(m)
        if msgs:
            raise admin.ArgValidationException("{}".format("\n Error: ".join(msgs)))

    def get_verify_ssl(self):
        """Read Verify SSL value from app_setup.conf."""
        try:
            config = cli.getConfStanza("app_setup", "fetch_sites_ssl") or {}
            verify = config.get("verify_ssl", "True").upper()
            verify = True if verify in ("T", "TRUE", "Y", "YES", "1") else False
            return verify
        except Exception:
            raise admin.ArgValidationException("Could not get verify ssl value from app_setup.conf. defaulting to True")
        return True

    def handleEdit(self, confInfo):
        """After user clicks Save on setup screen, take updated parameters, normalize and save them."""
        # INIT Input fields to empty string instead of null

        global VERIFY_SSL
        error_list = []

        try:
            VERIFY_SSL = self.get_verify_ssl()
        except Exception as e:
            error_list.append(str(e))

        if self.callerArgs.data["configure_apic"][0] == "0" and self.callerArgs.data["configure_mso"] == "0":
            return

        if self.callerArgs.data["configure_mso"][0] == "1":
            try:
                self.configure_mso()
            except Exception as e:
                error_list.append(str(e))

            mso_sites = json.loads(self.callerArgs.data["site_details"][0])

            for _, site_detail in list(mso_sites.items()):
                try:
                    self.configure_apic(site_detail)
                except Exception as e:
                    error_list.append(str(e))

            if error_list:
                msg = "Error: {}".format("\n Error: ".join(error_list))
                raise admin.ArgValidationException(msg)

        if self.callerArgs.data["configure_apic"][0] == "1":
            try:
                site = self.callerArgs.data
                self.configure_apic(site)
            except Exception as e:
                error_list.append(str(e))

            if error_list:
                msg = "Error: {}".format("\n Error: ".join(error_list))
                raise admin.ArgValidationException(msg)


admin.init(ConfigApp, admin.CONTEXT_NONE)
