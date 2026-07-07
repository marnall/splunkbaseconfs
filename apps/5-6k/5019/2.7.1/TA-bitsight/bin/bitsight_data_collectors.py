import hashlib
import json
import traceback

import splunk.version as v
from solnlib.utils import is_true

from bitsight_utils import bitsight_api_call, create_event, get_app_version, checkpoint_handler
from bitsight_exceptions import BitsightException

# Constants for log messages and checkpoint keys
COLLECTING_DATA_MSG = 'collecting data for <{}> endpoint'
CHECKPOINT_FOUND_MSG = 'checkpoint found. Using <{}> value for checkpoint.'
CHECKPOINT_FOUND_MSG_2 = 'checkpoint found. Using <previously indexed> values for checkpoint.'
CHECKPOINT_KEY = '{}_{}_{}'
CHECKPOINT_KEY_2 = '{}_{}_{}_{}'
BENCHMARKING_CHECKPOINT_KEY = 'benchmarking_{}_{}_{}'
BENCHMARKING_CHECKPOINT_KEY_2 = 'benchmarking_{}_{}_{}_{}'


def get_headers_with_version(session_key):
    """Return headers."""
    headers = {
        'Accept': 'application/json',
        'X-BITSIGHT-CONNECTOR-NAME-VERSION': 'BitSight Security Performance Management for Splunk Add-On {}'.format(
            get_app_version(session_key)),
        'X-BITSIGHT-CALLING-PLATFORM-VERSION': 'Splunk-Enterprise {}'.format(v.__version__),
    }
    return headers


def company(params):
    """Method to create company info events."""
    params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))
    input_name = params['input_name']
    if is_true(params['input_item'].get('skip_checkpoint')):
        params['logger'].info(
            "Skipping checkpointing of companies data for input {} as"
            " the 'Skip Checkpoint' checkbox is selected.".format(input_name)
        )
        checkpoint_data = []
    else:
        if "is_benchmarking" in params.keys():
            checkpoint_key = BENCHMARKING_CHECKPOINT_KEY.format(
                input_name, params['endpoint_name'], params['company_name']
            )
        else:
            checkpoint_key = CHECKPOINT_KEY.format(input_name, params['endpoint_name'], params['company_name'])
        _, checkpoint_collection = checkpoint_handler(
            params['logger'], params['session_key'], params['meta_configs']
        )
        checkpoint_data = checkpoint_collection.get(checkpoint_key)
        if not checkpoint_data:
            checkpoint_data = []
        else:
            params['logger'].info(CHECKPOINT_FOUND_MSG.format(checkpoint_data))
    headers = get_headers_with_version(params['session_key'])
    headers['X-BITSIGHT-CUSTOMER'] = params['company_name'].encode('utf-8')
    headers['Authorization'] = params['auth_header']
    url = params['base_url'] + params['endpoint_url'].format(params['company_guid'])
    results = bitsight_api_call(params['meta_configs'], url, headers)
    results['End_Point'] = params['endpoint_name']
    results_hash = hashlib.sha512(str(results).encode()).hexdigest()
    if results_hash != checkpoint_data:
        results = json.dumps(results, sort_keys=True)
        event = create_event(params['input_item'], results)
        params['event_writer'].write_event(event)
        if not is_true(params['input_item'].get('skip_checkpoint')):
            checkpoint_collection.update(checkpoint_key, results_hash)
        params['logger'].info("Updated Info for {}".format(params['company_name']))
    else:
        params['logger'].info("No new info for {}. Skipping indexing.".format(params['company_name']))


def alerts_events(alerts_data, params):
    """Method to create event with alerts."""
    input_name = params['input_name']
    if not is_true(params['input_item'].get('skip_checkpoint')):
        checkpoint_key = '{}_alerts'.format(input_name)
        _, checkpoint_collection = checkpoint_handler(
            params['logger'], params['session_key'], params['meta_configs']
        )
    for i in alerts_data:
        i['End_Point'] = "v2_alerts"
        i["Data_Category"] = "alerts"
        i = json.dumps(i, sort_keys=True)
        event = create_event(params['input_item'], i)
        params['event_writer'].write_event(event)
    latest_alert_date = alerts_data[0]['alert_date']
    if not is_true(params['input_item'].get('skip_checkpoint')):
        checkpoint_collection.update(checkpoint_key, latest_alert_date)
    params['logger'].info("Successfully indexed {} alerts for {}.".format(len(alerts_data), input_name))


