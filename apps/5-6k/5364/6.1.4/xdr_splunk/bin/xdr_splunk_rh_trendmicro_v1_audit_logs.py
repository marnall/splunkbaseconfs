import import_declare_test

from endpoints.audit_logs_endpoint import endpoint
from splunktaucclib.splunk_aoblib.rest_migration import ConfigMigrationHandler
from splunktaucclib.rest_handler import admin_external


if __name__ == '__main__':
    admin_external.handle(
        endpoint,
        handler=ConfigMigrationHandler,
    )
