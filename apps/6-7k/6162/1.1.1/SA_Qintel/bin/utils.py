import arrow


def regex_match(string, pattern):

    for r in pattern:
        if r.match(string):
            return True

    return False


# https://hackersandslackers.com/extract-data-from-complex-json-python/
def extract_json_values(obj, key):
    """Pull all values of specified key from nested JSON."""
    arr = []

    def extract(obj, arr, key):
        """Recursively search for values of key in JSON tree."""
        if isinstance(obj, dict):
            for k, v in obj.items():
                if isinstance(v, (dict, list)):
                    if k == key:
                        arr.extend(v)
                    else:
                        extract(v, arr, key)
                elif k == key:
                    arr.append(v)
        elif isinstance(obj, list):
            for item in obj:
                extract(item, arr, key)
        return arr

    results = extract(obj, arr, key)
    return results


def timerange_check(event_time, first_seen, last_seen, time_window):

    # no timerange, return everything
    if time_window == 0:
        return True

    event_time = arrow.get(event_time).to('UTC')

    first_seen = arrow.get(first_seen)
    last_seen = arrow.get(last_seen)
    lower_range = last_seen.shift(days=-int(time_window))
    upper_range = last_seen.shift(days=+int(time_window))

    if event_time.is_between(first_seen, last_seen, '[]') or \
            event_time.is_between(lower_range, upper_range, '[]'):
        return True

    return False
