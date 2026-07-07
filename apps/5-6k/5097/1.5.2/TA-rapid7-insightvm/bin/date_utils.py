import datetime

def datetime_to_string(datetime_object):
    if datetime_object is not None:
        return datetime_object.strftime('%Y-%m-%dT%H:%M:%S') + datetime_object.strftime('.%f')[:4] + 'Z'

# As per the api docs, dates or times are returned as strings in the ISO 8601 'extended' format. 
# When a date and time is returned (instant) the value is converted to UTC.
def string_to_datetime(date_str, asset_id=None, log_fn=None):
    parsed_date = None
    
    if date_str is not None:
        try:
            parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        except:
            pass

        if parsed_date is None:
            try:
                parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            except Exception as e:
                if log_fn:
                    log_fn("Date string not in expected format YYYY-MM-DD'T'hh:mm:ss[.nnn]Z for {}".format(asset_id))

    return parsed_date