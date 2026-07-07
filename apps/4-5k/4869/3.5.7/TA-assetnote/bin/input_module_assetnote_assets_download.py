# encoding = utf-8

import json
import os
import sys
import time
from datetime import datetime
import ta_assetnote_declare
import logging
from custom_checkpoint_manager import FallbackCheckpointHelper

"""Special prefix added to each log message"""
LOG_PREFIX = "AssetNote"

"""Number of assets to load per page"""
ASSETS_PER_PAGE_COUNT = 25

# Graphql Query template to pull down assets. 
# {page_count} is set and {page_num} is incremented to pull down the assets 
# listing
ASSETS_GRAPHQL_QUERY_TEMPLATE = """

query {{
    assets(s:[{{
        field:"id",
        dir:ASC
    }}], f:[{pull_verified_assets},{pull_time_after}],count:{page_count},page:{page_num}) {{
        edges {{
            node {{
                ... on CloudAsset {{
                    cloudTags {{
                    edges {{
                        node {{
                        lastUpdated
                        key
                        value
                        }}
                    }}
                    }}
                    cloudAttributes {{
                    edges {{
                        node {{
                        lastUpdated
                        key
                        value
                        }}
                    }}
                    }}
                    activeARecords {{
                        edges {{
                            node {{
                                ... on ADnsRecord {{
                                    id,
                                    ipAddress
                                    asnNetwork
                                    asnOrganizationName
                                    asnNumber
                                }}
                            }}
                        }}
                    }},
                    activeCnameRecords {{
                        edges {{
                            node {{
                                ... on CnameDnsRecord {{
                                    id,
                                    subdomain,
                                    rawRecord
                                }}
                            }}
                        }}
                    }}
                }},
                ... on IpAsset {{
                    activeARecords {{
                        edges {{
                            node {{ 
                                ... on ADnsRecord {{
                                    id,
                                    ipAddress
                                    asnNetwork
                                    asnOrganizationName
                                    asnNumber
                                }}
                            }}
                        }}
                    }},
                    activeCnameRecords {{
                        edges {{
                            node {{
                                ... on CnameDnsRecord {{
                                    id,
                                    subdomain,
                                    rawRecord
                                }}
                            }}
                        }}
                    }}
                }},
                ... on SubdomainAsset {{
                    activeARecords {{
                        edges {{
                            node {{ 
                                ... on ADnsRecord {{
                                    id,
                                    ipAddress
                                    asnNetwork
                                    asnOrganizationName
                                    asnNumber
                                }}
                            }}
                        }}
                    }},
                    activeCnameRecords {{
                        edges {{
                            node {{
                                ... on CnameDnsRecord {{
                                    id,
                                    subdomain,
                                    rawRecord
                                }}
                            }}
                        }}
                    }}
                }},
                __typename,
    	        ... on BaseAsset {{
                asnOrganizationName
                asnNumber
                asnNetwork
                    humanName,
                    activeARecordCount,
        	    activeCnameRecordCount,
	            exposureRating,
            	    hasUnmanagedExposures,
	            activeARecordCount,
            	    onlinePortEntryCount,
                    isOnline,
	            onlineDnsEntryCount,
	            onlineTechnologyCount,
                    canBeMonitored,
	            assetGroupId,
	            assetGroupName,
	            assetType,
	            created,
	            sslCertificates {{
                    edges {{
                        node {{
                            id,
                            created,
                            dateExpires,
                            dateIssued,
                            dnsNames,
                            emails,
                            issuerCommonName,
                            issuerCountry,
                            issuerDn,
                            issuerOrganization,
                            issuerOrganizationalUnit,
                            lastUpdated,
                            locationCity,
                            locationCountry,
                            locationContinent,
                            locationCountryCode,
                            locationRegisteredCountry,
                            locationRegisteredCountryCode,
                            parsedFingerprintMd5,
                            parsedFingerprintSha1,
                            parsedFingerprintSha256,
                            parsedNames,
                            subjectCommonName,
                            subjectCountry,
                            subjectDn,
                            subjectOrganization
                        }}
                    }}
                }},
	            geoData {{
                        id,
                        city,
                        country
                    }},
	            host,
                    ... on IpAsset {{
                        ipAddress,
                        technologies {{
                            edges {{
                                node {{
                                    name
                                }}
                            }}
                        }},
                        services {{
                            edges {{
                                node {{
                                    service {{ name }},
                                    port,
                                    isActive,
                                    lastActive
                                }}
                            }}
                        }}
                    }},
                    ... on CloudAsset {{
                        ipAddress,
                        technologies {{
                            edges {{
                                node {{
                                    name
                                }}
                            }}
                        }},
                        services {{
                            edges {{
                                node {{
                                    service {{ name }},
                                    port,
                                    isActive,
                                    lastActive
                                }}
                            }}
                        }}
                    }},
                    ... on SubdomainAsset {{
                       ipAddress: subdomain,
                       technologies {{
                            edges {{
                                node {{
                                    name
                                }}
                            }}
                        }},
                        services {{
                            edges {{
                                node {{
                                    service {{ name }},
                                    port,
                                    isActive,
                                    lastActive
                                }}
                            }}
                        }}
                    }},
	            id,
	            importance,
 	            isMonitored,
    	            lastUpdated,
	            notificationsEnabled,
	            parentName,
	            risk,
	            verifiedStatus,
                    assetGroup {{
                        id,
                        name
                    }}
	        }}
            }}
        }},
        pageInfo {{
            hasNextPage,
            hasPreviousPage,
            startCursor,
            endCursor
        }}
    }}
}}
"""

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(LOG_PREFIX)

