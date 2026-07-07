#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
"""
Rest handler file for the scom servers.

* isort ignores:
- isort: skip = Should not be sorted.

* flake8 ignores:
- noqa: E401 -> Def = module imported but unused
    Reason for ignoring = This is necessary as it contains adding a path to sys.path

"""


import import_declare_test  # isort: skip # noqa: F401
import base64
import logging
import os
import subprocess

import splunk.admin as admin
import splunk_ta_ms_scom_util as scom_util
from solnlib import log
from splunktalib.common import util as common_util
from splunktalib.splunk_platform import make_splunkhome_path
from splunktaucclib.rest_handler import base
from splunktaucclib.rest_handler.error import RestError
from splunktaucclib.rest_handler.error_ctl import RestHandlerError as RH_Err
import ipaddress

common_util.remove_http_proxy_env_vars()

log.Logs.set_context()
_LOGGER = log.Logs().get_logger("splunk_ta_microsoft-scom_server_validation")


class Managementgroup(base.BaseModel):
    """REST Endpoint of Server in Splunk Add-on UI Framework."""

    endpoint = "configs/conf-microsoft_scom_servers"
    requiredArgs = {"host", "username", "password"}
    encryptedArgs = {"password"}
    cap4endpoint = ""
    cap4get_cred = ""


