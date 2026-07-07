import splunk.admin as admin
import splunk.rest as rest
import splunk.entity as en
import json
import os
import io
import re
import sys
import logger_manager as log

try:
    import configparser
except ImportError:
    import ConfigParser as configparser

if sys.version_info < (3, 0, 0):
    from urllib import quote
else:
    from urllib.parse import quote

APPNAME = os.path.abspath(__file__).split(os.sep)[-3]
APP_DIR_PATH = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

_LOGGER = log.get_logger("apic_setup")


class ConfigApp(admin.MConfigHandler):
    """Configuration Handler."""

    def setup(self):
        """Set up supported arguments."""
        if self.requestedAction == admin.ACTION_EDIT:
            for arg in ["cisco_aci_inputs_json", "cisco_aci_show_inputs"]:
                self.supportedArgs.addOptArg(arg)

    def handleList(self, confInfo):
        """When setup page loads fetch all inputs and return to UI."""
        inputs = self.getInputs()
        confInfo["cisco_aci_data_inputs"].append("cisco_aci_inputs_json", json.dumps(inputs))
        confInfo["cisco_aci_data_inputs"].append("cisco_aci_show_inputs", "To avoid warning on Splunk side")

    def handleEdit(self, confInfo):
        """When user save updated inputs, save those back to inputs.conf."""
        if self.callerArgs.data["cisco_aci_show_inputs"][0] == "0":
            return
        try:
            inputs = json.loads(self.callerArgs.data["cisco_aci_inputs_json"][0])
        except ValueError as e:
            _LOGGER.error("Error while decoding. " + str(e))
        except Exception as e:
            _LOGGER.error("Error: " + str(e))
        for stanza, input in list(inputs.items()):
            arguments = stanza
            if "mso" in arguments:
                script_path = os.path.join("$SPLUNK_HOME", "etc", "apps", APPNAME, "bin", "collect_mso.py",)
            else:
                script_path = os.path.join("$SPLUNK_HOME", "etc", "apps", APPNAME, "bin", "collect.py")
            stanza = script_path + " -" + stanza
            if input["status"] == "edited" and self.validate_arg(arguments):
                _LOGGER.info("editing - " + str(input))
                self.editInputStanza(stanza, input)
            elif input["status"] == "removed" and self.validate_arg(arguments):
                _LOGGER.info("removing - " + str(input))
                self.removeInputStanza(stanza)
            elif input["status"] == "added" and self.validate_arg(arguments):
                _LOGGER.info("adding - " + str(input))
                self.addInputStanza(stanza, input)

        # Reloading scripted inputs
        try:
            en.getEntities(
                "data/inputs/script/_reload", sessionKey=self.getSessionKey(), namespace=APPNAME, owner="admin",
            )
            _LOGGER.debug("Refreshing scripted inputs")
        except Exception as e:
            _LOGGER.error("Error while refreshing scripted input after change. " + str(e))

    def validate_arg(self, arguments):
        """Validate the stanza which contains the classes provided in Arguments field of Input Setup."""
        valid_arg_regex = re.compile(r"^[\w\s-]+$")
        valid_arg = re.search(valid_arg_regex, arguments)
        if not valid_arg:
            _LOGGER.error("Invalid Class Names Provided in Arguments")
            raise admin.ArgValidationException(
                "CISCO_ACI_SETUP-INPUT_ERROR-xxx: Please Provide Valid Classes in Arguments"
            )
        return valid_arg

    def getInputs(self):
        """
        Fetch all input stanza present for scripted input: script://$SPLUNK_HOME/etc/apps/TA_cisco-ACI/bin/collect.py.

        return : None
        """
        inputs = {}
        confDict = self.readConfCtx("inputs")
        script_path = os.path.join("script://$SPLUNK_HOME", "etc", "apps", "TA_cisco-ACI", "bin", "collect.py")
        mso_script_path = os.path.join("script://$SPLUNK_HOME", "etc", "apps", "TA_cisco-ACI", "bin", "collect_mso.py",)
        if confDict != None:
            for stanza, settings in list(confDict.items()):
                if stanza.startswith(script_path) or stanza.startswith(mso_script_path):
                    stanza_elements = stanza.split(" ")  # 0 - script name, 1 - type, other arguments in the command
                    input_type = stanza_elements[1].lstrip("-")
                    input_arguments = " ".join(stanza_elements[2:])

                    new_stanza = input_type
                    for variable in stanza_elements[2:]:
                        new_stanza = new_stanza + " " + variable
                    input_el = {
                        "type": input_type,
                        "arguments": input_arguments,
                        "disabled": settings.get("disabled", ""),
                        "interval": settings.get("interval", ""),
                        # Other things like index, sourcetype, host, username, etc.
                        "status": "old",
                    }
                    inputs[new_stanza] = input_el
        return inputs

    def removeStanzaWithConfigParser(self, stanza_without_script_prefix):
        """
        Remove stanza from local and default inputs.conf via ConfigParser.

        param stanza_without_script_prefix: stanza without script:// prefix
        return : None
        """
        stanza = "script://" + str(stanza_without_script_prefix)
        try:
            input_local = configparser.ConfigParser()
            input_local.optionxform = str
            local_path = os.path.join(APP_DIR_PATH, "local", "inputs.conf")
            try:
                input_local.read(local_path)
            except Exception:
                with io.open(local_path, "r", encoding="utf_8_sig") as local_file:
                    input_local.readfp(local_file)

            _LOGGER.debug("local inputs: " + str(input_local.sections()))
            if input_local.has_section(stanza):
                input_local.remove_section(stanza)
                _LOGGER.debug("local inputs: (after removing section) " + str(input_local.sections()))
                with open(local_path, "w") as configfile:
                    input_local.write(configfile)
            else:
                _LOGGER.error("No section found in local/inputs.conf for stanza: " + str(stanza))

            input_default = configparser.ConfigParser()
            input_default.optionxform = str
            default_path = os.path.join(APP_DIR_PATH, "default", "inputs.conf")
            try:
                input_default.read(default_path)
            except Exception:
                with io.open(default_path, "r", encoding="utf_8_sig") as default_file:
                    input_default.readfp(default_file)

            _LOGGER.debug("default inputs: " + str(input_default.sections()))
            if input_default.has_section(stanza):
                input_default.remove_section(stanza)
                _LOGGER.debug("default inputs (after removing section): " + str(input_default.sections()))
                with open(default_path, "w") as configfile:
                    input_default.write(configfile)

        except Exception as e:
            _LOGGER.error('Error while removing stanza="' + str(stanza) + '" with ConfigParser : ' + str(e))

    def removeInputStanza(self, stanza):
        """
        Remove stanza (/servicesNS/nobody/search/data/inputs/script/stanza DELETE).

        param stanza: stanza to be removed
        return : None
        """
        try:
            encoded_stanza = quote(stanza, safe="")
            rest.simpleRequest(
                "/servicesNS/nobody/" + APPNAME + "/data/inputs/script/" + encoded_stanza,
                sessionKey=self.getSessionKey(),
                method="DELETE",
                raiseAllErrors=True,
            )
            _LOGGER.info('Successfully removed input stanza "' + str(stanza))
        except Exception:
            _LOGGER.error(
                'Unable to remove default input with rest call, removing via ConfigParser. stanza="' + str(stanza) + '"'
            )
            self.removeStanzaWithConfigParser(stanza)

    def addInputStanza(self, stanza, parameters):
        """
        Add stanza (/servicesNS/nobody/search/data/inputs/script/stanza POST).

        param stanza: stanza to be added
        param parameters: input parameters
        return : None
        """
        sourcetype = self.get_sourcetype(parameters["type"])
        postargs = {
            "name": stanza,
            "interval": parameters["interval"],
            "disabled": parameters["disabled"],
            "sourcetype": sourcetype,
            "passAuth": "admin",
        }
        try:
            rest.simpleRequest(
                "/servicesNS/nobody/" + APPNAME + "/data/inputs/script/",
                sessionKey=self.getSessionKey(),
                method="POST",
                getargs={"output_mode": "json"},
                postargs=postargs,
                raiseAllErrors=True,
            )
            _LOGGER.info('Successfully added input stanza "' + str(stanza))
        except Exception as e:
            _LOGGER.error('Error while adding input stanza "' + str(stanza) + '" - ' + str(e))

    def editInputStanza(self, stanza, parameters):
        """
        Update stanza (/servicesNS/nobody/search/data/inputs/script/stanza POST).

        param stanza: stanza to be updated
        param parameters: input parameters
        return : None
        """
        postargs = {
            "interval": parameters["interval"],
            "disabled": parameters["disabled"],
        }
        try:
            encoded_stanza = quote(stanza, safe="")
            rest.simpleRequest(
                "/servicesNS/nobody/" + APPNAME + "/data/inputs/script/" + encoded_stanza,
                sessionKey=self.getSessionKey(),
                method="POST",
                getargs={"output_mode": "json"},
                postargs=postargs,
                raiseAllErrors=True,
            )
            _LOGGER.info('Successfully updated input stanza "' + str(stanza))
        except Exception as e:
            _LOGGER.error('Error while updating input stanza "' + str(stanza) + '" - ' + str(e))

    def get_sourcetype(self, input_type):
        """
        Return sourcetype mapped with input_type.

        param input_type: Type of input
        return : Sourcetype mapped with input_type
        """
        # Exceptional scenarios about sourcetypes
        if input_type == "classInfo" or input_type == "microsegment":
            sourcetype = "cisco:apic:class"
        elif input_type == "fex":
            sourcetype = "cisco:apic:health"
        elif input_type == "mso":
            sourcetype = "cisco:mso"
        # Other conditions
        else:
            sourcetype = "cisco:apic:" + str(input_type)

        return sourcetype


# Initialize handler
admin.init(ConfigApp, admin.CONTEXT_NONE)
