import json

from recordedfuture.core.constants import CONFIG_FILENAME, HIDDEN_GLOBAL_BANNER_STANZA
from recordedfuture.core.dict_validation import (
    validate_dict,
    OptionalField,
    NestedField,
)
from recordedfuture.core.exceptions import ValidationError
from recordedfuture.api.splunk_api import SplunkClient
from recordedfuture.core.utils import (
    endpoint_requires_payload,
    get_property_from_usecases,
)


def get_global_banner(_, app_env):
    """Gets global banner from BFI and decides if it needs to be shown.

    Args:
        _ (dict): in_dict.
        app_env (app_env.RfesAppEnv): application environment.

    Returns:
        (int, dict): status code and payload for global banner to show.
    """
    banner_from_bfi = get_property_from_usecases(
        SplunkClient(app_env), app_env, "global_banner_usecase", {}
    )
    try:
        _validate_global_banner(banner_from_bfi)
    except ValidationError:
        return 200, {"show": False}

    hidden_global_banner = _get_hidden_global_banner(app_env)

    if hidden_global_banner and hidden_global_banner == banner_from_bfi:
        # The same global banner was hidden before, so setting "show" to False
        banner_from_bfi["show"] = False
        return 200, banner_from_bfi

    return 200, banner_from_bfi


@endpoint_requires_payload
def hide_global_banner(in_dict, app_env):
    """Marks the banner as hidden in the config.

    Args:
        in_dict (dict): dict with payload.
        app_env (app_env.RfesAppEnv): application environment.

    Returns:
        (int, dict): status code and payload.
    """
    splunk_client = SplunkClient(app_env)

    try:
        banner = json.loads(in_dict.get("payload"))
    except json.JSONDecodeError as exc:
        raise ValidationError(
            "Failed to parse the payload for banner to hide: {}. Error: {}".format(
                in_dict.get("payload"),
                str(exc),
            )
        )
    _validate_global_banner(banner)

    splunk_client.config.post_config(
        CONFIG_FILENAME,
        HIDDEN_GLOBAL_BANNER_STANZA,
        {"banner": json.dumps(banner)},
    )
    return 202, {}


def _validate_global_banner(banner):
    """Validates the global banner.

    Args:
        banner (dict): banner to validate.

    Raises:
        ValidationError: if the banner is not valid.
    """
    schema = {
        "show": bool,
        "color": str,
        "title": str,
        "description": OptionalField(str),
        "hyperlink": OptionalField(
            NestedField(
                {
                    "text": str,
                    "url": str,
                }
            )
        ),
    }
    validate_dict(banner, schema)


def _get_hidden_global_banner(app_env):
    """Gets hidden global banner from the configuration.

    Args:
        app_env (app_env.RfesAppEnv): application environment.

    Returns:
        dict|None: hidden global banner or None if was not found.
    """
    try:
        return json.loads(app_env.hidden_global_banner["banner"])
    except (json.JSONDecodeError, TypeError, KeyError):
        return None
