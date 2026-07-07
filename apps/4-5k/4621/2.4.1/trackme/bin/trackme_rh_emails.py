import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from trackme_rh_emails_handler import CustomRestHandlerCreateEmails
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "email_server",
        required=True,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(?!localhost|127\.0\.0\.1)[^\:]+:\d+$""",
        ),
    ),
    field.RestField(
        "email_username",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^.*$""",
        ),
    ),
    field.RestField(
        "email_password",
        required=False,
        encrypted=True,
        default=None,
        validator=validator.Pattern(
            regex=r"""^.*$""",
        ),
    ),
    field.RestField(
        "email_security",
        required=False,
        encrypted=False,
        default="tls",
        validator=None,
    ),
    field.RestField(
        "allowed_email_domains",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^.+$""",
        ),
    ),
    field.RestField(
        "environment_name",
        required=False,
        encrypted=False,
        default="Splunk",
        validator=None,
    ),
    field.RestField(
        "sender_email",
        required=True,
        encrypted=False,
        default="splunk",
        validator=validator.Pattern(
            regex=r"""^.+$""",
        ),
    ),
    field.RestField(
        "email_format",
        required=False,
        encrypted=False,
        default="html",
        validator=validator.Pattern(
            regex=r"""^(html|text)$""",
        ),
    ),
    field.RestField(
        "email_footer",
        required=True,
        encrypted=False,
        default="This is an automated email, please do not reply directly to this email.",
        validator=validator.Pattern(
            regex=r"""^.+$""",
        ),
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("trackme_emails", model, config_name="emails")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomRestHandlerCreateEmails,
    )
