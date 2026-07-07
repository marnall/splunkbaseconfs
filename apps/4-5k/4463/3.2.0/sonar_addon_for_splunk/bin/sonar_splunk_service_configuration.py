import json

from constants import (LICENSE, ADDRESS_FIELD, PORT_FIELD, LIMIT_FIELD, INDEX, TIMESTAMP_FIELD, APP_NAME, LICENSE_LABEL,
                       START_TIME, END_TIME, USER, SEARCH_ID, STAGES, SEARCH_STAGE, LIMIT_STAGE, SEARCH_COMMANDS,
                       COMMAND_FIELD, SONAR_COMMAND, SEARCH_COMMAND, SPATH_COMMAND, HEAD_COMMAND, ARGS_FIELD,
                       SEARCH_ARG, LICENSE_FIELD, DISABLE_COUNT, REALM, PORT_LABEL, ADDRESS_LABEL, KEY, LABEL,
                       INSTANCES_FIELD, DESCRIPTION_FIELD, IS_DEFAULT_FIELD, CONFIGURATION_STANZA)
from sonar_exception import ValidationException
from utils import string, number, logger # TODO: remove logger later. Or keep it and add more logging statements


class SonarSplunkServiceConfiguration:
    index = None
    timestamp = None
    limit = None
    disable_count = False
    instance = None
    description = None
    is_default = False

    search_service = None
    app_configuration = None
    search_metadata = None

    def __init__(self, search_service, app_configuration, search_metadata):
        self.search_service = search_service
        self.app_configuration = app_configuration
        self.search_metadata = search_metadata

    def with_index(self, index):
        self.index = index
        return self

    def with_timestamp(self, timestamp):
        self.timestamp = timestamp
        return self

    def with_limit(self, limit):
        self.limit = limit
        return self

    def with_disable_count(self, disable_count):
        self.disable_count = disable_count
        return self

    def with_description(self, description):
        self.description = description
        return self

    def with_is_default(self, is_default):
        self.is_default = is_default
        return self

    def with_instance(self, instance):
        self.instance = instance
        return self

    def get_address(self):
        address = self.app_configuration[ADDRESS_FIELD].strip().rstrip("/")

        if address.startswith("http://"):
            address = address.replace("http://", "", 1)
        elif address.startswith("https://"):
            address = address.replace("https://", "", 1)

        return address

    def get_port(self):
        return self.app_configuration[PORT_FIELD].strip()

    def get_description(self):
        description = self.app_configuration.get(DESCRIPTION_FIELD)
        return description.strip() if description else ""

    def request_body(self):
        body = {
            INDEX: self.index,
            TIMESTAMP_FIELD: self.timestamp,
            START_TIME: self.search_metadata.searchinfo.earliest_time,
            END_TIME: self.search_metadata.searchinfo.latest_time,
            USER: self.search_metadata.searchinfo.username,
            SEARCH_ID: self.search_metadata.searchinfo.sid,
            STAGES: self.query_stages(),
            DISABLE_COUNT: self.disable_count
        }

        limit = self.app_configuration[LIMIT_FIELD] if hasattr(self.app_configuration, LIMIT_FIELD) else None
        description = self.app_configuration[DESCRIPTION_FIELD] if hasattr(self.app_configuration, DESCRIPTION_FIELD) else None
        is_default = self.app_configuration[IS_DEFAULT_FIELD] if hasattr(self.app_configuration, IS_DEFAULT_FIELD) else False
        instance = self.instance or self.app_configuration[INSTANCES_FIELD][self.instance]

        body.update(description=description)
        body.update(is_default=is_default)
        body.update(instance=instance)
        body.update(license=self.get_secret_field(LICENSE_FIELD if (instance == CONFIGURATION_STANZA or not instance) else f"{LICENSE_FIELD}-{instance}"))

        if limit and isinstance(limit, (string, number)):
            body.update(limit=int(limit))

        return body

    def query_stages(self):
        sid = self.search_metadata.searchinfo.sid
        job = self.search_service.job(sid)
        query = job.content.optimizedSearch

        parsed_query = self.search_service.parse(query=query, output_mode="json")
        body = json.loads(parsed_query.body.read())
        commands = body.get(SEARCH_COMMANDS, [])

        stages = []

        for command in commands:
            command_type = command.get(COMMAND_FIELD, "").lower()
            args = command.get(ARGS_FIELD, "")

            # Ignore spath and sonar stages
            if command_type in (SPATH_COMMAND, SONAR_COMMAND):
                continue

            # Stop if an unknown stage is found
            if command_type not in (SEARCH_COMMAND, HEAD_COMMAND):
                break

            if SEARCH_COMMAND == command_type:
                search_args = args.get(SEARCH_ARG)  # type: list

                if len(search_args) > 0:
                    stages.append({SEARCH_STAGE: search_args[0]})
            else:
                stages.append({LIMIT_STAGE: args})

        return stages

    def get_secret_field(self, field):
        if SonarSplunkServiceConfiguration.is_blank_string(field):
            return ''

        password_storage = self.search_service.storage_passwords

        for credential in password_storage:
            if credential.username == field and credential.realm == REALM:
                return credential.clear_password

        return ''

    def validate(self):
        cfg = self.app_configuration

        if not cfg:
            raise ValidationException("Sonar Service configuration not found. If this error persists, contact the app support")

        self.validate_required_fields(cfg)
        self.validate_service()

        return self

    def validate_required_fields(self, cfg):
        fields = [{LABEL: ADDRESS_LABEL, KEY: ADDRESS_FIELD},
                  {LABEL: PORT_LABEL, KEY: PORT_FIELD}]

        secret_fields = [{LABEL: LICENSE_LABEL, KEY: LICENSE_FIELD}]

        missing_fields = []

        for field in fields:
            if SonarSplunkServiceConfiguration.is_blank_string(cfg[field[KEY]]):
                missing_fields.append(field)

        for field in secret_fields:
            secret_username = field[KEY] if (self.instance == CONFIGURATION_STANZA or not self.instance) else f"{field[KEY]}-{self.instance}"

            if SonarSplunkServiceConfiguration.is_blank_string(self.get_secret_field(secret_username)):
                missing_fields.append(field)

        if len(missing_fields) > 0:
            raise ValidationException("Missing configuration: %s. You can configure these fields on %s's Configuration page." % (
                ", ".join(str(missing_field[LABEL]) for missing_field in missing_fields), APP_NAME))

    def validate_service(self):
        address = self.get_address()
        port = self.get_port()

        if SonarSplunkServiceConfiguration.is_blank_string(address):
            raise ValidationException("Invalid sonar service address '%s'" % self.app_configuration[ADDRESS_FIELD])

        if not (isinstance(port, string) and port.isdigit() and int(port) > 0):
            raise ValidationException("Invalid sonar service port '%s'" % self.app_configuration[PORT_FIELD])

    @staticmethod
    def is_blank_string(value):
        return not (value and isinstance(value, string) and value.strip())
