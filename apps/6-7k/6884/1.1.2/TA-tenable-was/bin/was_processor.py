from tenable.io import TenableIO
from tenable.errors import TioExportsError, ConnectionError
import arrow
import json
import datetime

class WAS_Event_Proccessor(object):

    def __init__(self, input_name, start_time, api_key, secret_key, hostname='cloud.tenable.com'):
        self.hostname = hostname
        self.api_key = api_key
        self.secret_key = secret_key
        self.input_name = input_name
        self.start_time = start_time

        try:
            self._tio = TenableIO(
                access_key=self.api_key,
                secret_key=self.secret_key,
                url="https://" + self.hostname.strip("/"),
                vendor='Tenable',
                product='SPLUNK WAS',
                build='1.1.0'
            )

        except ConnectionError as e:
            self.helper.log_error("Tenable WAS error occured while initializing connection: {}".format(str(e)))
            exit(0)
        if self._tio.session.details().get('permissions') < 64:
            self.helper.log_error('This integrations requires that the user we connect with is a Tenable.io Administrator. Please update the account in Tenable.io and try again.')
            exit(0)

    def get_checkpoint(self, helper, export_type, time_filter):
        """Return checkpoint based on export type and time filter field.

        Args:
            export_type (str): vulns
            time_filter (str): time field filter based on export
                                finalized_at - active vulns
        Returns:
            dict: checkpoint state dict
        """
        check_point_name = "{}_{}_{}".format(self.input_name, export_type, time_filter)
        helper.log_debug(
            "Check point name is {}".format(check_point_name))

        state = helper.get_check_point(check_point_name)
        helper.log_debug(
            "Check point state returned is {}".format(state))

        # in case if checkpoint is not found state value will be None,
        # so we are setting it to empty dict
        if not isinstance(state, dict):
            state = {}
        return state

    def save_checkpoint(self, helper, export_type, time_filter, state):
        """Save checkpoint state with name formed from input name, export type, and time field.

       Args:
            export_type (str): vulns
            time_filter (str): time field filter based on export
                                finalized_at - active vulns
            state (dict): checkpoint state value
        """
        check_point_name = "{}_{}_{}".format(self.input_name, export_type, time_filter)
        helper.save_check_point(check_point_name, state)
        helper.log_debug(
            "Check point state saved is " + str(state))

    def create_events(self, helper, ew):
        helper.log_info("Started process for Vulns")
        permission = self._tio.session.details().get('permissions')
        helper.log_debug("Current permission {}".format(permission))

        vuln_checkpoint = self.get_checkpoint(helper, "was_vulns", "scans_finalized_at")
        if vuln_checkpoint:
            helper.log_debug("Checkpoint found for WAS vulns with value: {}".format(vuln_checkpoint))
        else:
            helper.log_debug("No Checkpoint found for WAS vulns")

        check_point_data = vuln_checkpoint.get("since", self.start_time)
        helper.log_debug("checkpoint :{}".format(check_point_data))
        was_findings = self._tio.was.export(and_filter=[
            ("scans_finalized_at", "gt", check_point_data),
            ("scans_status", "contains", ["completed"])
        ])

        # ct stores current time
        ct = datetime.datetime.now()

        # current_timestamp store timestamp of current time
        current_timestamp = int(round(ct.timestamp()))
        max_event_time = -1

        count = 0
        for finding in was_findings:
            count += 1
            finding["scan_uuid_timestamp"] = current_timestamp
            clean_asset = json.dumps(finding)
            # helper.log_debug("scans_finalized_at :{}".format((finding.get("parent_scan", "0")).get("finalized_at",
            # "0")))
            checkpoint_time = arrow.get((finding.get("parent_scan", "0")).get("finalized_at", "0")).int_timestamp
            event_time = arrow.get((finding.get("scan", "0")).get("finalized_at", "0")).int_timestamp
            event = helper.new_event(source=helper.get_input_type(), time=event_time, index=helper.get_output_index(), sourcetype=helper.get_sourcetype(), data=clean_asset)
            ew.write_event(event)
            max_event_time = max(max_event_time, checkpoint_time)

        if max_event_time != -1:
            vuln_checkpoint["since"] = datetime.datetime.utcfromtimestamp(max_event_time).isoformat() + "Z"
            helper.log_debug(
                "Saving new checkpoint for WAS Vulns with value: {0}".format(
                    vuln_checkpoint["since"]))
            self.save_checkpoint(helper, "was_vulns", "scans_finalized_at", vuln_checkpoint)

        helper.log_info("Process completed Successful. Total no. of vulns: {}".format(count))


if __name__ == '__main__':
    from pprint import pprint as pp
    api_key = ''
    secret_key = ''
    domain = 'cloud.tenable.com'
    input_name = ''
    start_time = ''
    tep = WAS_Event_Proccessor(input_name=input_name, start_time=start_time, api_key=api_key, secret_key=secret_key, hostname=domain)