class ManagementgroupHandler(base.BaseRestHandler):
    def setup(self):
        # overloaded method of base.BaseRestHandler for custom changes
        if self.customAction == "_sync":
            action = admin.ACTION_EDIT if self.exist4sync else admin.ACTION_CREATE
            self.setupArgs(action)
        elif self.requestedAction in (admin.ACTION_CREATE, admin.ACTION_EDIT):
            self.setupArgs(self.requestedAction)
        if self.requestedAction in (admin.ACTION_LIST, admin.ACTION_EDIT):
            self.supportedArgs.addOptArg("--get-clear-credential--")

    def handleList(self, confInfo):
        base.BaseRestHandler.handleList(self, confInfo)
        for item in confInfo.values():
            if "host" in item:
                item["host"] = item["host"].strip("[]")

    def validateString(self, value, minLen=None, maxLen=None):
        failed = (value and minLen is not None and len(value) < minLen) or (
            value and maxLen is not None and len(value) > maxLen
        )
        return False if (not isinstance(value, str)) or failed else True

    def validateServer(self, data):

        if not ("host" in data and "username" in data and "password" in data):
            _LOGGER.error(
                "Server validation unsuccessful. Reason: Some parameters are missing."
            )
            raise Exception(
                "Server validation unsuccessful. Refer Add-on logs for detailed error."
            )

        if not (
            self.validateString(data["host"][0], minLen=1, maxLen=250)
            and self.validateString(data["username"][0], minLen=1, maxLen=250)
            and self.validateString(data["password"][0], minLen=1, maxLen=8192)
        ):
            _LOGGER.error(
                "Server validation unsuccessful. "
                "Reason: Provided parameters are not in correct format or of invalid length."
            )
            raise Exception(
                "Server validation unsuccessful. Refer Add-on logs for detailed error."
            )

        _LOGGER.info(
            "Verifying the credentials for the SCOM Server with host {} and username {}.".format(
                data["host"][0], data["username"][0]
            )
        )

        serverhost = base64.b64encode(data["host"][0].encode("utf-8")).decode()
        username = base64.b64encode(data["username"][0].encode("utf-8")).decode()
        password = base64.b64encode(data["password"][0].encode("utf-8")).decode()
        scom_dir = make_splunkhome_path(
            (["etc", "apps", "Splunk_TA_microsoft-scom", "bin"])
        )
        scom_dir = scom_dir.replace("\\", "\\\\")
        cmd = "& '{}\\server_validation.ps1' {} {} {}".format(
            scom_dir, serverhost, username, password
        )

        p = subprocess.run(
            [
                "powershell.exe",
                cmd,
            ],
            timeout=120,
            capture_output=True,
        )
        res = p.stdout.decode("utf-8").strip()
        if not res:
            res = p.stderr.decode("utf-8").strip()

        if res == "true":
            _LOGGER.info(
                "Successfully Validated the credentials for the SCOM Server with host {} and username {}.".format(
                    data["host"][0], data["username"][0]
                )
            )
            return

        _LOGGER.error("Server validation unsuccessful. Reason: {}".format(res))
        raise Exception(
            "Server validation unsuccessful. Refer Add-on logs for detailed error."
        )

    def handleCreate(self, confInfo):
        # jscpd:ignore-start
        if "host" in self.callerArgs.data and self.is_ipv6(
            self.callerArgs.data["host"][0]
        ):
            self.callerArgs.data["host"][0] = f'[{self.callerArgs.data["host"][0]}]'
            _LOGGER.info(
                f'Added the square brackets around the host: {self.callerArgs.data["host"][0]}'
            )
        if not (
            len(self.callerArgs.data.keys()) == 1
            and "--get-clear-credential--" in self.callerArgs.data
        ):
            try:
                self.validateServer(self.callerArgs.data)
            except subprocess.SubprocessError as e:
                msg = "Server validation unsuccessful. {} Exception occured".format(
                    str(type(e).__name__)
                )
                _LOGGER.error(msg)
                raise RestError("400", msg)
            except Exception as e:
                raise RestError("400", str(e))
        # jscpd:ignore-end
        base.BaseRestHandler.handleCreate(self, confInfo)

    def handleRemove(self, confInfo):
        all_in_use_managementgroup = scom_util.get_all_in_use_managementgroups(  # NOQA
            self.getSessionKey(), *self.user_app()
        )
        stanza = self.callerArgs.id
        # delete checkpoint first
        scom_ckpt_dir = make_splunkhome_path(
            (["var", "lib", "splunk", "modinputs", "scom"])
        )
        if os.path.isdir(scom_ckpt_dir):
            encode_name = self._encode_name(stanza)
            delete_file_prefix = "###{}###".format(encode_name)
            files = os.listdir(scom_ckpt_dir)
            for file in files:
                if file.startswith(delete_file_prefix):
                    file_full_path = make_splunkhome_path(
                        (["var", "lib", "splunk", "modinputs", "scom", file])
                    )
                    os.remove(file_full_path)
        base.BaseRestHandler.handleRemove(self, confInfo)

    def _encode_name(self, stanza):
        # replace "/" with "-"
        base64_name = base64.b64encode(stanza.encode("utf-8"), b"+-").decode()
        return base64_name

    def handleEdit(self, confInfo):
        # overloaded method of base.BaseRestHandler for custom changes
        try:
            self.get(self.callerArgs.id)
        except Exception as exc:
            RH_Err.ctl(-1, msgx=exc, logLevel=logging.INFO)
        # jscpd:ignore-start
        if "host" in self.callerArgs.data and self.is_ipv6(
            self.callerArgs.data["host"][0]
        ):
            self.callerArgs.data["host"][0] = f'[{self.callerArgs.data["host"][0]}]'
            _LOGGER.info(
                f'Added the square brackets around the host: {self.callerArgs.data["host"][0]}'
            )
        if not (
            len(self.callerArgs.data.keys()) == 1
            and "--get-clear-credential--" in self.callerArgs.data
        ):
            try:
                self.validateServer(self.callerArgs.data)
            except subprocess.SubprocessError as e:
                msg = "Server validation unsuccessful. {} Exception occured".format(
                    str(type(e).__name__)
                )
                _LOGGER.error(msg)
                raise RestError("400", msg)
            except Exception as e:
                raise RestError("400", str(e))
        # jscpd:ignore-end
        try:
            clear_credential = self.callerArgs.data.get("--get-clear-credential--")
            if clear_credential:
                # popping out as it doesn't get written to conf files
                self.callerArgs.data.pop("--get-clear-credential--")
            args = self.encode(self.callerArgs.data, setDefault=False)
            self.update(self.callerArgs.id, **args)
            if clear_credential:
                self.callerArgs.data["--get-clear-credential--"] = clear_credential
            self.handleList(confInfo)
        except Exception as exc:
            RH_Err.ctl(-1, exc, logLevel=logging.INFO)

    def is_ipv6(self, ipv6_address):
        try:
            ipaddress.IPv6Address(ipv6_address)
            _LOGGER.info("proxy_url contains IPv6 address.")
            return True
        except ipaddress.AddressValueError:
            _LOGGER.info(f"Not a valid IPv6 address: {ipv6_address}.")
            return False


if __name__ == "__main__":
    admin.init(
        base.ResourceHandler(model=Managementgroup, handler=ManagementgroupHandler),
        admin.CONTEXT_APP_AND_USER,
    )
