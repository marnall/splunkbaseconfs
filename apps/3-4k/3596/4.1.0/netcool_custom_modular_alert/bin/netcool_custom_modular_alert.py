import logging
import sys
from modular_alert import ModularAlert, Field, IntegerField, FieldValidationException
from pysnmp.hlapi import *
from pysnmp.proto import rfc1902
from pysnmp.entity.rfc3413.oneliner import ntforg


class CustomAlert(ModularAlert):
    def __init__(self, **kwargs):
        params = [
            Field("community"),
            Field("hostname"),
            Field("customtext"),
            Field("alertmessage"),
            Field("severity"),
            Field("escalation"),
            Field("AlertKey"),
            Field("enterpriseSNMPObjectID"),
            Field("enterpriseSNMPSpecificTrapID"),
            Field("enterpriseSNMPSpecificObjectID"),
            Field("serverip"),
        ]

        super(CustomAlert, self).__init__(
            params,
            logger_name="netcool_custom_modular_alert",
            log_level=logging.INFO,
            log_to_file=True,
        )

    def run(self, cleaned_params, payload):

        ntfOrg = ntforg.NotificationOriginator()

        splunkapp = payload["app"]
        splunksearch = payload["search_name"]

        # From HTML Form
        community = cleaned_params.get("community", "(blank)")
        hostname = cleaned_params.get("hostname", "(blank)")
        customtext = cleaned_params.get("customtext", "(blank)")
        alertmessage = cleaned_params.get("alertmessage", "(blank)")
        severity = cleaned_params.get("severity", "(blank)")
        escalation = cleaned_params.get("escalation", "(blank)")
        alertkey = cleaned_params.get("AlertKey", "(blank)")
        enterpriseSNMPObjectID = cleaned_params.get("enterpriseSNMPObjectID", "(blank)")
        enterpriseSNMPSpecificTrapID = cleaned_params.get(
            "enterpriseSNMPSpecificTrapID", "(blank)"
        )
        enterpriseSNMPSpecificObjectID = cleaned_params.get(
            "enterpriseSNMPSpecificObjectID", "(blank)"
        )
        serverIPFormField = cleaned_params.get("serverip", "(blank)")
        enterpriseSNMP = enterpriseSNMPObjectID + "." + enterpriseSNMPSpecificTrapID
        enterpriseSNMP_SpecificObjectID = (
            enterpriseSNMPObjectID + "." + enterpriseSNMPSpecificObjectID
        )
        uniquePairs = serverIPFormField.split(";")

        self.logger.info("START")
        for uniquePair in uniquePairs:
            serveripField, portField = uniquePair.split(":")
            self.logger.debug(
                "splunkapp:"
                + str(splunkapp)
                + ", splunksearch:"
                + str(splunksearch)
                + ", snmp_serverip:"
                + str(serveripField)
                + ", snmp_port:"
                + str(portField)
                + ", snmp_community:"
                + str(community)
                + ", snmp_hostname:"
                + str(hostname)
                + ", snmp_alertmessage:"
                + str(alertmessage)
                + ", snmp_severity:"
                + str(severity)
                + ", splunk_escalation:"
                + str(escalation)
                + ", splunk_payload:"
                + str(payload)
                + ", splunk_customtext:"
                + str(customtext)
            )
            errorIndication = ntfOrg.sendNotification(
                ntforg.CommunityData(str(community), mpModel=0),
                ntforg.UdpTransportTarget((str(serveripField), str(portField))),
                "trap",
                str(enterpriseSNMP),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".1",
                    rfc1902.OctetString(str(hostname).encode()),
                ),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".2",
                    rfc1902.OctetString(str(customtext).encode()),
                ),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".3",
                    rfc1902.OctetString(str(alertkey).encode()),
                ),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".4",
                    rfc1902.OctetString(str(alertmessage).encode()),
                ),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".5",
                    rfc1902.OctetString(str(splunkapp).encode()),
                ),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".6",
                    rfc1902.OctetString(str(severity).encode()),
                ),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".7",
                    rfc1902.OctetString(str(escalation).encode()),
                ),
                (
                    str(enterpriseSNMP_SpecificObjectID) + ".8",
                    rfc1902.OctetString(str(splunksearch).encode()),
                ),
            )
        self.logger.info("STOP")


"""
If the script is being called directly from the command-line, then this is likely being executed by Splunk.
"""
if __name__ == "__main__":

    # Make sure this is a call to execute
    if len(sys.argv) > 1 and sys.argv[1] == "--execute":

        try:
            modular_alert = CustomAlert()
            modular_alert.execute()
            sys.exit(0)
        except Exception as e:
            # This logs general exceptions that would have been unhandled otherwise (such as coding errors)
            print(
                "Unhandled exception was caught, this may be due to a defect in the script:"
                + str(e),
                file=sys.stderr,
            )
            raise

    else:
        print("Unsupported execution mode (expected --execute flag)", file=sys.stderr)
        sys.exit(1)
