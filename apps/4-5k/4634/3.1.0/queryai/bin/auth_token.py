from typing import Optional
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "bin"))

from splunklib.searchcommands.search_command import SearchCommand

STAGE = os.getenv("APP_ENVIRONMENT", "PROD")
API_KEY_REALM = "queryai_splunk_app_secret"
PROXY_REALM = "queryai_proxy_secret"
API_KEY_USERNAME = "admin"
PROXY_USERNAME = "proxy"

# Realms and username to be used for storing and retrieving passwords using storage/passwords
SECRET_REALM = "queryai_splunk_app_secret"
SECRET_NAME = "admin"

SEARCH_URL = (
    f"https://api.{STAGE}.query.ai/search/translation/splunk"
    if STAGE in ("dev", "test")
    else "https://api.query.ai/search/translation/splunk"
)

# Auth0 URLs
AUTH_DOMAIN_URL = f"https://auth.{STAGE}.query.ai" if STAGE in ("dev", "test") else "https://auth.query.ai"
AUTH_AUDIENCE = (
    f"https://queryai-{STAGE}.us.auth0.com/api/v2/"
    if STAGE in ("dev", "test")
    else "https://queryai.us.auth0.com/api/v2/"
)


# Get plain text password from storage/password
def retrieve_password(
    query_command: SearchCommand, realm: str = SECRET_REALM, name: str = SECRET_NAME
) -> Optional[str]:
    if not query_command.service:
        query_command.logger.error("Service is not available.")  # pyright: ignore[reportOptionalMemberAccess]
        return None
    query_command.logger.info(  # pyright: ignore[reportOptionalMemberAccess]
        f"Retrieving password for realm: {realm}, name: {name}"
    )
    try:
        # Use direct access to storage/passwords by constructing the proper ID
        # This doesn't require list_storage_passwords permission
        password_id = f"{realm}:{name}:"
        storage_password = query_command.service.storage_passwords[password_id]
        query_command.logger.info(  # pyright: ignore[reportOptionalMemberAccess]
            f"Found password for realm: {realm}, name: {name}"
        )
        return storage_password.clear_password
    except KeyError:
        # Password doesn't exist
        query_command.logger.warning(  # pyright: ignore[reportOptionalMemberAccess]
            f"No password found for realm: {realm}, name: {name}"
        )
        return None
    except Exception as e:
        # Some other error occurred
        query_command.logger.warning(f"Error retrieving password: {e}")  # pyright: ignore[reportOptionalMemberAccess]
        return None
