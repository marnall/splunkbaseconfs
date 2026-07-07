# Test cases:
#
# 1. Z present, fractional seconds <= 6 digits -> unchanged
# "2025-12-02T07:38:53.6Z" -> "2025-12-02T07:38:53.6Z"
# "2025-12-02T07:38:53.677Z" -> "2025-12-02T07:38:53.677Z"
# "2025-12-02T07:38:53.677123Z" -> "2025-12-02T07:38:53.677123Z"
#
# 2. Z present, fractional seconds > 6 digits -> Exception
# "2025-12-02T07:38:53.6771239Z" -> "Exception"
# "2025-12-02T07:38:53.677123999Z" -> "Exception"
#
# 3. No Z, fractional seconds <= 6 digits -> add Z
# "2025-12-02T07:38:53.6" -> "2025-12-02T07:38:53.6Z"
# "2025-12-02T07:38:53.677123" -> "2025-12-02T07:38:53.677123Z"
#
# 4. No Z, fractional seconds > 6 digits -> Exception
# "2025-12-02T07:38:53.6771239" -> "Exception"
#
# 5. No fractional seconds -> add fractional seconds
# "2025-12-02T07:38:53" -> "2025-12-02T07:38:53.000000Z"
# "2025-12-02T07:38:53Z" -> "2025-12-02T07:38:53.000000Z"
def normalize_iso_datetime(date_str: str) -> str:
    """
       Normalize a timestamp, so it can be parsed by datetime.strptime(value, "%Y-%m-%dT%H:%M:%S.%fZ")
    """

    # Z present and fractional seconds are valid for strptime (≤ 6 digits)
    if date_str.endswith("Z") and "." in date_str:
        frac = date_str[:-1].split(".", 1)[1]
        if len(frac) <= 6:
            return date_str
        else:
            raise Exception(f"Invalid date string: {date_str}")
    elif date_str.endswith("Z") and "." not in date_str:
        # No fractional seconds present ex: 2025-12-02T07:38:53Z
        # datetime.strptime with "%Y-%m-%dT%H:%M:%S.%fZ" requires %f,
        # so we explicitly add ".000000" to make parsing succeed.
        updated_date_str = date_str.replace("Z", ".000000Z")
        return updated_date_str
    else:
        if "." in date_str:
            main, frac = date_str.split(".", 1)
            if len(frac) <= 6:
                return f"{main}.{frac}Z"
            else:
                raise Exception(f"Invalid date string: {date_str}")
        else:
            return f"{date_str}.000000Z"
