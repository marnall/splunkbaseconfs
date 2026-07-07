# python imports
import datetime
import traceback

# local imports
import riskiq_common_utility as util
import riskiq_constants as constants


def create_splunk_events(helper, x, ew, customer, riskiq_source, n_report, delim):
    """
    Method to groom asset data for ingestion into Splunk and then ingest them.

    # Add _time,customers and brand keys.
    :param helper: Splunk helper class.
    :param ew: Splunk event writer class.
    :param x: asset data.
    :param customer: Customer name associated with the account/input.
    :param riskiq_source: Source associated with input.
    :param delim: delimiter.
    :return: None
    """
    n_report += 1
    x['_time'] = datetime.datetime.strftime(
        datetime.datetime.now(), '%m/%d/%Y %H:%M:%S')
    if 'brands' not in x or x['brands'] == '' or x['brands'] == [] or x['brands'] == ():
        x['brands'] = customer
    x['global_customer'] = customer
    formatted_data = util.dict_2_splunk(util.l_flat(x, delim))
    if formatted_data.startswith('REPORT '):
        # Customer asks for intermediate report to be created
        formatted_data = formatted_data[len('REPORT '):].format(n_report)
        n_report = -1
    event = helper.new_event(
        source=riskiq_source,
        index=helper.get_output_index(),
        sourcetype=helper.get_sourcetype(),
        data=formatted_data
    )
    ew.write_event(event)
    return n_report


def MainThread(arg_dict):
    """
    Main driver method for the data ingestion sequence of assets.

    :param arg_dict: arguments related to GI or Legacy assets.
    :return: None.
    """
    url = arg_dict['url']
    conf_time = arg_dict['conf_time']
    retrieve_assets = arg_dict['retrieve_assets']
    checkpoint_file = arg_dict['checkpoint_file']
    create_filter = arg_dict['create_filter']
    tags_filter = arg_dict['tags_filter']
    org_filter = arg_dict['org_filter']
    brands_filter = arg_dict['brands_filter']
    helper = arg_dict['helper']
    ew = arg_dict['ew']
    try:
        input_name = helper.get_input_stanza_names()
        helper.log_info(
            "Starting data collection for input {}".format(input_name))
        global_account = helper.get_arg('global_account')
        customer = global_account['customer_name'].strip()
        d_last_events = util.get_checkpoint(
            helper, checkpoint_file, input_name)
        helper.log_info("Found checkpoint for input: [{}] with value: {}".format(input_name, d_last_events))
        for _, post in enumerate(arg_dict['commands']):
            # Check if we want to collect only changed GI assets
            if arg_dict['only_changed_assets']:
                try:
                    # Checkpoints consists of epoch time and date
                    last_stored_time = d_last_events[(customer, post[0])]
                    old_conf_time = last_stored_time.split("---")[1]
                    _, updated_conf_time = util.get_only_changed_assets_fields(helper)
                    if old_conf_time == updated_conf_time:
                        last_stored_time = last_stored_time.split("---")[0]
                    else:
                        last_stored_time = updated_conf_time
                        conf_time = updated_conf_time

                except Exception as e:
                    helper.log_debug("No checkpoint found" + str(e))
                    # When empty returns all data till now
                    last_stored_time = conf_time

                # Store current datetime in PST timezone
                date_time_now = str(datetime.datetime.now(constants.PST))

                # Remove extra microseconds, timezone offset and add the conf_time
                current_time = date_time_now[:-9].replace(" ", "T")
                end_time = current_time
                if last_stored_time.strip() == "" or not last_stored_time:
                    start_time = "0"
                    last_stored_time = "0"
                    helper.log_info("Data collection till {}".format(end_time))
                else:
                    start_time = last_stored_time
                    helper.log_info("Data collection starting from {} till {}".format(
                        start_time, end_time))

                current_time = current_time + "---" + conf_time
                if retrieve_assets(
                        helper,
                        ew,
                        url=url,
                        js=create_filter(
                            post[1], "CONFIRMED", last_stored_time, end_time),
                        category=post[0],
                        tags_filter=tags_filter,
                        org_filter=org_filter,
                        brands_filter=brands_filter) >= 0:
                    d_last_events[(customer, post[0])] = current_time
                    util.set_checkpoint(helper, input_name, d_last_events)
                    helper.log_info("Checkpoint stored for input: [{}] with value: {}".format(
                        input_name, d_last_events))
            else:
                # check if we have already ran this command earlier today
                # we want it once a day max
                try:
                    lastdate = d_last_events[(customer, post[0])]
                except KeyError:
                    lastdate = None
                if lastdate is None or lastdate < datetime.date.today():
                    # We can run, Determine which function to call
                    helper.log_info(
                        'Extracting data for {0}: {1}'.format(customer, post[0]))

                    if retrieve_assets(
                            helper,
                            ew,
                            url=url,
                            js=post[1],
                            category=post[0],
                            tags_filter=tags_filter,
                            org_filter=org_filter,
                            brands_filter=brands_filter) >= 0:
                        d_last_events[(customer, post[0])
                                      ] = datetime.date.today()
                        util.set_checkpoint(helper, input_name, d_last_events)
                        helper.log_info("Checkpoint stored for input: [{}] with value: {}".format(
                            input_name, d_last_events))
    except Exception:
        helper.log_error('Exception Occured {}'.format(traceback.format_exc()))
