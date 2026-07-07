import sys
import logging
from VMWUtilities import KennyLoggins
import multiprocessing.dummy as mp
from vmware_cbc_cmd import VmwareCBCCommand
import vmware_paths
from splunklib.searchcommands import (
    Configuration,
    EventingCommand,
    Option,
    validators,
    dispatch,
)

__app_name__ = vmware_paths.__app_name__
_cmd_name = "cbcquery"
kl = KennyLoggins()

# Global Constants
_OBSERVE = "observations"
_HISTORY = "alert_history"


@Configuration()
class VMWareCBCQueryCommand(EventingCommand):
    """%(synopsis)
    ##Syntax
    %(syntax)
    ##Description
    %(description)
    """

    _action = None
    _approved_actions = [_OBSERVE, _HISTORY]
    _results = []
    _log = None
    _cbc_client = None

    alert_id = Option(
        doc="""
            **Syntax:** **alert_id=***<field>*
            **Description:** Name of the field that holds the alert_id""",
        require=False,
        validate=validators.Fieldname(),
    )

    org_key = Option(
        doc="""
            **Syntax:** **org_key=***<field>*
            **Description:** Name of the field that holds the org key""",
        require=False,
        validate=validators.Fieldname(),
    )

    def _get_observations(self, evt, alert_id_field, org_key_field):
        try:
            org_key = evt[org_key_field]
            alert_id = evt[alert_id_field]
            self._log.debug("action=performing_threaded_action org_key={}".format(org_key))
            obs_details = self._cbc_client.get_alert_observations(alert_id, org_key)
            for idx, at in enumerate(obs_details):
                at["observation_seq_num"] = idx
                self._results.append(at)
        except Exception as e:
            self._log.error(f"action=performing_api_call exception={e}")
            evt["error"] = "{}: {}".format(type(e), e)
            self._results.append(evt)

    def _get_history(self, evt, alert_id_field, org_key_field):
        try:
            org_key = evt[org_key_field]
            alert_id = evt[alert_id_field]
            self._log.debug("action=performing_threaded_action org_key={}".format(org_key))
            alert_history = self._cbc_client.get_alert_history(alert_id, org_key)
            self._log.debug(f"action=performed_api_call alert_history={alert_history}")
            [self._results.append(at) for at in alert_history]
        except Exception as e:
            self._log.error(f"action=performing_api_call exception={e}")
            evt["error"] = "{}: {}".format(type(e), e)
            self._results.append(evt)

    def transform(self, events):
        self._log = kl.get_logger(
            app_name=__app_name__, file_name=_cmd_name, log_level=logging.INFO
        )
        self._log.debug(
            "action=starting_cmd_transform cmd={} config={} fieldnames={}".format(
                _cmd_name, self.service, self.fieldnames
            )
        )
        alert_id_field = self.alert_id or "alert_id"
        org_key_field = self.org_key or "org_key"
        self._log.debug(
            "action=setting_field_keys alert_id={} org_key={} ".format(
                alert_id_field, org_key_field
            )
        )
        session_key = "{}".format(self.metadata.searchinfo.session_key)
        if (
            self._fieldnames
            and len(self._fieldnames) == 1
            and self._fieldnames[0] in self._approved_actions
        ):
            self._action = self._fieldnames[0]
        elif (
            self._fieldnames
            and len(self._fieldnames) == 1
            and self._fieldnames not in self._approved_actions
        ):
            raise Exception("Invalid Action Provided: {}".format(self._fieldnames[0]))
        elif self._fieldnames and len(self._fieldnames) > 1:
            raise Exception("Too many API Actions provided")
        else:
            raise Exception("No API Action provided")
        cbc_client = VmwareCBCCommand(_cmd_name, session_key)
        cbc_client.init()
        self._cbc_client = cbc_client
        matrix = [(evt, alert_id_field, org_key_field) for num, evt in
                  enumerate(events)]
        selected_function = None
        if self._action == _OBSERVE:
            selected_function = self._get_observations
        if self._action == _HISTORY:
            selected_function = self._get_history
        if selected_function is None:
            raise Exception("Unable to find the correct API operation")
        p = mp.Pool(10)
        p.starmap(selected_function, matrix)
        p.close()
        p.join()
        self._log.info("action=cmd_result_evt type={1} results_length={0}".format(len(self._results), type(self._results)))
        for evt in self._results:
            yield evt


dispatch(VMWareCBCQueryCommand, sys.argv, sys.stdin, sys.stdout, __name__)
