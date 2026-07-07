import ta_etintel_declare

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    MultipleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from splunk_aoblib.rest_migration import ConfigMigrationHandler
import logging
import traceback

util.remove_http_proxy_env_vars()

logger = logging.getLogger('ta_etintel')

fields_proxy = [
    field.RestField(
        'proxy_enabled',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    ), 
    field.RestField(
        'proxy_type',
        required=False,
        encrypted=False,
        default='http',
        validator=None
    ), 
    field.RestField(
        'proxy_url',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=4096, 
        )
    ), 
    field.RestField(
        'proxy_port',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Number(
            min_val=1, 
            max_val=65535, 
        )
    ), 
    field.RestField(
        'proxy_username',
        required=False,
        encrypted=False,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=50, 
        )
    ), 
    field.RestField(
        'proxy_password',
        required=False,
        encrypted=True,
        default=None,
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'proxy_rdns',
        required=False,
        encrypted=False,
        default=None,
        validator=None
    )
]
model_proxy = RestModel(fields_proxy, name='proxy')


fields_logging = [
    field.RestField(
        'loglevel',
        required=False,
        encrypted=False,
        default='INFO',
        validator=None
    )
]
model_logging = RestModel(fields_logging, name='logging')


fields_additional_parameters = [
    field.RestField(
        'api_key',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    ), 
    field.RestField(
        'authorization_code',
        required=True,
        encrypted=True,
        default='',
        validator=validator.String(
            min_len=0, 
            max_len=8192, 
        )
    )
]
model_additional_parameters = RestModel(fields_additional_parameters, name='additional_parameters')


endpoint = MultipleModel(
    'ta_etintel_settings',
    models=[
        model_proxy, 
        model_logging, 
        model_additional_parameters
    ],
)


class BasicConfigHandler(ConfigMigrationHandler):
    def handleEdit(self, confInfo):
        try:
            # Call parent method to save settings
            super(BasicConfigHandler, self).handleEdit(confInfo)

            # Simple file operations with minimal dependencies
            import os

            # Create local directory
            app_path = os.path.join(os.environ.get('SPLUNK_HOME', '/opt/splunk'), 'etc', 'apps', 'TA-etintel', 'local')
            logger.info(f"Creating local directory at: {app_path}")
            if not os.path.exists(app_path):
                os.makedirs(app_path)

            # Mark app as configured
            app_conf_path = os.path.join(app_path, "app.conf")
            logger.info(f"Writing app.conf to: {app_conf_path}")
            with open(app_conf_path, 'w') as f:
                f.write("[install]\n")
                f.write("is_configured = 1\n")
                f.write("state = enabled\n\n")
                f.write("[ui]\n")
                f.write("is_visible = 1\n\n")
                f.write("[launcher]\n")
                f.write("author = Proofpoint Inc\n")
                f.write("version = 2.5.0\n")
                f.write("description = Proofpoint ET-Intel TA\n")

            # Create transforms.conf
            transforms_conf_path = os.path.join(app_path, "transforms.conf")
            logger.info(f"Writing transforms.conf to: {transforms_conf_path}")
            with open(transforms_conf_path, 'w') as f:
                f.write("# transforms.conf\n")
                f.write("[et_rep_categories]\nallow_caching = true\nfilename = categories.csv\n\n")
                f.write("[et_threat_categories]\nallow_caching = true\nfilename = cat.threat.csv\n\n")
                f.write("[et_domain_repdata]\nallow_caching = false\nfilename = combined.domain.csv\n\n")
                f.write(
                    "[et_extended_domain_repdata]\nallow_caching = false\nfilename = combined.extended-domain.csv\n\n")
                f.write("[et_ip_repdata]\nallow_caching = false\nfilename = combined.ip.csv\n\n")
                f.write("[et_extended_ip_repdata]\nallow_caching = false\nfilename = combined.extended-ip.csv\n\n")
                f.write("[etintel_ip_repdata]\nallow_caching = false\nfilename = combined.ip.csv\n\n")
                f.write("[etintel_domain_repdata]\nallow_caching = false\nfilename = combined.domain.csv\n\n")

            # Create inputs.conf
            inputs_conf_path = os.path.join(app_path, "inputs.conf")
            logger.info(f"Writing inputs.conf to: {inputs_conf_path}")
            with open(inputs_conf_path, 'w') as f:
                f.write("[update_repdata://default]\n")
                f.write("check_file_integrity = 1\n")
                f.write("interval = 3600\n")
                f.write("disabled = 0\n")

            # Create lookups directory and cat.threat.csv
            lookups_path = os.path.join(os.environ.get('SPLUNK_HOME', '/opt/splunk'), 'etc', 'apps', 'TA-etintel',
                                        'lookups')
            logger.info(f"Ensuring lookups directory exists at: {lookups_path}")
            if not os.path.exists(lookups_path):
                os.makedirs(lookups_path)
                
            # Create cat.threat.csv if it doesn't exist
            cat_threat_path = os.path.join(lookups_path, "cat.threat.csv")
            if not os.path.exists(cat_threat_path):
                logger.info(f"Creating cat.threat.csv at: {cat_threat_path}")
                with open(cat_threat_path, 'w') as f:
                    f.write("category,threat\n")
                    # Add default categories and threats
                    f.write("1,C&C\n")
                    f.write("2,Bot\n")
                    f.write("3,Spam\n")
                    f.write("4,Drop\n")
                    f.write("5,Spyware\n")
                    f.write("6,Malware\n")
                    f.write("7,Proxy\n")
                    f.write("8,P2P\n")
                    f.write("9,Phishing\n")
                    f.write("10,Compromised\n")
                    f.write("11,Scanning\n")
                    f.write("12,Fake AV\n")
                    f.write("13,Cryptomining\n")
                    f.write("14,Ransomware\n")

            logger.info("App configuration completed successfully")

        except Exception as e:
            error_msg = f"Error configuring app: {str(e)}"
            logger.error(error_msg)
            logger.error(traceback.format_exc())
            confInfo['error'] = error_msg  # This will display in the UI
            raise e  # Re-raise to ensure setup fails visibly


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=BasicConfigHandler,
    )
