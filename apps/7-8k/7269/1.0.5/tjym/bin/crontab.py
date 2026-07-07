#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Project:
@File   :crontab.py
@Author :Imocence
@Date   :2024/4/29 
"""

import calendar
import itertools
import re
import threading
import time

PREDEFINED_SCHEDULE = {
    "@yearly": "0 0 1 1 *",
    "@annually": "0 0 1 1 *",
    "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0",
    "@daily": "0 0 * * *",
    "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *",
}

scheduler_job = True


def convert_predefined(line):
    line = line.strip()
    if not line.startswith("@"):
        return line

    if line not in PREDEFINED_SCHEDULE:
        raise ValueError("Unknown predefine: %s" % line)
    return PREDEFINED_SCHEDULE[line]


class CronParser(object):
    """
    Parse a crontab entry and return a dictionary.
    Parse and validate a field in a crontab entry.
    """
    name = None
    bounds = None
    range_pattern = re.compile(
        r"""
        (?P<min>\d+|\*)         # Initial value
        (?:-(?P<max>\d+))?      # Optional max upper bound
        (?:/(?P<step>\d+))?     # Optional step increment
        """,
        re.VERBOSE,
    )

    def normalize(self, source):
        return source.strip()

    def parse(self, source):
        groups = [self.get_values(group) for group in source.split(",")]
        groups = set(itertools.chain.from_iterable(groups))
        has_last = False
        if "LAST" in groups:
            has_last = True
            groups.remove("LAST")
        groups = sorted(groups)
        if has_last:
            groups.append("LAST")
        return groups

    def get_match_groups(self, source):
        match = self.range_pattern.match(source)
        if not match:
            raise ValueError("Unknown expression: %s" % source)
        return match.groupdict()

    def get_values(self, source):
        source = self.normalize(source)
        match_groups = self.get_match_groups(source)
        step = 1
        min_value, max_value = self.get_value_range(match_groups)

        if match_groups["step"]:
            step = self.validate_bounds(match_groups["step"])
        return self.get_range(min_value, max_value, step)

    def get_value_range(self, match_groups):
        if match_groups["min"] == "*":
            return self.bounds

        min_value = self.validate_bounds(match_groups["min"])
        if match_groups["max"]:
            # Cron expressions are inclusive, range is exclusive on upper bound
            max_value = self.validate_bounds(match_groups["max"]) + 1
            return min_value, max_value

        return min_value, min_value + 1

    def get_range(self, min_value, max_value, step):
        if min_value < max_value:
            return list(range(min_value, max_value, step))

        min_bound, max_bound = self.bounds
        diff = (max_bound - min_value) + (max_value - min_bound)
        return [(min_value + i) % max_bound for i in list(range(0, diff, step))]

    def validate_bounds(self, value):
        min_value, max_value = self.bounds
        value = int(value)
        if not min_value <= value < max_value:
            raise ValueError("{} value out of range: {}".format(self.name, value))
        return value


class MinuteParser(CronParser):
    name = "minutes"
    bounds = (0, 60)


class HourParser(CronParser):
    name = "hours"
    bounds = (0, 24)


class MonthDayParser(CronParser):
    name = "monthdays"
    bounds = (1, 32)

    def normalize(self, source):
        # Handle special case for last day of month
        source = super(MonthDayParser, self).normalize(source)
        if source == "L":
            source = ["LAST"]
        return source.replace("?", "*")


class MonthParser(CronParser):
    name = "months"
    bounds = (1, 13)
    month_names = calendar.month_abbr[1:]

    def normalize(self, month):
        month = super(MonthParser, self).normalize(month)
        month = month.lower()
        for month_num, month_name in enumerate(self.month_names, start=1):
            month = month.replace(month_name.lower(), str(month_num))
        return month


class WeekdayParser(CronParser):
    name = "weekdays"
    bounds = (0, 7)
    day_names = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]

    def normalize(self, day_of_week):
        day_of_week = super(WeekdayParser, self).normalize(day_of_week)
        day_of_week = day_of_week.lower()
        for dow_num, dow_name in enumerate(self.day_names):
            day_of_week = day_of_week.replace(dow_name, str(dow_num))
        return day_of_week.replace("7", "0").replace("?", "*")


second_parser = MinuteParser()
minute_parser = MinuteParser()
hour_parser = HourParser()
day_parser = MonthDayParser()
month_parser = MonthParser()
weekday_parser = WeekdayParser()


def parse_cron_tab(line):
    line = convert_predefined(line).split(' ')
    if len(line) < 6:
        for i in range(6 - len(line)):
            line.append("*")

    return {
        "second": second_parser.parse(line[0]),  # 秒
        "minutes": minute_parser.parse(line[1]),  # 分
        "hours": hour_parser.parse(line[2]),  # 时
        "monthdays": day_parser.parse(line[3]),  # 天
        "months": month_parser.parse(line[4]),  # 月
        "weekdays": weekday_parser.parse(line[5] if line[3] == '?' else '?'),  # 星期
        "ordinals": None,
    }


def parse_cron_time(cron_exp):
    cron_list = parse_cron_tab(cron_exp)
    cron_hours = cron_list['hours'][0]
    if len(str(cron_hours)) == 1:
        cron_hours = "0{}".format(cron_hours)
    cron_minutes = cron_list['minutes'][0]
    if len(str(cron_minutes)) == 1:
        cron_minutes = "0{}".format(cron_minutes)
    return "{}:{}".format(cron_hours, cron_minutes)


if __name__ == '__main__':
    print(parse_cron_time('0 6 16 * * *'))
    print("Time matched cron schedule: {}".format(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))))