def alerts(params):
    """Method for bitsight alerts."""
    params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))
    input_name = params['input_name']
    if is_true(params['input_item'].get('skip_checkpoint')):
        checkpoint_data = params['input_item'].get('start_date')
        params['logger'].info(
            "Skipping checkpointing of alerts data for input {}"
            " as the 'Skip Checkpoint' checkbox is selected.".format(input_name)
        )
    else:
        checkpoint_key = '{}_alerts'.format(input_name)
        _, checkpoint_collection = checkpoint_handler(
            params['logger'], params['session_key'], params['meta_configs']
        )
        checkpoint_data = checkpoint_collection.get(checkpoint_key)
        if not checkpoint_data:
            checkpoint_data = params['input_item'].get('start_date')
        else:
            params['logger'].info(CHECKPOINT_FOUND_MSG.format(checkpoint_data))
    i = {
        'limit': 1000,
        'alert_date_gt': checkpoint_data,
        'sort': '-alert_date'
    }
    headers = get_headers_with_version(params['session_key'])
    headers['Authorization'] = params['auth_header']
    url = params['base_url'] + params['endpoint_url']
    result = bitsight_api_call(
        params['meta_configs'], url, headers, req_params=i)
    next_link = (result.get('links').get('next'))
    alrt = []
    if len(result.get('results')) == 0:
        return
    i['offset'] = 1000
    c_data = {}
    while next_link:
        c_data['next1'] = bitsight_api_call(
            params['meta_configs'], url, headers, req_params=i)
        next_link = (c_data['next1'].get('links').get('next'))
        result.get('results').extend(c_data['next1'].get('results'))
        i['offset'] = i['offset'] + 1000
    for i in result["results"]:
        try:
            if i['company_guid'] in params['selected_companies_guid_list']:
                i['Company'] = next(
                    item['company_name'] for item in params['selected_companies_map']
                    if item["company_guid"] == i['company_guid'])
                alrt.append(i)
        except KeyError:
            raise BitsightException(traceback.format_exc())
    if alrt:
        alerts_events(alrt, params)
    else:
        params['logger'].info('No alerts data to ingest.')


def _get_checkpoint_data(params):
    """Helper method to get checkpoint data."""
    input_name = params['input_name']
    if is_true(params['input_item'].get('skip_checkpoint')):
        params['logger'].info(
            "Skipping checkpointing of diligence_statistics data for input {}"
            " as the 'Skip Checkpoint' checkbox is selected.".format(input_name)
        )
        return [], None, None

    checkpoint_key = (
        BENCHMARKING_CHECKPOINT_KEY if "is_benchmarking" in params
        else CHECKPOINT_KEY
    ).format(input_name, params['endpoint_name'], params['company_name'])

    _, checkpoint_collection = checkpoint_handler(
        params['logger'], params['session_key'], params['meta_configs']
    )

    checkpoint_data = checkpoint_collection.get(checkpoint_key) or []
    if checkpoint_data:
        params['logger'].info(CHECKPOINT_FOUND_MSG_2)

    return checkpoint_data, checkpoint_collection, checkpoint_key


def risk_vector_data(params):
    """Method to create risk vector data events."""
    params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))

    # Get checkpoint data
    checkpoint_data, checkpoint_collection, checkpoint_key = _get_checkpoint_data(params)

    # Make API call
    headers = get_headers_with_version(params['session_key'])
    headers['Authorization'] = params['auth_header']
    url = params['base_url'] + params['endpoint_url'].format(params['company_guid'])
    res_list = bitsight_api_call(params['meta_configs'], url, headers)
    if (res_list.get("risk_vectors")):
        risk_data = res_list.get("risk_vectors")
        risk_vector = risk_data.keys()
        new_rv_count = 0
        for i in risk_vector:
            j = risk_data.get(i)
            j['End_Point'] = params['endpoint_name']
            j['risk_vector'] = i
            j['Company'] = params['company_name']
            j = json.dumps(j, sort_keys=True)
            result = hashlib.sha512(j.encode())
            result_hash = result.hexdigest()
            if checkpoint_data:
                if (result_hash not in checkpoint_data):
                    event = create_event(params['input_item'], j)
                    params['event_writer'].write_event(event)
                    checkpoint_data.append(result_hash)
                    new_rv_count += 1
            else:
                event = create_event(params['input_item'], j)
                params['event_writer'].write_event(event)
                checkpoint_data.append(result_hash)
                new_rv_count += 1
        if not is_true(params['input_item'].get('skip_checkpoint')) and checkpoint_collection:
            checkpoint_collection.update(checkpoint_key, checkpoint_data)
        params['logger'].info('Successfully indexed {} {} data for "{}".'.format(
            new_rv_count, params['endpoint_name'], params['company_name']))


