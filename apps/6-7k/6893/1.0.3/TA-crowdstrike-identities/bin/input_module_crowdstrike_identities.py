
# encoding = utf-8

from falconpy import IdentityProtection
from crowdstrike_identities_version import *
import json
from time import time
from zts_helper import *


def validate_input(helper, definition):
    pass


def collect_events(helper, ew):
    log_level = helper.get_log_level()
    helper.set_log_level(log_level)
    helper.log_info(f'log_level="{log_level}"')

    api_credentials = helper.get_arg('api_credentials')
    api_clientid = api_credentials['username']
    api_secret = api_credentials['password']
    cloud_env = helper.get_arg('cloud_environment')
    domains_to_exclude = helper.get_arg('domains_to_exclude')
    domains_to_include = helper.get_arg('domains_to_include')
    user_agent = f'zTsSplunkTAFalconIdentities/{APP_VERSION}'
    stanza = str(helper.get_input_stanza_names())
    hostname = f'crowdstrike/{cloud_env}'

    proxy = helper.get_proxy()
    event_type = 'proxy_config'
    if proxy:
        if proxy["proxy_username"]:
            event_log = zts_logger(
                msg='Proxy is configured with authentication',
                action='success',
                event_type=event_type,
                stanza=stanza,
                hostname=hostname
            )
            helper.log_info(event_log)
            proxy_string = f'{proxy["proxy_type"]}://{proxy["proxy_username"]}:{proxy["proxy_password"]}@{proxy["proxy_url"]}:{proxy["proxy_port"]}'
        else:
            event_log = zts_logger(
                msg='Proxy is configured with no authentication',
                action='success',
                event_type=event_type,
                stanza=stanza,
                hostname=hostname
            )
            helper.log_info(event_log)
            proxy_string = f'{proxy["proxy_type"]}://{proxy["proxy_url"]}:{proxy["proxy_port"]}'

        proxy_config = {'http': proxy_string, 'https': proxy_string}
    else:
        event_log = zts_logger(
            msg='Proxy is not configured',
            action='success',
            event_type=event_type,
            stanza=stanza,
            hostname=hostname
        )
        helper.log_info(event_log)
        proxy_config = None

    idp_query = """
    query ($after: Cursor, $first: Int) 
    {
        entities(
            types: [USER]
            archived: false
            first: $first
            after: $after
            ~~~DOMAIN_FILTER~~~
        ) {
            nodes {
                entityId
                learned
                archived
                primaryDisplayName
                secondaryDisplayName
                markTime
                type
                watched
                isHuman: hasRole(type: HumanUserAccountRole)
                riskScore
                riskScoreSeverity
                riskFactors {
                    type
                    severity
                }
                roles { 
                    type
                    fullPath
                    probability
                }
                isProgrammatic: hasRole(type: ProgrammaticUserAccountRole) ... on UserEntity {
                    emailAddresses
                }
                accounts { 
                    description
                    dataSource
                    creationTime
                    ... on ActiveDirectoryAccountDescriptor {
                        passwordAttributes {
                            lastChange
                        }
                        creationTime
                        objectSid
                        samAccountName
                        domain
                        enabled
                        dn
                        department
                        ou
                        servicePrincipalNames
                        upn
                        title
                        userAccountControl
                        objectGuid
                        lastUpdateTime
                    }
                }
            }
            pageInfo {
                hasNextPage
                endCursor
            }
        }
    }
    """

    get_data = True
    query_vars = {"first": 1000}
    if domains_to_include:
        domain_filter = f'including: {domains_to_include}'
        i = domains_to_include.replace(" ", "")
        idp_query = idp_query.replace("~~~DOMAIN_FILTER~~~", f'domains: {json.dumps(i.split(","))}')
    elif domains_to_exclude:
        domain_filter = f'excluding: {domains_to_exclude}'
        e = domains_to_exclude.replace(" ", "")
        idp_query = idp_query.replace("~~~DOMAIN_FILTER~~~", f'not: {{domains: {json.dumps(e.split(","))}}}')
    else:
        domain_filter = None
        idp_query = idp_query.replace("~~~DOMAIN_FILTER~~~", "")
    page_count = 0
    start_time = time()
    identity_count = 0

    event_type = 'api_call'
    event_log = zts_logger(
        msg='Sending request',
        action='started',
        event_type=event_type,
        stanza=stanza,
        hostname=hostname,
        base_url=cloud_env,
        user_agent=user_agent,
        query_vars=json.dumps(query_vars),
        domain_filter=domain_filter
    )
    helper.log_info(event_log)

    falcon = IdentityProtection(client_id=api_clientid,
                                client_secret=api_secret,
                                base_url=cloud_env,
                                user_agent=user_agent,
                                ssl_verify=True,
                                proxy=proxy_config
                                )

    while get_data:
        page_count += 1
        response = falcon.graphql(query=idp_query, variables=query_vars)

        if response["status_code"] != 200:
            error_msg = response["body"]["errors"]
            event_log = zts_logger(
                msg='Request failed',
                action='failure',
                event_type=event_type,
                stanza=stanza,
                hostname=hostname,
                http_status_code=response["status_code"],
                error_message=json.dumps(error_msg),
                base_url=cloud_env,
                user_agent=user_agent
            )
            helper.log_error(event_log)
            raise SystemExit(response["status_code"])

        if response["body"]["data"].get("entities"):
            if "nodes" in response["body"]["data"]["entities"]:
                returned_identities = response["body"]["data"]["entities"]["nodes"]
                page_info = response["body"]["data"]["entities"]["pageInfo"]

                # Index Events
                for identity in returned_identities:
                    identity_count += 1
                    splunk_event = helper.new_event(source=helper.get_input_type(), index=helper.get_output_index(
                    ), sourcetype=helper.get_sourcetype(), data=json.dumps(identity), host=hostname)
                    ew.write_event(splunk_event)

                if page_info["hasNextPage"]:
                    query_vars["after"] = page_info["endCursor"]
                else:
                    get_data = False
            else:
                get_data = False
        else:
            event_log = zts_logger(
                msg="No data returned.",
                action="none",
                event_type=event_type,
                stanza=stanza,
                hostname=hostname
            )
            helper.log_info(event_log)
            raise SystemExit()

    event_log = zts_logger(
        msg='Finished collection',
        action='success',
        event_type=event_type,
        stanza=stanza,
        hostname=hostname,
        base_url=cloud_env,
        user_agent=user_agent,
        time_taken_sec=time() - start_time,
        identity_count=identity_count,
        page_count=page_count
    )
    helper.log_info(event_log)

    raise SystemExit()

