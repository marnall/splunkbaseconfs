# encoding = utf-8


import json
from datetime import datetime
from azure_ta_nxtp.graph import Request, ManagementConnection, strip_empties_from_dict

"""
    IMPORTANT
    Edit only the validate_input and collect_events functions.
    Do not edit any other part in this file.
    This file is generated only once when creating the modular input.
"""
"""
# For advanced users, if you want to create single instance mod input, uncomment this method.
def use_single_instance_mode():
    return True
"""


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    # This example accesses the modular input variable
    # tenant_id = definition.parameters.get('tenant_id', None)
    # client_id = definition.parameters.get('client_id', None)
    # client_secret = definition.parameters.get('client_secret', None)


def collect_events(helper, ew):
    # helper.log_info(
    #     f"Start running Azure activity log collection from {start_from} till {datetime.now(tz=timezone)}"
    # )
    api_manager = ManagementConnection(helper)
    apps = []
    credentials = {}
    startTime = datetime.now().timestamp()
    for raw_app in Request(connection=api_manager, endpoint=f"applications", mode="GET").run():
        app = {}
        app["id"] = raw_app.get("id", None)  # unique identifier for directoryObject
        app["app_id"] = raw_app.get("appId", None)  # unique identifier for the application
        app["app_name"] = raw_app.get("displayName", None)  # display name for the application
        app["description"] = raw_app.get("description", None)
        app["app_creation_timestamp"] = datetime.strptime(
            raw_app.get("createdDateTime"), "%Y-%m-%dT%H:%M:%SZ"
        ).timestamp()
        app["template_id"] = raw_app.get(
            "applicationTemplateId", None
        )  # identifier for applicationTemplate
        app["template_name"] = (
            list(
                Request(
                    connection=api_manager,
                    endpoint=f"applicationTemplates/{app['template_id']}",
                    mode="GET",
                ).run()
            )[0]["displayName"]
            if app["template_id"]
            else None
        )
        if not app["template_id"] or app["template_id"] == "NotDisabled":
            app["status"] = "enabled"
        else:
            app["status"] = "disabled"
        app["app_url"] = raw_app.get("identifierUris", None)
        if app["app_url"]:
            try:
                app["app_domain"] = urlparse(app["app_url"]).netloc
            except:
                pass
        app["notes"] = raw_app.get("notes", None)
        app["authentication_method"] = (
            "device" if raw_app.get("isDeviceOnlyAuthSupported", False) else "user"
        )
        if raw_app.get("tags") and raw_app.get("tags") != []:
            app["tags"] = raw_app.get("tags")
        app["publisher_domain"] = app.get("publisherDomain", None)
        # signInAudience - 	Specifies the Microsoft accounts that are supported for the current application.
        if raw_app.get("signInAudience") == "AzureADMyOrg":
            app["app_audience"] = "single-tenant"
        elif raw_app.get("signInAudience") == "AzureADMultipleOrgs":
            app["app_audience"] = "multi-tenant"
        elif raw_app.get("signInAudience") == "AzureADandPersonalMicrosoftAccount":
            app["app_audience"] = "all-authenticated"
        elif raw_app.get("signInAudience") == "PersonalMicrosoftAccount":
            app["app_audience"] = "personal"
        # tokenEncryptionKeyId - Specifies the keyId of a public key from the keyCredentials collection. When configured, Azure AD encrypts all the tokens it emits by using the key this property points to. The application code that receives the encrypted token must use the matching private key to decrypt the token before it can be used for the signed-in user.
        # defaultRedirectUri
        # certification
        # optionalClaims - Application developers can configure optional claims in their Azure AD applications to specify the claims that are sent to their application by the Microsoft security token service
        # info -> https://docs.microsoft.com/en-us/graph/api/resources/informationalurl?view=graph-rest-1.0
        # info.logoUrl - CDN URL to the application's logo, Read-only.
        # info.marketingUrl - Link to the application's marketing page
        # info.privacyStatementUrl - Link to the application's privacy statement.
        # info.supportUrl - Link to the application's support page.
        # info.termsOfServiceUrl - Link to the application's terms of service statement.
        # keyCredentials - The collection of key credentials associated with the application.
        if raw_app.get("keyCredentials") and raw_app.get("keyCredentials") != []:
            app["app_key"] = []
            for credential in raw_app.get("keyCredentials"):
                app["app_key"].append(credential["keyId"])
        # passwordCredentials - The collection of password credentials associated with the application.
        if raw_app.get("passwordCredentials") and raw_app.get("passwordCredentials") != []:
            app["app_password"] = []
            for credential in raw_app.get("passwordCredentials"):
                app["app_password"].append(credential["keyId"])
        if raw_app.get("verifiedPublisher") and isinstance(
            raw_app.get("passwordCredentials"), dict
        ):
            # verifiedPublisher.displayName - The verified publisher name from the app publisher's Partner Center account.
            if raw_app["verifiedPublisher"]["displayName"] is not None:
                app["app_vendor_name"] = raw_app["verifiedPublisher"]["displayName"]
            # verifiedPublisher.verifiedPublisherId - 	The ID of the verified publisher from the app publisher's Partner Center account.
            # verifiedPublisher.addedDateTime - The timestamp when the verified publisher was first added or most recently updated.

        # spa - Specifies settings for a single-page application, including sign out URLs and redirect URIs for authorization codes and access tokens.
        if raw_app.get("spa") and isinstance(raw_app.get("spa"), dict):
            # spa.redirectUris - Specifies settings for a single-page application, including sign out URLs and redirect URIs for authorization codes and access tokens.
            if raw_app["spa"]["redirectUris"] is not None and raw_app["spa"]["redirectUris"] != []:
                app["app_redirect_url"] = raw_app["spa"]["redirectUris"]
        # publicClient - Specifies settings for installed clients such as desktop or mobile devices.
        if raw_app.get("publicClient") and isinstance(raw_app.get("publicClient"), dict):
            # publicClient.redirectUris - Specifies the URLs where user tokens are sent for sign-in, or the redirect URIs where OAuth 2.0 authorization codes and access tokens are sent.
            if (
                raw_app["publicClient"]["redirectUris"] is not None
                and raw_app["publicClient"]["redirectUris"] != []
            ):
                app["app_redirect_url"] = raw_app["publicClient"]["redirectUris"]
        # web - Specifies settings for a web application.
        if raw_app.get("web") and isinstance(raw_app.get("web"), dict):
            if raw_app["web"]["logoutUrl"] is not None:
                app["app_logon_url"] = raw_app["web"]["logoutUrl"]
            if raw_app["web"]["redirectUris"] is not None and raw_app["web"]["redirectUris"] != []:
                app["app_redirect_url"] = raw_app["web"]["redirectUris"]

        if app.get("app_redirect_url") and app.get("app_redirect_url") is not []:
            try:
                app["app_redirect_host"] = list(
                    set([urlparse(url).netloc for url in app["app_redirect_url"]])
                )
            except:
                pass
        app = strip_empties_from_dict(app)

        # Get the Application Owner from a seperate Query
        owner_email = []
        owner_id = []
        for owner in Request(
            connection=api_manager,
            endpoint=f"applications/{app['id']}/owners",
            params={"$select": "id,mail"},
            mode="GET",
        ).run():
            owner_email.append(owner["mail"])
            owner_id.append(owner["id"])
        if len(owner_email) > 0:
            app["owner_email"] = owner_email
            app["owner_id"] = owner_id
        ew.write_event(
            helper.new_event(
                source=f"{helper.get_input_type()}:{helper.get_arg('tenant_id')}",
                index=helper.get_output_index(),
                sourcetype=f"azure:application",
                data=json.dumps(app),
            )
        )
        # app["raw_data"] = raw_app
        # console.print_json(data=app)

        apps.append(app)
        if raw_app.get("passwordCredentials") and not raw_app.get("passwordCredentials") == []:
            helper.log_debug(f'{raw_app.get("passwordCredentials")}')
            secrets = raw_app.get("passwordCredentials")
            credential_type = "password"
            for secret in secrets:
                id = secret["keyId"]
                if id in credentials:
                    credentials[id]["app_id"].append(raw_app.get("appId", None))
                    continue
                credentials[id] = {}
                credentials[id]["id"] = id
                credentials[id]["credential_type"] = credential_type
                credentials[id]["app_id"] = [raw_app.get("appId", None)]
                if secret.get("displayName") and secret.get("displayName") is not None:
                    credentials[id]["description"] = secret.get("displayName")
                if secret.get("startDateTime"):
                    credentials[id]["start_timestamp"] = datetime.strptime(
                        secret.get("startDateTime")[:19], "%Y-%m-%dT%H:%M:%S"
                    ).timestamp()
                if secret.get("endDateTime"):
                    credentials[id]["end_timestamp"] = datetime.strptime(
                        secret.get("endDateTime")[:19], "%Y-%m-%dT%H:%M:%S"
                    ).timestamp()
        if raw_app.get("keyCredentials") and not raw_app.get("keyCredentials") == []:
            helper.log_debug(f'{raw_app.get("keyCredentials")}')
            secrets = raw_app.get("keyCredentials")
            credential_type = "key"
            for secret in secrets:
                id = secret["keyId"]
                if id in credentials:
                    credentials[id]["app_id"].append(raw_app.get("appId", None))
                    continue
                credentials[id] = {}
                credentials[id]["id"] = id
                credentials[id]["credential_type"] = credential_type
                credentials[id]["app_id"] = [raw_app.get("appId", None)]
                credentials[id]["description"] = secret.get("displayName", None)
                if secret.get("startDateTime"):
                    print(secret)
                    credentials[id]["start_timestamp"] = datetime.strptime(
                        secret.get("startDateTime")[:19], "%Y-%m-%dT%H:%M:%S"
                    ).timestamp()
                if secret.get("endDateTime"):
                    credentials[id]["end_timestamp"] = datetime.strptime(
                        secret.get("endDateTime")[:19], "%Y-%m-%dT%H:%M:%S"
                    ).timestamp()
                if secret.get("type") and secret.get("type") is not None:
                    credentials[id]["credential_key_type"] = secret.get("type")
                if secret.get("usage") and secret.get("usage") is not None:
                    credentials[id]["credential_usage"] = secret.get("usage")

    for credential in credentials.values():
        ew.write_event(
            helper.new_event(
                source=f"{helper.get_input_type()}:{helper.get_arg('tenant_id')}",
                index=helper.get_output_index(),
                sourcetype=f"azure:credential",
                data=json.dumps(credential),
            )
        )
    helper.log_debug(f"Fetched {len(apps)} apps and {len(credentials)} credentials in {datetime.now().timestamp() - startTime:.2f} seconds.")