def get_results_hash(data):
    """
    Method to generate hash digest.

    :data: Data to be hashed.
    :return: SHA512 hexdigest of data.
    """
    data = json.dumps(data, sort_keys=True)
    result = hashlib.sha512(data.encode())
    result_hash = result.hexdigest()
    return result_hash


def _get_dhs_checkpoint_data(params):
    """Helper method to get checkpoint data for dhs."""
    input_name = params['input_name']
    if is_true(params['input_item'].get('skip_checkpoint')):
        params['logger'].info(
            "Skipping checkpointing of diligence_historical-statistics data for input {}"
            " as the 'Skip Checkpoint' checkbox is selected.".format(input_name)
        )
        return [], None, None

    checkpoint_key = (
        BENCHMARKING_CHECKPOINT_KEY if "is_benchmarking" in params
        else CHECKPOINT_KEY
    ).format(input_name, params['endpoint_name'], params['company_name'])

    _, checkpoint_collection = checkpoint_handler(
        params['logger'], params['session_key'], params['meta_configs']
    )

    checkpoint_data = checkpoint_collection.get(checkpoint_key) or []
    if checkpoint_data:
        params['logger'].info(CHECKPOINT_FOUND_MSG_2)

    return checkpoint_data, checkpoint_collection, checkpoint_key


def d_h_s(params):
    """Method to hash events."""
    params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))
    url = params['base_url'] + params['endpoint_url'].format(params['company_guid'])
    headers = get_headers_with_version(params['session_key'])
    headers['Authorization'] = params['auth_header']
    res_list = bitsight_api_call(params['meta_configs'], url, headers)
    checkpoint_data, checkpoint_collection, checkpoint_key = _get_dhs_checkpoint_data(params)

    # Process results if available
    if not res_list.get("results"):
        params['logger'].info(
            'No Diligence Historical Statistics found for "{}". Skipping indexing'.format(params['company_name']))
        return

    # Process the data
    new_dhs_count = _process_dhs_data(res_list["results"], params, checkpoint_data)

    # Update checkpoint if needed
    if not is_true(params['input_item'].get('skip_checkpoint')) and checkpoint_collection:
        checkpoint_collection.update(checkpoint_key, checkpoint_data)

    # Log results
    params['logger'].info(
        'Successfully indexed {} Diligence Historical Statistics for "{}".'.format(
            new_dhs_count, params['company_name']))


def _process_dhs_data(data, params, checkpoint_data):
    """Process DHS data and update checkpoint."""
    new_dhs_count = 0
    for i in data:
        if (i.get("counts")):
            data2 = i.get("counts")
            for j in data2:
                j['date'] = i.get("date")
                j['grade'] = i.get("grade")
                j['End_Point'] = params['endpoint_name']
                j['Company'] = params['company_name']
                result_hash = get_results_hash(j)
                if (checkpoint_data and result_hash not in checkpoint_data) or not checkpoint_data:
                    j = json.dumps(j, sort_keys=True)
                    event = create_event(params['input_item'], j)
                    params['event_writer'].write_event(event)
                    checkpoint_data.append(result_hash)
                    new_dhs_count += 1

    return new_dhs_count


