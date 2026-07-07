##
## SPDX-FileCopyrightText: 2024 Splunk, Inc.
## SPDX-License-Identifier: LicenseRef-Splunk-8-2021
##
##
import import_declare_test
import splunk.admin as admin
import traceback
import requests as rq
import json
import time
from rsa_utils import get_proxy_settings
from rsa_utils import get_log_level
from solnlib import log
import jwt
from jwt.algorithms import RSAAlgorithm
from splunktaucclib.rest_handler.error import RestError


def account_validation(
    adminRestApiUrl, api_access_key, access_id_of_api, logger, session_key
):
    """
    Validates account configuration.
    :param adminRestApiUrl: Base URL of Admin REST API entered by user.
    :param api_access_key: Access Key entered by user.
    :param access_id_of_api: Access ID entered by user.
    :param logger: provides logger.
    :param session_key: session_key used for fetching proxy details.
    """

    logger = log.Logs().get_logger("splunk_ta_rsa_securid_cas_account_validation")
    log_level = get_log_level(session_key, logger)
    logger.setLevel(log_level)

    logger.info("Verifying account credentials for RSA SecurID instance.")
    if not api_access_key or not access_id_of_api or not adminRestApiUrl:
        raise RestError(
            400, "Provide all base URL of Admin REST API, Access ID and Access Key."
        )

    if "https://" not in adminRestApiUrl:
        raise RestError(
            400, "Provided base URL of Admin REST API must start with https."
        )

    proxy_settings = get_proxy_settings(session_key, logger)

    url = "{}/v1/adminlog/exportlogs?pageSize=1&pageNumber=0".format(adminRestApiUrl)
    private_key = api_access_key.encode("utf-8").decode("unicode_escape")
    claim_set = {
        "sub": access_id_of_api,
        "iat": int(time.time()),
        "exp": int(time.time() + 3600),
        "aud": adminRestApiUrl,
    }
    try:
        jwt.unregister_algorithm("RS256")
    except Exception:
        pass

    try:
        jwt.register_algorithm("RS256", RSAAlgorithm(RSAAlgorithm.SHA256))
    except Exception as exception:
        logger.error(
            "Error encountered while registering the JWT RS256 algorithm. Error: {}".format(
                exception
            )
        )
        raise RestError(400, "Could not encode the JWT token using the entered details")

    try:
        headers = {
            "Authorization": "Bearer {}".format(
                jwt.encode(
                    claim_set,
                    private_key,
                    algorithm="RS256",
                    headers={"typ": "JWT", "alg": "RS256"},
                )
            )
        }

        response = rq.request("GET", url, proxies=proxy_settings, headers=headers)

        if response.status_code != 200:
            if response.status_code == 403:
                apidata = json.loads(response.content)
                if "Access Id" in apidata["message"]:
                    msg = "Provided Access ID is incorrect."
                elif "Invalid audience" in apidata["message"]:
                    msg = "Provided base URL of Admin REST API is incorrect."
                else:
                    msg = "Provided Access Key is incorrect."
            else:
                msg = "Failed to verify RSA SecurID credentials"
                logger.error(
                    "Failure occurred while verifying credentials. Response code={} ({})".format(
                        response.status_code, response.content
                    )
                )
            logger.error("{}".format(msg))
            raise RestError(400, msg)
        else:
            apidata = json.loads(response.content)

    except RestError as e:
        logger.error(e)
        raise RestError(400, e)

    except json.decoder.JSONDecodeError as json_error:
        logger.error(
            "Provided base URL of Admin REST API is incorrect. Error: {}".format(
                json_error
            )
        )
        raise RestError(400, "Provided base URL of Admin REST API is incorrect.")

    except rq.ConnectionError as connection_error:
        logger.error("Connection Error: {}".format(connection_error))
        raise RestError(
            400,
            "Connection error! Check the base URL or your Admin REST or network settings.",
        )

    except rq.TooManyRedirects as too_many_redirects_error:
        logger.error("Too many redirect Error {}".format(too_many_redirects_error))
        raise RestError(400, "Too many redirects!")

    except rq.exceptions.RequestException as e:
        logger.error(
            "Error occured while connecting with given credentials {}".format(e)
        )
        raise RestError(
            400,
            "An error occurred while connecting with the given credentials. Make sure you have entered the correct Admin REST API base URL, Access ID, and Access Key.",
        )

    except ValueError:
        logger.error(
            "RSA key format is not supported: {}".format(traceback.format_exc())
        )
        raise RestError(400, "RSA key format is not supported.")

    except Exception as exception:
        logger.error(
            "Unable to reach RSA SecurID instance at {0}. Error: {1} \nTraceback: {2}".format(
                adminRestApiUrl, exception, traceback.format_exc()
            )
        )
        raise RestError(
            400,
            "Unable to reach server at {}. Check configurations and network settings.".format(
                adminRestApiUrl
            ),
        )
