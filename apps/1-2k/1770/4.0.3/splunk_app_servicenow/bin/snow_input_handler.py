__author__ = 'strong'

import base_handler as base
import util
import splunk.admin as admin
import snow_input_manager as sim

OPTIONAL_ARGS = ["exclude","since_when","duration","timefield","index","host","disabled"]
logger = util.getLogger()
ARG_TARGET = "target"

class SnowInputHandler(base.BaseHandler):
    def setup(self):
        self.supportedArgs.addReqArg(ARG_TARGET)
        for key in OPTIONAL_ARGS:
            self.supportedArgs.addOptArg(key)

    def handleCreate(self, confInfo):
        input_manager = self._get_input_manager()
        props = self._build_args(self.callerArgs)
        input_manager.create(**props)

    def handleEdit(self, confInfo):
        input_manager = self._get_input_manager()
        snow_input = input_manager.get_by_name(self.callerArgs.id)
        if "disabled" in self.callerArgs and snow_input.content["disabled"]!=self.callerArgs["disabled"][0]:
            action = self.callerArgs["disabled"][0]
            if action == "0" or action == "false" or action == "False":
                snow_input.enable()
            else:
                snow_input.disable()
            return
        else:
            props = self._build_args(self.callerArgs)
            props = {key: value for key, value in props.items() if key is not "disabled"}   #TODO enable/disable
            input_manager.update(**props)

    def handleList(self, confInfo):
        input_manager = self._get_input_manager()
        snow_inputs = input_manager.list()
        for snow_input in snow_inputs:
            entry = confInfo[snow_input.name]
            for key in OPTIONAL_ARGS:
                if key in snow_input.content:
                    entry[key] = snow_input.content[key]
            if "remove" in snow_input.links:
                entry["can_remove"] = "true"

    def handleRemove(self, confInfo):
        name = self.callerArgs.id
        input_manager = self._get_input_manager()
        input_manager.delete(name)

    def _build_args(self, callerArgs):
        props = {"name": callerArgs.id}
        for key in OPTIONAL_ARGS:
            if key in callerArgs:
                props[key] = callerArgs[key][0]
        return props

    def _get_input_manager(self):
        target = self.callerArgs[ARG_TARGET][0]
        service = self._get_ta_target_service(target)
        input_manager = sim.SnowInputManager(service)
        return input_manager

admin.init(SnowInputHandler, admin.CONTEXT_APP_ONLY)