def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations"""
    pass

def collect_events(helper, ew):
    
    # Initialize fallback checkpoint helper
    checkpoint_helper = FallbackCheckpointHelper(helper, "TA-assetnote")
    
    # Get the values for all the user supplied options
    opt_assetnote_api_key = helper.get_arg('assetnote_account')['password']
    opt_assetnote_instance = helper.get_arg('assetnote_instance')
    opt_sleep_time_per_page = int(helper.get_arg('sleep_time_per_page'))
    opt_num_retries_per_page = int(helper.get_arg('num_retries_per_page'))
    opt_backoff_time_per_page_retry = int(helper.get_arg('backoff_time_per_page_retry'))
    opt_limit_num_pages_returned = int(helper.get_arg('limit_num_pages_returned'))
    opt_pull_verified_assets = bool(helper.get_arg('pull_verified_assets'))

    if opt_pull_verified_assets:
        opt_pull_verified_assets = '{op:EQ, field:"verifiedStatus", value:true}'
    else:
        opt_pull_verified_assets = ''
    
    last_pull_time = checkpoint_helper.get_check_point('assets_last_pull_time')

    if not last_pull_time:
        logger.info("ASSETS INFO: Last pull time checkpoint not set, pulling all data for assets from Assetnote.")
        opt_pull_datetime_after = '{field: "created", op: GT, value: "2000-01-01T00:00:00Z"}'
    else:
        opt_pull_datetime_after = f'{{field: "created", op: GT, value: "{last_pull_time}"}}'
        logger.info(f"ASSETS INFO: Last pull time checkpoint IS set. Pulling all data from {last_pull_time}.")

    # define a global parameters set
    all_params = {
        'assetnote_index': helper.get_output_index(),
        'assetnote_sourcetype': helper.get_sourcetype(),
        'assetnote_source': helper.get_input_type(),
        'assetnote_api_key': opt_assetnote_api_key,
        'assetnote_instance': opt_assetnote_instance,
        'sleep_time': opt_sleep_time_per_page,
        'backoff_time': opt_backoff_time_per_page_retry,
        'num_retries': opt_num_retries_per_page,
        'page_count': ASSETS_PER_PAGE_COUNT,
        'limit_pages_returned': opt_limit_num_pages_returned,
        'pull_verified_assets': opt_pull_verified_assets,
        'pull_time_after': opt_pull_datetime_after
    }
    
    # Logging all the current parameters
    logger.info(f"assetnote_index: {all_params['assetnote_index']}, "
                f"assetnote_sourcetype: {all_params['assetnote_sourcetype']}, "
                f"assetnote_api_key: REDACTED, "
                f"assetnote_instance: {all_params['assetnote_instance']}")

    logger.info(f"Requesting assets for instance: {all_params['assetnote_instance']} page-wise...")
    assets = []
    get_next_page = True
    all_params['page_num'] = 1

    while get_next_page:
        all_params['try'] = 0
        all_params['page_load_success'] = False
        
        while not all_params['page_load_success'] and all_params['try'] < all_params['num_retries']:
            all_params['try'] += 1

            logger.info(f"Try: {all_params['try']}. Requesting page: {all_params['page_num']} for assets from AssetNote...")
            graphql_query = ASSETS_GRAPHQL_QUERY_TEMPLATE.format(**all_params)
            url_to_call = f"https://{all_params['assetnote_instance']}.assetnotecloud.com/api/v2/graphql"
            method = "POST"
            auth_header = "X-ASSETNOTE-API-KEY"
            if 'assetnote_api_key' in all_params:
                if all_params['assetnote_api_key'].startswith('anmt_'):
                    auth_header = "X-ASSETNOTE-MACHINE-TOKEN"
            headers = {
                auth_header: all_params['assetnote_api_key'],
                "X-SPLUNK-VERSION": ta_assetnote_declare.version,
                "User-Agent": f"Splunk/Assetnote/TA-assetnote/{ta_assetnote_declare.version}"
            }
            payload = dict(query=graphql_query)
            try:
                # Attempt to make HTTP request to load the page with assets
                resp = helper.send_http_request(url=url_to_call,
                                                method=method, 
                                                payload=payload,
                                                headers=headers,
                                                verify=True,
                                                use_proxy=True,
                                                timeout=20)
                status_code = resp.status_code
                resp_text = resp.text
                    
            except Exception as e:
                # Log the exception occurred to log file
                status_code = -1
                err_class = str(e.__class__)
                raw_err_msg = str(e)
                logger.error(f"Error in send_http_request for page: {all_params['page_num']} for try: {all_params['try']}. "
                             f"Error: {err_class}, {raw_err_msg}")
                
            # Page was not loaded successfully, so wait for some time before
            # re-requesting the page
            if status_code == 200:
                all_params['page_load_success'] = True
            else:
                all_params['page_load_success'] = False
                logger.info(f"Sleeping {all_params['backoff_time']}s before requesting same page...")
                time.sleep(all_params['backoff_time'])
                
        logger.info(f"Checking if page: {all_params['page_num']} obtained successfully...")
            
        if (status_code == -1) or (status_code != 200 or "data" not in resp_text):
            logger.error(f"Error encountered when retrieving page: {all_params['page_num']}...")
            logger.error(f"Error: {resp_text}")
            get_next_page = False
            
        else:
            logger.info(f"Parsing page: {all_params['page_num']} response for assets as JSON...")
                 
            resp_json = resp.json()
            all_params['assets_count'] = 0
            logger.info("Listing the number of assets on the page obtained...")
            assets_on_page = resp_json['data']['assets']['edges']
            for asset_on_page in assets_on_page:
                assets.append(asset_on_page)
                all_params['assets_count'] = len(assets)
                
            logger.info(f"Number of assets after page: {all_params['page_num']} is: {all_params['assets_count']}")

            logger.info(f"Checking if another page exists from page: {all_params['page_num']} response...")
                
            logger.info("Calculating the number of assets in the page...")
            all_params['asset_count_per_page'] = len(assets_on_page)
            
            logger.info(f"Creating all {all_params['asset_count_per_page']} assets as an event...")
            new_event = helper.new_event(json.dumps(assets_on_page, indent=4),
                            index=all_params['assetnote_index'],
                            sourcetype=all_params['assetnote_sourcetype'],
                            source=all_params['assetnote_source'])
                            
            logger.info(f"Writing an event to Splunk index: {all_params['assetnote_index']}, "
                        f"sourcetype: {all_params['assetnote_sourcetype']}, "
                        f"source: {all_params['assetnote_source']}...")
            ew.write_event(new_event)
            
            logger.info("Checking if next page should be obtained...")
            get_next_page_in_resp = resp_json['data']['assets']['pageInfo']['hasNextPage']
            if get_next_page_in_resp:
                logger.info("Checking if limit of number of pages to return has been hit...")
                if all_params['limit_pages_returned'] > 0:
                    if int(all_params['page_num']) >= all_params['limit_pages_returned']:
                        logger.info("Limit hit! Stopping extraction of more pages...")
                        current_time = datetime.utcnow().isoformat()[:-3]+'Z'
                        checkpoint_helper.save_check_point('assets_last_pull_time', current_time)
                        get_next_page = False
            else:
                logger.info("Stopping as no indication if next page is available...")
                current_time = datetime.utcnow().isoformat()[:-3]+'Z'
                checkpoint_helper.save_check_point('assets_last_pull_time', current_time)    
                get_next_page = False
                    
            if get_next_page:
                logger.info("Incrementing page counter...") 
                all_params['page_num'] += 1
                
                logger.info(f"Next page to get: {all_params['page_num']}...")
                
                logger.info(f"Sleeping for {all_params['sleep_time']}s before requesting next page...")
                time.sleep(all_params['sleep_time'])