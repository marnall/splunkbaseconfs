import csv
import io


def _coerce_value(value):
    """Convert CSV string values to appropriate Python types.

    Preserves numeric precision for large integers like epoch timestamps
    that would otherwise be stored as scientific notation strings.
    """
    if not value:
        return value
    try:
        float_val = float(value)
        if float_val.is_integer():
            return int(float_val)
        return float_val
    except (ValueError, OverflowError):
        return value


def csv_convert(log_label, response_data, helper):
    helper.log_info(f'{log_label} Preparing to convert CSV file to JSON')
    if not response_data:
        helper.log_warning(f'{log_label} CSV data was empty, no events to convert')
        return []
    try:
        text = response_data.decode('utf-8-sig')
        reader = csv.reader(io.StringIO(text), delimiter=',')
        headers = next(reader)
        num_headers = len(headers)
        formatted_data = []
        for row in reader:
            data_dict = dict(zip(headers, (_coerce_value(v) for v in row)))
            if len(row) > num_headers:
                helper.log_debug(f'{log_label} CSV row has {len(row)} values but only {num_headers} headers — extra columns discarded')
            if len(row) < num_headers:
                for item in range(len(row), num_headers):
                    data_dict[headers[item]] = ''
            formatted_data.append(data_dict)
    except Exception as err:
        helper.log_error(f'{log_label} Unable to convert CSV to JSON: {err} — no data was passed to Splunk. Please correct the error or create a clone of the search with a JSON output.')
        raise ValueError(f'CSV to JSON conversion failed: {err}')

    helper.log_info(f'{log_label} CSV to JSON conversion completed — {len(formatted_data)} events produced from {num_headers} columns')
    return formatted_data
