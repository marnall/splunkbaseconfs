import json

from uuid import uuid4
from base64 import b64encode

import requests

import utils
import license


def validate_input(helper, definition):
    return None


def write_to_index(ew, source, data, helper, ocapi_hostname):
    event = helper.new_event(
        data=json.dumps(data),
        host=ocapi_hostname,
        index=helper.get_output_index(),
        source=source,
    )
    ew.write_event(event)


@license.license_required
def collect_events(helper, ew):
    # Get fields filled in the Data Input Form
    account                 = helper.get_arg('ocapi_credentials')
    hostname                = helper.get_arg('hostname')
    data_input_name         = helper.get_arg('name')
    endpoint                = helper.get_arg('endpoint')
    url                     = utils.urljoin(f"https://{hostname}", endpoint)
    # Validate the URL
    utils.enforce_secure_connection(url)
    unique_id               = str(uuid4())
    credentials             = account[u'username'] + ':' + account[u'password']
    basic_auth              = b64encode(credentials.encode('utf-8')).decode('utf-8')
    helper.log_info(
        f'Starting KPIs ingestion data_input={data_input_name} id={unique_id}'
    )
    try:
        response = requests.get(
            url,
            headers={
                'Content-Type': "application/x-www-form-urlencoded",
                'Authorization': "Basic " + basic_auth,
                'Accept': "*/*",
            }
        )
        response.raise_for_status()
        data = response.json()
        write_to_index(
            ew,
            endpoint,
            data,
            helper,
            hostname,
        )
        helper.log_info(
            f'Finished KPIs ingestion data_input={data_input_name} id={unique_id}'
        )
    except requests.exceptions.HTTPError as http_error_exc:
        helper.log_error(
            f"KPIs ingestion data_input={data_input_name} id={unique_id} exception={str(http_error_exc)}"
        )
        raise http_error_exc
    except Exception as exc:
        helper.log_error(
            f"KPIs ingestion data_input={data_input_name} id={unique_id} exception={str(exc)}"
        )
