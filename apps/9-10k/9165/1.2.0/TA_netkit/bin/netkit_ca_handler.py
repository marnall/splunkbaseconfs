try:
    import import_declare_test
except ImportError:
    pass

import netkit_ca
from netkit_rest import ValidatingHandler


class CertificateAuthorityHandler(ValidatingHandler):
    def _validate(self):
        netkit_ca.validate_ca_certificate(self.payload.get("ca_certificate", ""))
