[global]

#EDR BAN HASH
action.vmware-edr-ban-hash = [0|1]
* Enable vmware-edr-ban-hash action
action.vmware-edr-ban-hash.param.hash_field = <string>
action.vmware-edr-ban-hash.param.dryrun = <bool>
action.vmware-edr-ban-hash.param._cam = <object>

# ISOLATE DEVICE
action.vmware-edr-isolate-device = [0|1]
* Enable isolate device action
action.vmware-edr-isolate-device.param.device_id_field = <string>
action.vmware-edr-isolate-device.param._cam = <object>

# UNISOLATE DEVICE
action.vmware-edr-unisolate-device = [0|1]
* Enable unisolate device action
action.vmware-edr-unisolate-device.param.device_id_field = <string>
action.vmware-edr-unisolate-device.param._cam = <object>

# KILL PROCESS
action.vmware-edr-kill-process = [0|1]
* Enable kill process action
action.vmware-edr-kill-process.param.process_field = <string>
action.vmware-edr-kill-process.param.device_id_field = <string>
action.vmware-edr-kill-process.param._cam = <object>