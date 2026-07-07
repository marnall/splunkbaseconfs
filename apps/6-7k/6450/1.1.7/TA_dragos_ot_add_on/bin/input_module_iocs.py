# encoding = utf-8
import os
from datetime import datetime
import pytz
import time


from dragoslib import worldview_input_utils as dragos_worldview_input_utils
from dragoslib import app_config as dragos_app_config


def submit_request_to_platform_api(session, page_number, preferred_batch_size, **kwargs):

    time.sleep(dragos_app_config.AppConfig().dragos_worldview_fetch_wait_seconds())

    params = {}
    params['page_size'] = preferred_batch_size
    params['page'] = page_number
    params['updated_after'] = datetime.fromtimestamp(kwargs['unix_timestamp_checkpoint'], pytz.utc).isoformat()

    return session.get("/api/v1/indicators", params=params)


def write_splunk_item(dic_rest, helper, ew, dragos_input_utils):
    helper.logger.info("Writing {0} events to Splunk".format(len(dic_rest['indicators'])))

    # Create a splunk event
    for item in dic_rest['indicators']:
        obj_data = obj_data = dragos_input_utils.format_individual_data_item_for_splunk(item)

        event = dragos_input_utils.new_event_for_slunk(helper, obj_data)
        ew.write_event(event)

    return dic_rest['total_pages']

def validate_input(helper, definition):
    # We don't have access to the credentials the user has selected so there is minimal
    # validation that we can do. Just do some basics to make sure everything looks
    # broadly OK

    dragos_worldview_input_utils.WorldviewInputUtils().validate_input_parameters(
        helper, definition.parameters
    )

    timestamp_bookmark = definition.parameters.get('full_replacement_interval', None)
    if timestamp_bookmark:
        try:
            num_days = int(timestamp_bookmark)

            if num_days < 0:
                raise ValueError
        except ValueError as e:
            message = "Invalid full replacement interval value. Unable to convert '{0}' in an integer >= 0. If you are attempting to turn this setting off then leave it blank, otherwise enter a whole number of days.".format(timestamp_bookmark)
            helper.logger.error(message)
            raise ValueError(message)

        if num_days > dragos_app_config.AppConfig().dragos_worldview_max_full_replacement_interval_days():
            message = "Full replacement interval must be less than {0} days.".format(dragos_app_config.AppConfig().dragos_worldview_max_full_replacement_interval_days())
            helper.logger.error(message)
            raise ValueError(message)  

def collect_events(helper, ew):
    # Setup a sesion with the platform and do standard initialization for inputs
    dragos_worldview_input = dragos_worldview_input_utils.WorldviewInputUtils()
    session = dragos_worldview_input.collect_events_initialization(helper)

    unix_timestamp_now = dragos_worldview_input.datetime_to_unix_timestamp(datetime.now(pytz.utc))

    user_repull_in_days = helper.get_arg("full_replacement_interval")
    user_repull_in_seconds = 0
    user_repull_active = False
    if user_repull_in_days != None and user_repull_in_days != '' and int(user_repull_in_days) > 0:
        user_repull_active = True
        user_repull_in_days = int(user_repull_in_days)
        user_repull_in_seconds = user_repull_in_days * 24 * 60 * 60
        helper.logger.info("Full replacement interval being used. Days {0} (in seconds {1})".format(user_repull_in_days, user_repull_in_seconds))
    else:
        helper.logger.info("Full replacement interval not being used")
        user_repull_active = False

    # Additional procesing to determine timestamp if first run or retrieve the checkpoint
    # if its the nth run to only pull ther IOC diff
    helper.logger.info("Procesing ioc timestamp bookmark")
    token_name_timetamp = "{0}-{1}-{2}".format(helper.get_input_type(), list(helper.get_input_stanza().keys())[0], "timestamp")
    unix_timestamp_checkpoint = helper.get_check_point(token_name_timetamp)
    if unix_timestamp_checkpoint:
        helper.logger.info("Got existing timestamp checkpoint")
    else:
        helper.logger.info("No existing timestamp checkpoint")
        unix_timestamp_checkpoint = 0 # use default value of the start of the unix epoch
    
    # Additional processing to determine if we have hit the re-pull interval
    token_name_re_pull = "{0}-{1}-{2}".format(helper.get_input_type(), list(helper.get_input_stanza().keys())[0], "timestamp_re_pull")
    unix_timestamp_last_full_pull = 0
    if user_repull_active:
        helper.logger.info("Procesing ioc repull bookmark")
        unix_timestamp_last_full_pull= helper.get_check_point(token_name_re_pull)
        if unix_timestamp_last_full_pull:
            helper.logger.info("Got existing timestamp checkpoint")
            helper.logger.info("Last re-pull {0}    Interval in Seconds {1}    Now {2}".format(unix_timestamp_last_full_pull, user_repull_in_seconds, unix_timestamp_now))
            
            if unix_timestamp_now > (unix_timestamp_last_full_pull + user_repull_in_seconds):
                helper.logger.info("Repull interval hit, adjusting timetamp checkpoint")
                unix_timestamp_last_full_pull = unix_timestamp_now
                unix_timestamp_checkpoint = 0
            else:
                helper.logger.info("We haven't hit repull interval")
        else:
            helper.logger.info("No existing timestamp checkpoint defauling to now")
            unix_timestamp_last_full_pull = unix_timestamp_now    # Default to now as being the most recent pull if the bookmark doesn't exist
                                                                  # and don't adjust the checkpoint timestamp
        
    helper.logger.info("Current Timestamp checkpoint {0} ({1})".format(unix_timestamp_checkpoint, datetime.fromtimestamp(unix_timestamp_checkpoint, pytz.utc).isoformat()))
    helper.logger.info("Repull checkpoint {0} ({1})".format(unix_timestamp_last_full_pull, datetime.fromtimestamp(unix_timestamp_last_full_pull, pytz.utc).isoformat()))

    api_context = {
        "unix_timestamp_checkpoint": unix_timestamp_checkpoint,
        "unix_timestamp_now": unix_timestamp_now
    }

    dragos_worldview_input.collect_events_from_api(helper, ew, submit_request_to_platform_api, write_splunk_item, session=session, api_context=api_context)

    # save timestamp so that on the next run we only pickup new iocs
    helper.logger.info("New Timestamp checkpoint {0} ({1})".format(unix_timestamp_now, datetime.fromtimestamp(unix_timestamp_now, pytz.utc).isoformat()))
    helper.logger.info("Saving ioc bookmarks")
    helper.save_check_point(token_name_timetamp, unix_timestamp_now)
    helper.save_check_point(token_name_re_pull, unix_timestamp_last_full_pull)

   