def _process_findings_pagination(params, risk, results, url, headers, req_params):
    """Helper method to process pagination for findings."""
    next_link = results.get('links', {}).get('next')
    c_data = {}
    pg = 1
    req_params['offset'] = 1000

    params['logger'].debug("Findings: Page {} of {} ({})".format(pg, params['company_name'], risk))
    params['logger'].debug("Got {} findings for {} on page {}".format(
        len(results.get('results', [])), params['company_name'], pg))

    while next_link:
        pg += 1
        c_data['next1'] = bitsight_api_call(
            params['meta_configs'], url, headers, req_params=req_params)
        next_link = c_data['next1'].get('links', {}).get('next')
        params['logger'].debug("Findings: Page {} of {} ({})".format(
            pg, params['company_name'], risk))
        params['logger'].debug("Got {} findings for {} on page {}".format(
            len(c_data.get('next1', {}).get('results', [])),
            params['company_name'],
            pg))
        results.get('results', []).extend(c_data.get('next1', {}).get('results', []))
        req_params['offset'] += 1000

    return results


def _get_findings_checkpoint_key(params, risk, input_name):
    """Helper method to get the checkpoint key for findings."""
    if "is_benchmarking" in params:
        return BENCHMARKING_CHECKPOINT_KEY_2.format(
            input_name,
            params['endpoint_name'],
            params['company_name'],
            risk.replace(" ", "_"))
    return CHECKPOINT_KEY_2.format(
        input_name,
        params['endpoint_name'],
        params['company_name'],
        risk.replace(" ", "_"))


def findings(params):
    """Method to get findings data."""
    params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))
    risk_categories = [
        {'risk_category': 'Diligence'},
        {'risk_category': "Compromised Systems"},
        {'risk_category': "User Behavior"}
    ]
    input_name = params['input_name']

    for risk_item in risk_categories:
        risk = risk_item['risk_category']
        req_params = {
            'risk_category': risk,
            'sort': "-last_seen",
            'limit': 1000,
            'expand': 'attributed_companies',
            'offset': 0
        }

        # Handle checkpointing
        if is_true(params['input_item'].get('skip_checkpoint')):
            checkpoint_data = params['input_item'].get('start_date')
            req_params['last_seen_gte'] = str(checkpoint_data)
            params['logger'].info(
                "Skipping checkpointing of findings data for input {}"
                " as the 'Skip Checkpoint' checkbox is selected.".format(input_name)
            )
        else:
            checkpoint_key = _get_findings_checkpoint_key(params, risk, input_name)
            _, checkpoint_collection = checkpoint_handler(
                params['logger'], params['session_key'], params['meta_configs']
            )
            checkpoint_data = checkpoint_collection.get(checkpoint_key)
            if not checkpoint_data:
                checkpoint_data = params['input_item'].get('start_date')
                req_params['last_seen_gte'] = str(checkpoint_data)
            else:
                req_params['last_seen_gt'] = str(checkpoint_data)
                params['logger'].info(CHECKPOINT_FOUND_MSG.format(checkpoint_data))

        # Prepare API call
        headers = get_headers_with_version(params['session_key'])
        headers['Authorization'] = params['auth_header']
        url = params['base_url'] + params['endpoint_url'].format(params['company_guid'])

        try:
            # Initial API call
            results = bitsight_api_call(
                params['meta_configs'],
                url,
                headers,
                req_params=req_params
            )

            # Check if we have valid results
            if not results or not results.get('results'):
                params['logger'].info(
                    'No findings found for "{}" ({}) on/after date {}. Skipping indexing'.format(
                        risk, params['company_name'], checkpoint_data
                    ))
                continue

            # Process pagination
            results['id'] = risk
            results['Company'] = params['company_name']

            # Process pagination if there are results
            if len(results.get('results', [])) > 0:
                results = _process_findings_pagination(
                    params, risk, results, url, headers, req_params)

            # Write findings
            write_findings(results, params)

        except Exception:
            # Do not save checkpoint or ingest any event and return if any error occurs
            params['logger'].error(
                "An error occurred while fetching findings data for {}. {}".format(
                    params['company_name'],
                    traceback.format_exc()
                )
            )
            return


