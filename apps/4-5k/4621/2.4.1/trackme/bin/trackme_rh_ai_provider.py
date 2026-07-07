import import_declare_test

from splunktaucclib.rest_handler.endpoint import (
    field,
    validator,
    RestModel,
    SingleModel,
)
from splunktaucclib.rest_handler import admin_external, util
from trackme_rh_ai_provider_handler import CustomRestHandlerCreateAiProvider
import logging

util.remove_http_proxy_env_vars()


fields = [
    field.RestField(
        "ai_enabled",
        required=False,
        encrypted=False,
        default="1",
        validator=validator.Pattern(
            regex=r"""^(0|1)$""",
        ),
    ),
    field.RestField(
        "ai_provider",
        required=True,
        encrypted=False,
        default="openai",
        validator=validator.Pattern(
            regex=r"""^(openai|azure|anthropic|google|mistral|xai|ollama|custom|splunk_hosted)$""",
        ),
    ),
    field.RestField(
        "ai_base_url",
        required=False,
        encrypted=False,
        default=None,
        validator=validator.Pattern(
            regex=r"""^(https?://.*)?$""",
        ),
    ),
    field.RestField(
        "ai_azure_api_version",
        required=False,
        encrypted=False,
        default="2024-10-21",
        validator=validator.Pattern(
            regex=r"""^[\w\-\.]+$""",
        ),
    ),
    field.RestField(
        "ai_api_key",
        required=False,
        encrypted=True,
        default=None,
        validator=None,
    ),
    field.RestField(
        "ai_model",
        required=True,
        encrypted=False,
        default="gpt-4o",
        validator=validator.Pattern(
            regex=r"""^.+$""",
        ),
    ),
    field.RestField(
        "ai_max_tokens",
        required=False,
        encrypted=False,
        default="4096",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        ),
    ),
    field.RestField(
        "ai_temperature",
        required=False,
        encrypted=False,
        default="0.3",
        validator=validator.Pattern(
            regex=r"""^(\d+\.?\d*|\.\d+)$""",
        ),
    ),
    field.RestField(
        "ai_request_timeout",
        required=False,
        encrypted=False,
        default="600",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        ),
    ),
    field.RestField(
        "ai_context_window",
        required=False,
        encrypted=False,
        default="8192",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        ),
    ),
    field.RestField(
        "ai_agent_token_limit",
        required=False,
        encrypted=False,
        default="150000",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        ),
    ),
    field.RestField(
        "ai_agent_step_limit",
        required=False,
        encrypted=False,
        default="20",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        ),
    ),
    field.RestField(
        "ai_agent_act_token_limit",
        required=False,
        encrypted=False,
        default="200000",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        ),
    ),
    field.RestField(
        "ai_agent_act_step_limit",
        required=False,
        encrypted=False,
        default="40",
        validator=validator.Pattern(
            regex=r"""^[1-9]\d*$""",
        ),
    ),
    field.RestField(
        "ai_prompt_caching_enabled",
        required=False,
        encrypted=False,
        default="1",
        validator=validator.Pattern(
            regex=r"""^(0|1)$""",
        ),
    ),
    field.RestField(
        "ai_custom_prompt",
        required=False,
        encrypted=False,
        default="",
        validator=None,
    ),
]
model = RestModel(fields, name=None)


endpoint = SingleModel("trackme_ai_provider", model, config_name="ai_provider")


if __name__ == "__main__":
    logging.getLogger().addHandler(logging.NullHandler())
    admin_external.handle(
        endpoint,
        handler=CustomRestHandlerCreateAiProvider,
    )
