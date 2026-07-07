# python imports
import json
import sys
import base64
import calendar
import datetime
import traceback
import requests

# local imports
import iso8601
import riskiq_common_utility as util
import riskiq_constants as constants


def createeventfilter(dt):
    """Method to create filters for API call for events endpoint."""
    return({'filters': [
        {'filters': [{'field': 'updatedAt', 'type': 'GTE', 'value': dt}]}]})


def validate_input(helper, definition):
    """Implement your own validation logic to validate the input stanza configurations."""
    pass


def ingest_data_into_splunk(helper, ew, **kwargs):
    """
    Method to ingest event data into Splunk.

    :param helper: Splunk helper class.
    :param ew: Splunk event writer class.
    :param result: data to be ingested.
    :param last_updated_time: last updated time from checkpoint.
    :param customer: customer name associated with the account/input.
    :param eventnum: number of events.
    :param checkpoint: checkpoint value.
    :return: eventnum and checkpoint.
    """
    result = kwargs['result']
    last_updated_time = kwargs['last_updated_time']
    customer = kwargs['customer']
    eventnum = kwargs['eventnum']
    checkpoint = kwargs['checkpoint']
    n_report = kwargs['n_report']
    try:
        last_event_updated_time = result['Results'][-1]['updated']
        epoch_time = int(calendar.timegm(iso8601.parse_date(
            last_event_updated_time).utctimetuple()))
        milliseconds = last_event_updated_time.split('.')[1][:3]
        latest_event_time = int(str(epoch_time) + str(milliseconds))

        # Loop only if the last event has time > checkpoint.
        if latest_event_time > last_updated_time:
            checkpoint = str(latest_event_time) + "---" + \
                str(last_event_updated_time.split('T')[0])
            for x in result['Results']:
                # Add _time,customers and brand keys
                x['_time'] = datetime.datetime.strftime(
                    datetime.datetime.now(), '%m/%d/%Y %H:%M:%S')
                if 'brands' not in x or x['brands'] == '' or x['brands'] == [] or x['brands'] == ():
                    x['brands'] = customer
                x['customer'] = customer

                # Get the created time in epoch
                event_time = int(calendar.timegm(
                    iso8601.parse_date(x['updated']).utctimetuple()))
                # Catch the milliseconds as they will be ignored by iso8601
                milliseconds = x['updated'].split('.')[1][:3]
                event_time = int(str(event_time) + str(milliseconds))

                # Index only if new event is collected
                if event_time > last_updated_time:
                    eventnum += 1
                    n_report += 1
                    formatted_data = util.dict_2_splunk(
                        util.l_flat(x, delim=";"))
                    if formatted_data.startswith('REPORT '):
                        # Customer asks for intermediate report to be created
                        formatted_data = formatted_data[len(
                            'REPORT '):].format(n_report)
                        n_report = -1
                    event = helper.new_event(
                        source=helper.get_input_type(),
                        index=helper.get_output_index(),
                        sourcetype=helper.get_sourcetype(),
                        data=formatted_data
                    )
                    ew.write_event(event)
            helper.log_info("Number of new events indexed " + str(eventnum))
        return eventnum, checkpoint, n_report
    except Exception:
        helper.log_error(
            "Failed to ingest data into splunk - {}".format(traceback.format_exc()))
        sys.exit()


