#
# SPDX-FileCopyrightText: 2024 Splunk, Inc.
# SPDX-License-Identifier: LicenseRef-Splunk-8-2021
#
#
import re
from datetime import datetime

from splunktaucclib.rest_handler.endpoint.validator import Validator


class QuartzValidation(object):
    def __init__(self):
        self._month = (
            "JAN",
            "FEB",
            "MAR",
            "APR",
            "MAY",
            "JUN",
            "JUL",
            "AUG",
            "SEP",
            "OCT",
            "NOV",
            "DEC",
        )
        self._week = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")

    def validate(self, cron):
        if not cron:
            return False

        cron = cron.strip()

        if cron in (None, ""):
            return False

        items = cron.split(" ")
        if len(items) != 6:
            return False

        return self._cron_validate(items)

    def _cron_validate(self, items):
        sec, minute, hour, day, month, week = items
        if not self._validate_field(sec, 0, 59, "-*/"):
            return False

        if not self._validate_field(minute, 0, 59, "-*/"):
            return False

        if not self._validate_field(hour, 0, 23, "-*/"):
            return False

        if not self._validate_field(day, 1, 31, "-*/?LW"):
            return False

        if not self._validate_field(month, 1, 12, "-*/", self._month):
            return False

        if not self._validate_field(week, 0, 59, "-*/?L#", self._week):
            return False

        return True

    def _validate_field(self, field, min_val, max_val, chars, enum=None):
        if field.count("#") > 1:
            return False

        if not field.strip():
            return False

        for item in field.split(","):
            if item.count("/") > 1:
                return False

            regex = "[{}]".format("".join(chars))
            regex = regex.replace("-", "\\-").replace("*", "\\*").replace("?", "\\?")
            if self._has_negative_number(item, regex):
                return False

            for exp in re.split(regex, item):
                if not exp:
                    continue
                if not self._value_in_range(exp, min_val, max_val):
                    if enum:
                        if exp not in enum:
                            return False
                    else:
                        return False

        return True

    def _has_negative_number(self, item, regex):
        regex = regex.replace("\\-", "")
        exps = re.split(regex, item)
        for exp in exps:
            try:
                exp = int(exp)
            except Exception:
                continue
            if exp < 0:
                return True
        return False

    def _value_in_range(self, val, min_val, max_val):
        try:
            val = int(val)
        except Exception:
            return False
        if max_val >= val >= min_val:
            return True
        return False


class IntervalValidation(Validator):
    def __init__(self, *args, **kwargs):
        super(IntervalValidation, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        result = QuartzValidation().validate(data["interval"])
        if not result:
            msg = "Enter the valid value for field 'Interval'."
            self.put_msg(msg, True)
            return False
        else:
            return True


class DateValidator(Validator):
    """
    This class validates if the date passed for starttime in input is in future.
    If so, throws error in UI.
    """

    def __init__(self, *args, **kwargs):
        super(DateValidator, self).__init__(*args, **kwargs)

    def validate(self, value, data):
        try:
            input_date = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
            now = datetime.utcnow()
            if input_date > now:
                self.put_msg("Start date should not be in future", True)
                return False

        except ValueError as exc:
            self.put_msg(str(exc))
            return False
        return True
