# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib']))
sys.path.append(make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common']))

from ITOA.itoa_common import is_cloud
from ITOA.mod_input_utils import skip_run_during_migration
from ITOA.setup_logging import getLogger4ModInput
from SA_ITOA_app_common.solnlib.modular_input import ModularInput
from SA_ITOA_app_common.solnlib.conf_manager import ConfManager
from ITOA.event_management.itsi_nats_tls_helper import ITSINatsTLSHelper


class ITSINatsCertficatesAutoRotation(ModularInput):
    """
    Automatically rotate the TLS certificates that are about to expire without down time and reload NATS server to take new certificates
    """
    title = 'IT Service Intelligence NATS Certificates Auto Rotation'
    description = 'Modular Input to rotate the TLS certificates without down time and reload NATS server to take new certificates'
    app = 'SA-ITOA'
    name = 'itsi_nats_certificates_auto_rotation'
    owner = 'nobody'
    use_single_instance = False
    use_kvstore_checkpointer = False
    use_hec_event_writer = False

    @skip_run_during_migration
    def do_run(self, input_config):
        logger = getLogger4ModInput(input_config)
        self.logger = logger
        cfm = ConfManager(self.session_key, 'SA-ITOA')
        conf = cfm.get_conf('itsi_nats')
        settings = conf.get('nats_settings')
        require_tls_client_cert_cloud = int(settings.get('require_tls_client_cert_cloud', 1))
        require_tls_client_cert_on_prem = int(settings.get('require_tls_client_cert_on_prem', 0))
        is_cloud_stack = is_cloud(self.logger, self.session_key)
        tls_enabled = (is_cloud_stack is True and require_tls_client_cert_cloud == 1) or (is_cloud_stack is False and require_tls_client_cert_on_prem == 1)
        logger.info(f'ITSI NATS Certificate Rotation and reload modinput. Cloud stack : {is_cloud_stack}, TLS enabled : {tls_enabled}')
        if tls_enabled is True:
            ITSINatsTLSHelper(self.session_key, self.logger).rotate_tls_certificates()


if __name__ == '__main__':
    worker = ITSINatsCertficatesAutoRotation()
    worker.execute()
    sys.exit(0)
