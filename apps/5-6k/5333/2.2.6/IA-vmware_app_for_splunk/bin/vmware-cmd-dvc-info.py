import sys
import logging
from VMWUtilities import KennyLoggins
from vmware_cbc_cmd import VmwareCBCCommand
import vmware_paths
from splunklib.searchcommands import Configuration, EventingCommand, Option, validators, dispatch

__app_name__ = vmware_paths.__app_name__
# _cmd_name = "cbccmddvcinfo"
_cmd_name = "cbcdvcinfo"
kl = KennyLoggins()


@Configuration()
class VMWareDvcInfoCommand(EventingCommand):
    """ %(synopsis)
    ##Syntax
    %(syntax)
    ##Description
    %(description)
    """

    device_id = Option(
        doc='''
            **Syntax:** **host=***<field>*
            **Description:** Name of the field that holds the hostname''',
        require=False, validate=validators.Fieldname())

    org_key = Option(
        doc='''
            **Syntax:** **org_key=***<field>*
            **Description:** Name of the field that holds the org key''',
        require=False, validate=validators.Fieldname())

    fields = Option(
        doc='''
                **Syntax:** **fields=***<list>*
                **Description:** List of fields to return''',
        require=False, validate=validators.List()
    )

    def transform(self, events):
        log = kl.get_logger(app_name=__app_name__, file_name=_cmd_name, log_level=logging.INFO)
        log.debug("action=starting_cmd_transform cmd={} config={} fieldnames={}".format(_cmd_name, self.service,
                                                                                             self.fieldnames))
        hosts = {}
        hostname_field = self.device_id or "device_id"
        org_key_field = self.org_key or "org_key"
        fields_to_keep = self.fields or False
        if fields_to_keep:
            fields_to_keep.append("internal_exception")
        log.debug("action=setting_keys hostname={} org_key={} fields={}".format(hostname_field, org_key_field, fields_to_keep))
        session_key = "{}".format(self.metadata.searchinfo.session_key)
        cbc_client = VmwareCBCCommand(_cmd_name, session_key)
        cbc_client.init()
        for evt in events:
            if evt[hostname_field] in hosts.keys():
                log.debug("action=found_pulled_host host={}".format(evt[hostname_field]))
            else:
                log.debug("action=host_not_found host={}".format(evt[hostname_field]))
                hosts[hostname_field] = cbc_client.get_device(evt[hostname_field], evt[org_key_field])
                log.debug("action=found_data {}".format(hosts[hostname_field].keys()))
            for k in hosts[hostname_field].keys():
                if not fields_to_keep:
                    evt[k] = hosts[hostname_field][k]
                else:
                    log.debug("action=check_key key={} is_in={}".format(k, k in fields_to_keep))
                    if k in fields_to_keep:
                        evt[k] = hosts[hostname_field][k]

            log.info("action=check_key evt={}".format(evt))
            yield evt


dispatch(VMWareDvcInfoCommand, sys.argv, sys.stdin, sys.stdout, __name__)