def write_findings(result, params):
    """Method to write findings data for each page."""
    try:
        risk_vector = result.get('id')
        company = result.get('Company')
        input_name = params['input_name']
        if not is_true(params['input_item'].get('skip_checkpoint')):
            if "is_benchmarking" in params.keys():
                checkpoint_key = BENCHMARKING_CHECKPOINT_KEY_2.format(
                    input_name, params['endpoint_name'],
                    company,
                    risk_vector.replace(" ", "_"))
            else:
                checkpoint_key = CHECKPOINT_KEY_2.format(
                    input_name, params['endpoint_name'],
                    company,
                    risk_vector.replace(" ", "_"))
            _, checkpoint_collection = checkpoint_handler(
                params['logger'], params['session_key'], params['meta_configs']
            )

        results = result.get('results')
        latest_date = results[0]['last_seen']
        for res in results:
            res['risk_vector'] = risk_vector
            res['End_Point'] = params['endpoint_name']
            res['Company'] = company
            res = json.dumps(res, sort_keys=True)
            event = create_event(params['input_item'], res)
            params['event_writer'].write_event(event)
        if not is_true(params['input_item'].get('skip_checkpoint')):
            checkpoint_collection.update(checkpoint_key, latest_date)
        params['logger'].info("Indexed {} findings for {} ({})".format(len(results), company, risk_vector))
    except Exception:
        params['logger'].error(
            'An Unxpected error occurred while writing findings data: {}'.format(traceback.format_exc()))


def graph(params):
    """Method to populate graph."""
    params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))
    url = params['base_url'] + params['endpoint_url'].format(params['company_guid'])
    headers = get_headers_with_version(params['session_key'])
    headers['Authorization'] = params['auth_header']
    input_name = params['input_name']
    if is_true(params['input_item'].get('skip_checkpoint')):
        params['logger'].info(
            "Skipping checkpointing of graph data for input {}"
            " as the 'Skip Checkpoint' checkbox is selected.".format(input_name)
        )
        checkpoint_data = []
    else:
        if "is_benchmarking" in params.keys():
            checkpoint_key = BENCHMARKING_CHECKPOINT_KEY.format(
                input_name, params['endpoint_name'], params['company_name']
            )
        else:
            checkpoint_key = CHECKPOINT_KEY.format(input_name, params['endpoint_name'], params['company_name'])
        _, checkpoint_collection = checkpoint_handler(
            params['logger'], params['session_key'], params['meta_configs']
        )
        checkpoint_data = checkpoint_collection.get(checkpoint_key)
        if not checkpoint_data:
            checkpoint_data = []
        else:
            params['logger'].info(CHECKPOINT_FOUND_MSG_2)
    res_list = bitsight_api_call(params['meta_configs'], url, headers)
    rating_data = res_list.get("ratings")
    sorted_ratings = sorted(rating_data, key=lambda i: i['x'])
    count = 0
    for i in sorted_ratings:
        i['Rating_Date'] = i.pop('x')
        i['Rating'] = i.pop('y')
        i['End_Point'] = params['endpoint_name']
        i['Data_Category'] = "Ratings"
        i['Company'] = params['company_name']

        result_hash = get_results_hash(i)
        if (checkpoint_data and result_hash not in checkpoint_data) or not checkpoint_data:
            i = json.dumps(i, sort_keys=True)
            event = create_event(params['input_item'], i)
            params['event_writer'].write_event(event)
            count += 1
            checkpoint_data.append(result_hash)
    if not is_true(params['input_item'].get('skip_checkpoint')):
        checkpoint_collection.update(checkpoint_key, checkpoint_data)
    params['logger'].info("Indexed {} Ratings data for {}".format(count, params['company_name']))


def _get_findings_summary_checkpoint_data(params, input_name):
    """Helper method to get checkpoint data for findings summary."""
    if is_true(params['input_item'].get('skip_checkpoint')):
        params['logger'].info(
            "Skipping checkpointing of findings_summary data for input {}"
            " as the 'Skip Checkpoint' checkbox is selected.".format(input_name)
        )
        return [], None, None

    checkpoint_key = (
        BENCHMARKING_CHECKPOINT_KEY if "is_benchmarking" in params
        else CHECKPOINT_KEY
    ).format(input_name, params['endpoint_name'], params['company_name'])

    _, checkpoint_collection = checkpoint_handler(
        params['logger'], params['session_key'], params['meta_configs']
    )

    checkpoint_data = checkpoint_collection.get(checkpoint_key) or []
    if checkpoint_data:
        params['logger'].info(CHECKPOINT_FOUND_MSG_2)

    return checkpoint_data, checkpoint_collection, checkpoint_key


