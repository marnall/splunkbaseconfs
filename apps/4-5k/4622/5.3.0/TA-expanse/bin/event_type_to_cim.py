import abc
import datetime
from collections import OrderedDict

from constants import SPLUNK_EVENT_TIME_FORMAT, \
    SPLUNK_CERT_TIME_FORMAT


class Processor(abc.ABCMeta):
    """The Abstract Base Class for processing data from Expanse endpoints into a CIM

    Available methods:
        process: An abstract implementation for processing the data
    """

    @staticmethod
    @abc.abstractmethod
    def process(payload):
        """An abstract implementation - this must be implemented by the inheriting class

        :param payload: The payload to process into a CIM
        :return: The CIM (if possible, else the original data)
        """
        pass


class AlertProcessor(Processor):
    """
    This processor class is used to return CIM-formatted model for all Alerts.

    Available methods:
        process: Processes an Alert into the Issues Updates CIM
    """

    allow_listed_alert_fields_mapping = {
        'cloud_providers': 'cloud_providers',
        'service_ids': 'service_ids',
        'website_ids': 'website_ids',
        'asset_ids': 'asset_ids',
        'attack_surface_rule_name': 'attack_surface_rule_name',
        'remediation_guidance': 'remediation_guidance',
        'source': 'source',
        'description': 'asm_description',
        'case_id': 'incident_id',
        'tags': 'tags',
        'integration_source': 'integration_source',
        'cloud_management_status': 'cloud_management_status',
        'mitre_tactic_id_and_name': 'mitre_tactic_id_and_name',
        'mitre_technique_id_and_name': 'mitre_technique_id_and_name',
        'country_codes': 'country_codes'
    }

    @staticmethod
    def process(alert):
        """Processes an update from the Alerts API into the Update CIM

        Args:
            alert (dict): The alert object from the Alerts API

        Returns:
            OrderedDict: The Update for CIM
        """

        cert = alert.get('certificate')
        if cert is not None:
            issuer_common_name = cert.get('issuerName')
            start_time = format_time_field(cert.get('validNotBefore'), SPLUNK_CERT_TIME_FORMAT)
            end_time = format_time_field(cert.get('validNotAfter'), SPLUNK_CERT_TIME_FORMAT)
            serial_number = cert.get('serialNumber')
            subject_name = cert.get('subjectName')
        else:
            issuer_common_name = start_time = end_time = serial_number = subject_name = None

        ip = None
        ipv4addresses = alert.get('ipv4_addresses')
        ipv6addresses = alert.get('ipv6_addresses')
        if ipv6addresses:
            ip = ipv6addresses[0]
        elif ipv4addresses:
            ip = ipv4addresses[0]

        if not alert.get("cloud_management_status"):
            raise Exception("Alert context is missing. Adding alert to retry queue")

        data_dict = OrderedDict([
            ('dest_ip', ip),
            ('dest_port', str(alert.get('action_remote_port', [None])[0]) if alert.get('action_remote_port') else None),
            ('dest_name', alert.get('domain_names')[0] if alert.get('domain_names') else None),
            ('severity', alert.get('severity')),
            ('description', alert['name']),
            ('creation_time', format_time_field(alert.get('detection_timestamp'), SPLUNK_EVENT_TIME_FORMAT)),
            ('server_creation_time', format_time_field(alert.get('local_insert_ts'), SPLUNK_EVENT_TIME_FORMAT)),
            ('last_modified_ts', format_time_field(alert.get('last_modified_ts'), SPLUNK_EVENT_TIME_FORMAT)),
            ('transport', alert.get('port_protocol')),
            ('ssl_issuer_common_name', issuer_common_name),
            ('ssl_start_time', start_time),
            ('ssl_end_time', end_time),
            ('ssl_serial', serial_number),
            ('ssl_subject_common_name', subject_name),
            ('last_observed', format_time_field(alert.get('last_observed'), SPLUNK_EVENT_TIME_FORMAT)),
            ('alert_id', alert['alert_id'])
        ])

        bus = []
        bu_hierarchies = alert.get('business_unit_hierarchies')
        if isinstance(bu_hierarchies, list) and all(isinstance(elem, list) for elem in bu_hierarchies):
            bu_hierarchies = [bu for hierarchy in bu_hierarchies for bu in hierarchy]

        if bu_hierarchies:
            for business_unit in bu_hierarchies:
                business_unit['creation_time'] = datetime.datetime.fromtimestamp(
                    business_unit.get('creation_time') / 1000) \
                    .strftime(SPLUNK_EVENT_TIME_FORMAT)
                business_unit['update_time'] = datetime.datetime.fromtimestamp(business_unit.get('update_time') / 1000) \
                    .strftime(SPLUNK_EVENT_TIME_FORMAT)
                bus.append(business_unit)

        data_dict['business_units'] = bus

        asset_identifiers = alert.get('asset_identifiers')

        if asset_identifiers:
            for identifier in asset_identifiers:
                if identifier:
                    if identifier["firstObserved"]:
                        identifier["firstObserved"] = format_time_field(
                            identifier["firstObserved"], SPLUNK_EVENT_TIME_FORMAT)
                    if identifier["lastObserved"]:
                        identifier["lastObserved"] = format_time_field(
                            identifier["lastObserved"], SPLUNK_EVENT_TIME_FORMAT)

                    if identifier["certificate"]:
                        identifier["certificate"]["validNotBefore"] = format_time_field(
                            identifier["certificate"]["validNotBefore"], SPLUNK_CERT_TIME_FORMAT)
                        identifier["certificate"]["validNotAfter"] = format_time_field(
                            identifier["certificate"]["validNotAfter"], SPLUNK_CERT_TIME_FORMAT)

        data_dict['asset_identifiers'] = asset_identifiers

        data_dict['resolution_status'] = alert.get('resolution_status')[11:] if alert.get('resolution_status') else None

        list_of_kv_update = [(value, alert.get(key)) for key, value in
                             AlertProcessor.allow_listed_alert_fields_mapping.items()]
        data_dict.update(list_of_kv_update)
        return data_dict


def format_time_field(epoch_millis, format):
    if epoch_millis:
        epoch_seconds = epoch_millis / 1000
        millis = epoch_millis % 1000
        date = datetime.datetime.fromtimestamp(epoch_seconds, datetime.timezone.utc) + datetime.timedelta(
            milliseconds=millis)
        return date.strftime(format)
    else:
        return ""
