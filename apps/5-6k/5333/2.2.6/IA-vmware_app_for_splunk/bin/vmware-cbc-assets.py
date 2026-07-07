import json
import logging as logger
import sys
import os
from VMWUtilities import KennyLoggins
from splunk.util import normalizeBoolean
from vmware_cbc_client import VmwareCBCModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import multiprocessing.dummy as mp
from vmware_paths import __app_name__
from cbc_sdk.endpoint_standard import USBDevice
from cbc_sdk.platform import AssetGroup, Device

__author__ = "ksmith"
_MI__app_name__ = "VMWare Security Assets Modular Input"
_SPLUNK_HOME = make_splunkhome_path([""])
kl = KennyLoggins()
_input_name = "vmware-cbc-assets-modularinput"
log = kl.get_logger(__app_name__, _input_name, logger.INFO)


class VmwareCBCAssetsInput(VmwareCBCModularInput):
    _log = logger

    def __init__(self, app_name, scheme):
        try:
            VmwareCBCModularInput.__init__(self, app_name=app_name, scheme=scheme)
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            error_msg = (
                'error_message="{}" '
                'error_type="{}" '
                'error_arguments="{}" '
                'error_filename="{}" '
                'error_line_number="{}" '
                'alert_name="{}" '.format(
                    str(e),
                    type(e),
                    "{}".format(e),
                    fname,
                    exc_tb.tb_lineno,
                    _input_name,
                )
            )
            logger.fatal(error_msg)

    def get_asset_groups(self):
        try:
            old_sourcetype = self.sourcetype()
            self.dbg(action="starting_VmwareCBCAssetGroupInput")
            deployment_type = self.get_config("deployment_type", None)
            self.warn(
                action="not_setting_checkpoint",
                message="Will not Set Checkpoint for Inventory Item",
                deployment_type=deployment_type
            )
            if deployment_type and len(deployment_type) > 1:
                valid = [x for x in deployment_type.split(",") if x in ["ASSET_GROUPS", "ALL"]]
                if any(valid):
                    self.sourcetype("vmware:cbc:inventory:asset_group")
                    groups = AssetGroup.get_all_groups(self.cb)
                    self.dbg(action="received_events", number_of_groups=len(groups))
                    matrix = [(num, result) for num, result in enumerate(groups)]
                    p = mp.Pool(10)
                    p.starmap(self._get_assets_threaded, matrix)
                    p.close()
                    p.join()
                    self.sourcetype(old_sourcetype)
        except Exception as e:
            self._catch_error(e)

    def _get_assets_threaded(self, num, evt):
        self.dbg(action="processing_result", num=num)
        self.print_event(json.dumps(evt.to_json()), time_field="timestamp")

    def _get_usb_devices_threaded(self, num, evt):
        self.dbg(action="processing_result", num=num)
        self.print_event(json.dumps(evt.to_json()))

    def get_usb_devices(self):
        try:
            old_sourcetype = self.sourcetype()
            self.dbg(action="starting_VmwareCBCUSBInput")
            deployment_type = self.get_config("deployment_type", None)
            self.warn(
                action="not_setting_checkpoint",
                message="Will not Set Checkpoint for Inventory Item",
                deployment_type=deployment_type
            )
            if deployment_type and len(deployment_type) > 1:
                valid = [x for x in deployment_type.split(",") if x in ["USB_DEVICES", "ALL"]]
                if any(valid):
                    self.sourcetype("vmware:cbc:inventory:usb_device")
                    query = self.cb.select(USBDevice).set_max_rows(10000).where("1")
                    matrix = [(num, result) for num, result in enumerate(query)]
                    self.dbg(action="received_events", device_type="usb_devices", number_of_devices=len(matrix))
                    p = mp.Pool(10)
                    p.starmap(self._get_usb_devices_threaded, matrix)
                    p.close()
                    p.join()
                    self.sourcetype(old_sourcetype)
        except Exception as e:
            self._catch_error(e)

    def _get_devices_threaded(self, num, evt):
        self.dbg(action="processing_result", num=num)
        self.print_event(json.dumps(evt.to_json()), time_field="timestamp")

    def get_devices(self):
        try:
            old_sourcetype = self.sourcetype()
            self.dbg(action="starting_vmware_cbc_devices")
            self.sourcetype("vmware:cbc:inventory:device")
            deployment_type = self.get_config("deployment_type", None)
            self.warn(
                action="not_setting_checkpoint",
                message="Will not Set Checkpoint for Inventory Item",
                deployment_type=deployment_type
            )
            statuses = ["REGISTERED", "PENDING", "BYPASS"]
            restrict = self.get_config("include_deregistered", False)
            if normalizeBoolean(restrict):
                statuses.append("DEREGISTERED")
            device_scroller = self.cb.select(Device).set_status(statuses)
            if deployment_type and len(deployment_type) > 1:
                invalid_device_deployment_types = ["USB_DEVICES", "ASSET_GROUPS", "ALL", "CHROME_OS"]
                device_scroller = device_scroller.set_deployment_type([x for x in deployment_type.split(",") if x not in invalid_device_deployment_types])
            self.dbg(action="setup_scroller", devices_dict=device_scroller.__dict__, statuses=statuses)
            remaining_number = 1
            while remaining_number > 0:
                devices = device_scroller.scroll()
                remaining_number = device_scroller.num_remaining if device_scroller.num_remaining is not None else 0
                self.dbg(
                    action="received_events",
                    number_of_devices=len(devices),
                    device_type="devices",
                    remaining_number=remaining_number,
                    devices_dict=device_scroller.__dict__,
                )
                matrix = [(num, result) for num, result in enumerate(devices)]
                p = mp.Pool(10)
                p.starmap(self._get_devices_threaded, matrix)
                p.close()
                p.join()
            self.sourcetype(old_sourcetype)
        except Exception as e:
            self._catch_error(e)


modular_input = VmwareCBCAssetsInput(
    app_name=__app_name__,
    scheme={
        "title": "VMWare Assets Inventory",
        "description": "Provides a view into VMWare SBU",
        "args": [
            {
                "name": "guid",
                "description": "distinct guid",
                "title": "GUID",
                "required": True,
            },
            {
                "name": "input_name",
                "description": "descriptive name",
                "title": "Name",
                "required": True,
            },
            {
                "name": "credential_guid",
                "description": "The tenant guid for authentication.",
                "title": "Tenant Guid",
                "required": True,
            },
        ],
    },
)


def run():
    log.info(
        "action=start_modular_input name=vmware-cbc-assets path={}".format(sys.path)
    )
    modular_input.set_logger(log)
    modular_input.start()
    try:
        modular_input.setup_cb()
        modular_input.sourcetype("vmware:cbc:informational")
        modular_input.source(
            "vmware:cbc:input:{}".format(modular_input.get_config("guid"))
        )

        modular_input.get_devices()
        modular_input.get_usb_devices()
        modular_input.get_asset_groups()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = (
            " "
            'error_message="{}" '
            'error_type="{}" '
            'error_arguments="{}" '
            'error_filename="{}" '
            'error_line_number="{}" '
            'input_guid="{}" '
            'input_name="{}" '.format(
                str(e),
                type(e),
                "{}".format(e),
                fname,
                exc_tb.tb_lineno,
                modular_input.get_config("guid"),
                modular_input.get_config("input_name"),
            )
        )
        log.error("{}".format(error_msg))
    finally:
        modular_input.stop()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print("No tests for the scheme present")
        else:
            print("You giveth weird arguments")
    else:
        run()

    sys.exit(0)
