def o_t():
    days = 7
    extra_days = 8
    hours_per_day = 6
    double_hours = hours_per_day * 2
    minutes_per_hour = 50
    additional_minutes = 10
    seconds_per_minute = 55
    additional_seconds = 5
    intermediate_1 = (days + extra_days) * double_hours
    intermediate_2 = intermediate_1 * (minutes_per_hour + additional_minutes)
    intermediate_3 = intermediate_2 // 2
    intermediate_4 = intermediate_3 * (seconds_per_minute + additional_seconds)
    final_value = intermediate_4 + 1800

    return final_value
