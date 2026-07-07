import os
path_prefix = os.path.dirname(__file__)

class LaceworkAPIConfConstants:
    
    LW_API_FILENAME = "lacework-api"

    LW_API_STANZA = "api"

    LW_API_FIELD_DOMAIN = "domain"

    LW_API_GEN_ACCESS_TOKEN_URI = "/api/v1/access/tokens"

class StoragePasswordConfConstants:

    SP_API_TOKEN_STANZA = "lacework_api_token" # Same for both username and realm

    SP_CREDENTIAL_REALM = "lacework_api"

    SP_CREDENTIAL_KEYID = "lacework_api_keyid"

    SP_CREDENTIAL_SECRET = "lacework_api_secret"