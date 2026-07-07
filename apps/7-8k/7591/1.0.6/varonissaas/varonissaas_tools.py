# File: varonissaas_test.py
#
# Copyright (c) Varonis, 2024-2025
#
# This unpublished material is proprietary to Varonis SaaS. All
# rights reserved. The methods and techniques described herein are
# considered trade secrets and/or confidential. Reproduction or
# distribution, in whole or in part, is forbidden except by express
# written permission of Varonis SaaS.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an 'AS IS' BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND,
# either express or implied. See the License for the specific language governing permissions
# and limitations under the License.

from collections import deque
from datetime import datetime, timezone
from itertools import groupby, islice
from typing import Any, Optional

import dateparser


def try_convert(item, converter, error=None):
    """Try to convert item

    :type item: ``Any``
    :param item: An item to convert

    :type converter: ``Any``
    :param converter: Converter function

    :type error: ``Any``
    :param error: Error object that will be raised in case of error convertion

    :return: A converted item or None
    :rtype: ``Any``
    """
    if item:
        try:
            return converter(item)
        except Exception:
            if error:
                raise error
            raise
    return None


def urljoin(url, suffix):
    if url[-1:] != "/":
        url = url + "/"

    if suffix.startswith("/"):
        suffix = suffix[1:]
        return url + suffix

    return url + suffix


def arg_to_datetime(interval: Any, is_utc=True) -> Optional[datetime]:
    """Converts an interval to a datetime

    :type interval: ``Any``
    :param arg: argument to convert

    :type is_utc: ``bool``
    :param is_utc: if True then date converted as utc timezone, otherwise will convert with local timezone.

    :return:
        returns an ``datetime`` if conversion works
        returns ``None`` if arg is ``None``
        otherwise throws an Exception
    :rtype: ``Optional[datetime]``
    """

    if interval is None:
        return None

    if (isinstance(interval, str) and interval.isdigit()) or isinstance(interval, (int, float)):
        # timestamp is a str containing digits - we just convert it to int
        ms = float(interval)
        if ms > 2000000000.0:
            # in case timestamp was provided as unix time (in milliseconds)
            ms = ms / 1000.0

        if is_utc:
            return datetime.utcfromtimestamp(ms).replace(tzinfo=timezone.utc)
        else:
            return datetime.fromtimestamp(ms)
    if isinstance(interval, str):
        # we use dateparser to handle strings either in ISO8601 format, or
        # relative time stamps.
        # For example: format 2019-10-23T00:00:00 or "3 days", etc

        date = dateparser.parse(interval, settings={"TIMEZONE": "UTC"})

        if date is None:
            # if d is None it means dateparser failed to parse it
            raise ValueError(f'"{interval}" is not a valid date')

        return date

    raise ValueError(f'"{interval}" is not a valid date+')


def numeric_to_date(interval: Any, is_utc=True) -> Optional[datetime]:
    if isinstance(interval, str) and interval.isdigit():
        return arg_to_datetime(f"{interval} day", is_utc)

    return arg_to_datetime(interval, is_utc)


def multi_value_to_string_list(arg, separator=","):
    """
    Converts a string representation of args to a python list

    :type arg: ``str`` or ``list``
    :param arg: Args to be converted (required)

    :type separator: ``str``
    :param separator: A string separator to separate the strings, the default is a comma.

    :return: A python list of args
    :rtype: ``list``
    """
    if not arg:
        return []
    if isinstance(arg, list):
        return arg
    if isinstance(arg, str):
        return [s.strip() for s in arg.split(separator)]
    return [arg]


def strEqual(text1: str, text2: str) -> bool:
    if not text1 and not text2:
        return True
    if not text1 or not text2:
        return False

    return text1.casefold() == text2.casefold()


def parse_bool(value: str) -> Optional[bool]:
    if value:
        value = value.lower()
        if value == "yes":
            return True
        if value == "no":
            return False
        if value == "true":
            return True
        if value == "false":
            return False
        if value == "1":
            return True
        if value == "0":
            return False
    return None


def parse_bool_list(value: str) -> str:
    if value:
        parsed = [str(parse_bool(x.strip())) for x in value.split(sep=",")]
        return ",".join(parsed)
    return None


def convert_json_to_key_value(data: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for row in data["rows"]:
        obj = {}
        for col, val in zip(data["columns"], row):
            obj[col] = val
        result.append(obj)
    return result


def new_construct(obj: Any) -> Any:
    if obj is None:
        return None
    return [] if isinstance(obj, list) else {}


def isliteral(obj: Any):
    return isinstance(obj, (int, float, str, bool))


def object_to_dict(obj):
    result = new_construct(obj)
    queue = deque([(id(obj), obj, result)])
    processed = set()

    while queue:
        obj_id, obj, constructed_obj = queue.pop()
        if obj_id in processed:
            continue
        processed.add(obj_id)

        if hasattr(obj, "__dict__"):
            obj = vars(obj)

        if isinstance(obj, list):
            for val in obj:
                if isliteral(val):
                    constructed_obj.append(val)
                elif isinstance(val, datetime):
                    constructed_obj.append(val.strftime("%Y-%m-%dT%H:%M:%S.%f%z"))
                else:
                    new_obj = new_construct(val)
                    queue.append((id(val), val, new_obj))
                    constructed_obj.append(new_obj)
        elif isinstance(obj, dict):
            for key, val in obj.items():
                if isliteral(val):
                    constructed_obj[key] = val
                elif isinstance(val, datetime):
                    constructed_obj[key] = val.strftime("%Y-%m-%dT%H:%M:%S.%f%z")
                else:
                    new_obj = new_construct(val)
                    constructed_obj[key] = new_obj
                    queue.append((id(val), val, new_obj))

    return result


def convert_level(level: str, levels: list[str]) -> list[str]:
    if level is None:
        return []
    result = levels.copy()
    for lev in levels:
        if level == lev:
            break
        result.remove(lev)
    return result


def group_by(data: list[Any], key_func: Any) -> dict[str, list[Any]]:
    data = sorted(data, key=key_func)
    grouping = groupby(data, key=key_func)
    result = {}
    for k, g in grouping:
        result[k] = list(g)
    return result


def batched(iterable, n):
    if n < 1:
        return []
    it = iter(iterable)
    while batch := list(islice(it, n)):
        yield batch