def retrieve_events(
    helper,
    ew,
    page_size,
    customer,
    input_name,
    client_token,
    proxies,
    filters_time,
    last_updated_time
):
    """
    Method to retrieve events data from the RiskIQ API.

    :param helper: Splunk helper class.
    :param ew: Splunk event writer class.
    :param page_size: page_size.
    :param customer: Customer name associated with the account/input.
    :param input_name: Name of current input.
    :param client_token: Client token for RiskIQ API.
    :param proxies: Configured proxies.
    :param filters_time: Time filters for API request.
    :param last_updated_time: Last updated time from checkpoint.
    :return: None.
    """
    try:
        b_more = True
        scroll = None
        i_len = 0
        eventnum = 0
        url = constants.EVENTS_URL + "&results={}".format(page_size)
        checkpoint = None
        d_last_events = {}
        n_report = 0
        while b_more:
            theurl = url
            if scroll:
                theurl = theurl.split(
                    '?')[0] + '?sort=updatedAt&order=ASC&results={}'.format(
                        page_size) + '&scroll=' + scroll

            try:
                headers = {"Authorization": "Basic " + client_token.decode(),
                           "Content-Type": "application/json"}
                response = requests.post(url=theurl,
                                         headers=headers,
                                         data=json.dumps(
                                             createeventfilter(filters_time)),
                                         verify=constants.SSL_VERIFY,
                                         proxies=proxies)
            except Exception as e:
                helper.log_warning('API request failed: {0}'.format(str(e)))
                sys.exit()

            try:
                response.raise_for_status()
            except Exception as e:
                helper.log_warning(
                    'Unexpected response code {0}'.format(str(e)))
                helper.log_warning('Response:{0}'.format(repr(response)))
                sys.exit()

            # Result is dict with keys: offset Results totalResults
            try:
                result = response.json()
            except Exception as e:
                helper.log_warning(
                    'Could not interpret json response from {0}'.format(
                        theurl))
                helper.log_warning('Response:{0} error {1}'.format(
                    repr(response), str(e)))
                sys.exit()

            try:
                scroll = result['scroll']
            except KeyError:
                scroll = None

            i_len += len(result['Results'])
            helper.log_debug("Number of results returned from API are : {}"
                             .format(str(len(result['Results']))))
            eventnum, checkpoint, n_report = ingest_data_into_splunk(
                helper,
                ew,
                result=result,
                last_updated_time=last_updated_time,
                customer=customer,
                eventnum=eventnum,
                checkpoint=checkpoint,
                n_report=n_report)
            b_more = (i_len < int(result['totalResults']))
    except Exception as e:
        helper.log_error('Data Collection Failed : {0}'.format(str(e)))
    finally:
        if checkpoint:
            d_last_events[(customer, "EVENTS")] = checkpoint
            util.set_checkpoint(helper, input_name, d_last_events)
            helper.log_info("Checkpoint saved with value: {}".format(checkpoint))
        else:
            helper.log_info(
                "No new checkpoint found for input {}".format(input_name))
        helper.log_info(
            "Collected {} data for input {}".format(eventnum, input_name))


def collect_events(helper, ew):
    """Splunk default collect event method for core logic of data collection and ingestion."""
    input_name = helper.get_input_stanza_names()
    helper.log_info("Starting data collection for input {}".format(input_name))

    global_account = helper.get_arg('global_account')
    token = global_account['api_key'].strip()
    key = global_account['api_secret'].strip()
    customer = global_account['customer_name'].strip()
    page_size = helper.get_arg('page_size').strip()
    session_key = helper.context_meta['session_key']
    try:
        try:
            events_checkpoint = util.get_checkpoint(
                helper, 'last_events', input_name)
            # Checkpoints consists of epoch time and date
            checkpoints = events_checkpoint[(customer, "EVENTS")].split('---')
            last_epoch_time = int(checkpoints[0])
            filters_time = checkpoints[1]
        except KeyError as e:
            helper.log_info("No old checkpoint found for EVENTS" + str(e))
            # When empty returns all data till now
            filters_time = ''
            last_epoch_time = 0
        except Exception:
            helper.log_info("Unknown error occurred while fetching checkpoint. {}".format(traceback.format_exc()))
            filters_time = ''
            last_epoch_time = 0

        helper.log_info('Last checkpoint with time ' + str(last_epoch_time))
        if page_size != '':
            page_size = int(page_size)
        else:
            page_size = 100
        if customer.strip() == "":
            helper.log_error("Customer name cannot be empty")
            sys.exit()

        proxies = util.get_proxy_uri(session_key)
        client_token = (token + ":" + key).encode()
        base64_client_token = base64.b64encode(client_token)
        retrieve_events(helper, ew, page_size, customer, input_name,
                        base64_client_token, proxies, filters_time, last_epoch_time)
        helper.log_info('Script exiting....')
        sys.exit()
    except Exception:
        helper.log_error('Exception Occured {}'.format(traceback.format_exc()))