def _process_findings_stats(stats, result, params, checkpoint_data):
    """Process findings stats and write events."""
    counter = 0
    for stat in stats:
        for vuln in result:
            if stat.get('name') == vuln.get('display_name'):
                stat.update({
                    'severity': vuln.get('severity'),
                    'End_Point': params['endpoint_name'],
                    'end_date': params.get('end_date'),
                    'start_date': params.get('start_date'),
                    'Company': params['company_name']
                })

                result_hash = get_results_hash(stat)
                if not checkpoint_data or result_hash not in checkpoint_data:
                    event = create_event(params['input_item'], json.dumps(stat))
                    params['event_writer'].write_event(event)
                    counter += 1
                    checkpoint_data.append(result_hash)
    return counter, checkpoint_data


def findings_summary(params):
    """Method to get findings summary."""
    params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))
    url = params['base_url'] + params['endpoint_url'].format(params['company_guid'])
    headers = get_headers_with_version(params['session_key'])
    headers['Authorization'] = params['auth_header']

    # Get findings data
    res_list = bitsight_api_call(params['meta_configs'], url, headers)

    # Get checkpoint data
    checkpoint_data, checkpoint_collection, checkpoint_key = _get_findings_summary_checkpoint_data(
        params, params['input_name']
    )

    # Get vulnerability data
    request_url = 'https://service.bitsighttech.com/customer-api/v1/defaults/vulnerabilities'
    req_params = {'fields': 'name,display_name,description,severity'}
    result = bitsight_api_call(params['meta_configs'], request_url, headers, req_params=req_params)

    # Process findings
    counter = 0
    for finding in res_list:
        if finding.get('stats'):
            stats_count, checkpoint_data = _process_findings_stats(
                finding['stats'],
                result,
                {**params, 'end_date': finding.get('end_date'), 'start_date': finding.get('start_date')},
                checkpoint_data
            )
            counter += stats_count

    # Update checkpoint if needed
    if not is_true(params['input_item'].get('skip_checkpoint')) and checkpoint_collection:
        checkpoint_collection.update(checkpoint_key, checkpoint_data)
    params['logger'].info('Indexed {} findings summary for "{}"'.format(counter, params['company_name']))


def remediations(params):
    """Method to fetch remediation data."""
    try:
        params['logger'].info(COLLECTING_DATA_MSG.format(params['endpoint_name']))
        url = params['base_url'] + params['endpoint_url']
        headers = get_headers_with_version(params['session_key'])
        headers['Authorization'] = params['auth_header']
        checkpoint_data = params['input_item'].get('start_date')

        remediations_params = {}
        remediations_params['limit'] = 1000
        remediations_params['offset'] = 0
        remediations_params['company_guid'] = params['company_guid']
        remediations_params['created_time_gte'] = str(checkpoint_data)

        results = bitsight_api_call(
            params['meta_configs'],
            url,
            headers,
            req_params=remediations_params
        )
        if results:
            if len(results.get('results')) == 0:
                params['logger'].info('No remediations data found for company {}. '
                                      'Skipping indexing'.format(params['company_name']))
            else:
                next_link = results.get('links').get('next')
                c_data = {}
                remediations_params['offset'] = 1000
                pg = 1
                params['logger'].info("Remediations data: Page {}".format(pg))
                params['logger'].debug("Got {} results for on page {}".format(len(results.get('results')), pg))
                while next_link:
                    pg += 1
                    c_data['next1'] = bitsight_api_call(
                        params['meta_configs'], url, headers, req_params=remediations_params)
                    next_link = (c_data['next1'].get('links').get('next'))
                    params['logger'].debug("Remediations data: Page {} of {}".format(pg, params['company_name']))
                    params['logger'].debug("Got {} events for {} on page {}".format(
                        len(c_data.get('next1').get('results')), params['company_name'], pg))
                    results.get('results').extend(c_data['next1'].get('results'))
                    remediations_params['offset'] += 1000
                results_to_ingest = results.get("results")
                rmd_count = 0
                for res in results_to_ingest:
                    res["End_Point"] = params['endpoint_name']
                    res = json.dumps(res, sort_keys=True)
                    event = create_event(params['input_item'], res)
                    params['event_writer'].write_event(event)
                    rmd_count = rmd_count + 1
                params['logger'].info("Indexed {} remediation events for {}".format(rmd_count, params['company_name']))
        else:
            params['logger'].info('No remediation data response for company {}.'.format(params['company_name']))
    except Exception as e:
        params['logger'].error("Error fetching remediations data: {}".format(str(e)))
