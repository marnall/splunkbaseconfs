try:
    import import_declare_test
except ImportError:
    pass

import netkit_config
import netkit_dns
import netkit_targets
from netkit_rest import ValidatingHandler


class DomainGroupHandler(ValidatingHandler):
    def _validate(self):
        netkit_targets.parse_names(self.payload.get("domains", ""))


class DnsResolverHandler(ValidatingHandler):
    def _validate(self):
        netkit_dns.validate_nameserver(self.payload.get("nameserver", ""))
        netkit_dns.validate_protocol(self.payload.get("protocol"))


class SettingsHandler(ValidatingHandler):
    def _validate(self):
        if netkit_config.is_true(self.payload.get("override_system_resolver")):
            netkit_dns.validate_nameserver(self.payload.get("default_resolver", ""))
        netkit_dns.validate_protocol(self.payload.get("default_protocol"))
