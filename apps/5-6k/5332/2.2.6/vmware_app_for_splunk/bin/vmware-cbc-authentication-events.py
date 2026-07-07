# - VMware Alert Inputs
#     - Use this page to configure inputs that will pull alerts using the Carbon Black Cloud APIs. If you configure alert input on this page do not also configure alerts using AWS. Doing so may result in duplicate events.
#     - Ref: `CBC Alerts API <https://developer.carbonblack.com/reference/carbon-black-cloud/platform/latest/alerts-api/#alert-search>`_
#     - ``Name``: The generic name this input should be named.
#     - ``Disabled``: This is a checkbox if the input is disabled.
#     - ``Severity``: This is the minimum severity that will be pulled from the API
#     - ``Type``: The Types of alerts to pull from the API.
#     - ``API Configuration``: The API Configuration API Key to use for the API authorization.
#     - ``Proxy``: The proxy configuration, if needed.
#     - ``Lookback (days)``: The number of historical days to pull from the API.
#     - ``Index``: The Splunk Index in which to store the data
#     - ``Interval``: The frequency (in seconds) that the API should poll for data. Range: 60-86400
#     - ``Query``: The Carbon Black Cloud compatible query to limit the alert results.
import json
import logging as logger
import sys
import os
from datetime import datetime
from VMWUtilities import KennyLoggins
from vmware_cbc_client import VmwareCBCModularInput
from splunk.appserver.mrsparkle.lib.util import make_splunkhome_path
import multiprocessing.dummy as mp
from pathlib import Path
from vmware_paths import __app_name__
from cbc_sdk.enterprise_edr.auth_events import AuthEvent

_input_name = Path(__file__).stem
__author__ = 'ksmith'
_MI__app_name__ = 'VMWare Security Authentication Events Modular Input'
_SPLUNK_HOME = make_splunkhome_path([""])
sys.path.insert(0, make_splunkhome_path(["etc", "apps", __app_name__, "lib"]))
kl = KennyLoggins()
log = kl.get_logger(__app_name__, _input_name, logger.INFO)


class SplunkAuthEvent(AuthEvent):

    def __init__(self,
                 cb,
                 model_unique_id=None,
                 initial_data=None,
                 force_init=False,
                 full_doc=False):
        super(AuthEvent, self).__init__(cb,
                                        model_unique_id=model_unique_id,
                                        initial_data=initial_data,
                                        force_init=force_init,
                                        full_doc=full_doc)

    def to_json(self):
        lines = {}
        for attr in sorted(self._info):
            try:
                val = str(self._info[attr])
            except UnicodeDecodeError:
                val = repr(self._info[attr])
            lines[attr] = val
        return lines


class VmwareCBCAuthEventsInput(VmwareCBCModularInput):
    def __init__(self, **kwargs):
        VmwareCBCModularInput.__init__(self, **kwargs)

    def _get_auth_events_threaded(self, num, x):
        try:
            self.log.debug(
                "action=found_authentication_event num={}".format(num))
            evt = self._process_evt_ips(x.to_json())
            self.print_event(json.dumps(evt), time_field="device_timestamp")
        except Exception as e:
            self._catch_error(e)

    def get_authentication_events(self):
        try:
            self.log.debug("action=starting_modular_input_ingest")
            oldst = self.sourcetype()
            tenant = self.get_config("tenant")
            chkpnt_name = "vmware-cbc-{}_org-{}_auth-events.txt".format(
                tenant.get("guid"), tenant.get("org_key"))
            lb = self.get_config("lookback")
            config = self.get_config()
            self.log.info(self.logobj(
                {"action": "input_configurations",
                 **{x: config[x] for x in config if x not in ["session_key", "api_key_secret"]}}))
            self.log.debug(
                "action=evaluating_lookback lookback={} lookback_type={}".format(lb, type(lb)))
            if int(lb) > 0:
                self.log.debug(
                    "action=evaluating_lookback new_lookback={}".format((int(lb) * 1440)))
                self.checkpoint_default_lookback(new_time=(int(lb) * 1440))
            chkpnt = self.get_checkpoint(chkpnt_name)
            self.sourcetype("vmware:cbc:authentication_events")
            self.log.warning(f'action="got_checkpoint" checkpoint={json.dumps(chkpnt)}')
            start = "{}Z".format(datetime.utcfromtimestamp(chkpnt).isoformat())
            end = "{}Z".format(datetime.utcnow().isoformat())
            self.log.info("action=calling_endpoint status=start "
                          f'start="{start}" start_type="{type(start)}" end="{end}" end_type="{type(end)}" '
                          f' checkpoint="{chkpnt}"')

            auth_events = self.cb.select(SplunkAuthEvent).where("auth_username:*").set_time_range(start=start, end=end)
            p = mp.Pool(10)
            matrix = [(num, result) for num, result in enumerate(auth_events)]
            p.starmap(self._get_auth_events_threaded, matrix)
            p.close()
            p.join()
            self.log.info("action=calling_endpoint status=end")
            self.sourcetype(oldst)
            if len(auth_events) > 0:
                self.log.info(
                    "action=saving_checkpoint items_found={}".format(len(auth_events)))
                self.set_checkpoint(chkpnt_name)

            else:
                self.log.warning("action=saving_checkpoint "
                                 "msg='not saving checkpoint in case there was a communication error' "
                                 "start={} items_found={}".format(start, len(auth_events)))
        except Exception as e:
            self._catch_error(e)


modular_input = VmwareCBCAuthEventsInput(app_name=__app_name__, scheme={
    "title": "VMWare CBC Authentication Events",
    "description": "Provides a view into VMWare CBC Authentication Events.",
    "args": [
        {"name": "guid",
         "description": "distinct guid",
         "title": "GUID",
         "required": True
         },
        {"name": "input_name",
         "description": "descriptive name",
         "title": "Name",
         "required": True
         },
        {"name": "lookback",
         "description": "how many days to lookback on initial ingest",
         "title": "Lookback",
         "required": True
         },
        {"name": "credential_guid",
         "description": "The tenant guid for authentication.",
         "title": "Tenant Guid",
         "required": True
         }
    ]
})


def run():
    log.info(f"action=start_modular_input name={_input_name} path={sys.path}")
    modular_input.set_logger(log)
    modular_input.start()
    try:
        modular_input.setup_cb()
        modular_input.sourcetype("vmware:cbc:informational")
        modular_input.source("vmware:cbc:input:{}".format(modular_input.get_config("guid")))
        # modular_input.print_event(json.dumps(modular_input.get_config()))
        # UNCOMMENT THIS OUT TO ENABLE additional debug information about the API configuration.
        # modular_input.print_event(json.dumps(tmp_mi_config))
        modular_input.get_authentication_events()
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        error_msg = " " \
                    "error_message=\"{}\" " \
                    "error_type=\"{}\" " \
                    "error_arguments=\"{}\" " \
                    "error_filename=\"{}\" " \
                    "error_line_number=\"{}\" " \
                    "input_guid=\"{}\" " \
                    "input_name=\"{}\" " \
            .format(str(e), type(e), "{}".format(e), fname, exc_tb.tb_lineno, modular_input.get_config("guid"),
                    modular_input.get_config("input_name"))
        log.error("{}".format(error_msg))
    finally:
        modular_input.stop()


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == "--scheme":
            modular_input.scheme()
        elif sys.argv[1] == "--validate-arguments":
            modular_input.validate_arguments()
        elif sys.argv[1] == "--test":
            print('No tests for the scheme present')
        else:
            print('You giveth weird arguments')
    else:
        run()

    sys.exit(0)
