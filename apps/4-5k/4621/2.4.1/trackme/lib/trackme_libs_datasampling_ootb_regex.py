#!/usr/bin/env python
# coding=utf-8

__author__ = "TrackMe Limited"
__copyright__ = "Copyright 2022-2026, TrackMe Limited, U.K."
__credits__ = "TrackMe Limited, U.K."
__license__ = "TrackMe Limited, all rights reserved"
__version__ = "0.1.0"
__maintainer__ = "TrackMe Limited, U.K."
__email__ = "support@trackme-solutions.com"
__status__ = "PRODUCTION"

# List of regular expressions and their corresponding labels
ootb_regex_list = [
    {"regex": r"^\{", "label": "json"},
    {
        "regex": r"^<\d*>\w{3}\s*\d{1,2}\s*\d{1,2}:\d{1,2}:\d{1,2}\s",
        "label": "syslog_rfc3164",
    },
    {
        "regex": r"^<\d*>\d*\s*\d{4}-\d{1,2}-\d{1,2}T\d{2}:\d{2}:\d{2}\.",
        "label": "syslog_rfc5424",
    },
    {
        "regex": r"^\[\w*]\s*\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}:\d{1,2}:\d{1,2},\d{1,3}",
        "label": "log4j",
    },
    {"regex": r"^<[^\s]*\sxmlns=", "label": "xml"},
    {"regex": r"^\w{3}\s\d{2}\s\d{4}\s\d{2}:\d{2}:\d{2}", "label": "wineventlog_etv"},
    {
        "regex": r"^type=[^\s]*\s*msg=\w*\(\d{2}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}\.\d{6}\)",
        "label": "auditd",
    },
    {
        "regex": r"^[^:]*:\[timestamp=\d{1,2}-\d{1,2}-\d{4}\s*\d{1,2}:\d{1,2}:\d{1,2}\.\d{3}",
        "label": "linux_syslog",
    },
    {
        "regex": r"\[\d{2}/\w{3}/\d{4}\s*\d{2}:\d{2}:\d{2}:\d+\]",
        "label": "access_log1",
    },
    {"regex": r"\[\d{2}/\w{3}/\d{4}\s*\d{2}:\d{2}:\d{2}\]", "label": "access_log2"},
    {"regex": r"^\w*\[\d*\]:\s*", "label": "syslog_no_timestamp"},
    {
        "regex": r"^\w{3}\s*\d{1,2}\s*\d{1,2}-\d{1,2}-\d{1,2}",
        "label": "raw_start_by_timestamp %b %d %H-%M-%S",
    },
    {
        "regex": r"^\w{3}\s*\d{1,2}\s*\d{1,2}:\d{1,2}:\d{1,2}:\d{3}",
        "label": "raw_start_by_timestamp %b %d %H:%M:%S:%3N",
    },
    {
        "regex": r"^\w{3}\s*\d{1,2}\s*\d{1,2}:\d{1,2}:\d{1,2}\.\d{3}",
        "label": "raw_start_by_timestamp %b %d %H:%M:%S.%3N",
    },
    {
        "regex": r"^\w{3}\s*\d{1,2}\s*\d{1,2}:\d{1,2}:\d{1,2}",
        "label": "raw_start_by_timestamp %b %d %H:%M:%S",
    },
    {
        "regex": r"^\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}:\d{1,2}:\d{1,2}",
        "label": "raw_start_by_timestamp %Y-%d-%m %H:%M:%S",
    },
    {
        "regex": r"^\d{4}-\d{1,2}-\d{1,2}\s*\d{1,2}-\d{1,2}-\d{1,2}",
        "label": "raw_start_by_timestamp %Y-%d-%m %H-%M-%S",
    },
    {
        "regex": r"^\d{1,2}-\d{1,2}-\d{4}\s*\d{1,2}:\d{1,2}:\d{1,2}",
        "label": "raw_start_by_timestamp %m-%d-%Y %H:%M:%S",
    },
    {
        "regex": r"^\d{1,2}/\d{1,2}/\d{4}\s*\d{1,2}:\d{1,2}:\d{1,2}",
        "label": "raw_start_by_timestamp %m/%d/%Y %H-%M-%S",
    },
    {
        "regex": r"^\d*,\d{1,2}/\d{1,2}/\d{2},\d{1,2}:\d{1,2}:\d{1,2}",
        "label": "raw_start_by_id_then_timestamp %m/%d/%y,%H:%M:%S",
    },
    {
        "regex": r"^\w{3}\s*\w{3}\s*\d{1,2}\s*\d{1,2}:\d{1,2}:\d{1,2}\s*\d{4}",
        "label": "raw_start_by_timestamp %a &b %d %H:%M:%S",
    },
    {"regex": r"^CEF:\d*\|", "label": "CEF_regular"},
    {"regex": r"^[^\s]*\sCEF:\d*\|", "label": "CEF_variation1"},
    {
        "regex": r"(?i)^current\s*time:\s*\d{1,2}-\d{1,2}-\d{4}\s*\d{1,2}:\d{1,2}\d{1,2}",
        "label": "raw_start_by_current_time_then_timestamp %d-%m-%Y %H:%M:%S",
    },
    {
        "regex": r"(?i)^(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\s*\d{1,2}\s*\w+\s*\d{4}\s*\d{1,2}:\d{1,2}:\d{1,2}",
        "label": "raw_start_by_timestamp %A %d %B %Y %H:%M:%S",
    },
    {
        "regex": r"^\d{4}\d{2}\d{2}\d{2}\d{2}\d{2}",
        "label": "raw_start_by_timestamp %Y%m%d%H%M%S",
    },
    {
        "regex": r'date="\d{4}-\d{1,2}-\d{1,2}" time="\d{1,2}:\d{1,2}:\d{1,2}"',
        "label": 'raw_start_by date="%Y-%m-%d" time="%H:%M:%S"',
    },
    {"regex": r"^\d+\.\d{6}\s*", "label": "raw_start_by_timestamp %s.%f"},
    {
        "regex": r"^\d{4}-\d{1,2}-\d{1,2}T\d{1,2}:\d{1,2}:\d{1,2}\s",
        "label": "raw_start_by_timestamp %Y-%m-%dT%H:%M:%S",
    },
    {
        "regex": r'^"\d{4}-\d{1,2}-\d{1,2}\s*\d{2}:\d{2}:\d{2}"\s',
        "label": 'raw_start_by_timestamp "%Y-%m-%d %H:%M:%S"',
    },
    {
        "regex": r"^\d{2}-\w{3}-\d{4}\s*\d{2}:\d{2}:\d{2}\s",
        "label": "raw_start_by_timestamp %d-%b-%Y %H:%M:%S",
    },
    {
        "regex": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}",
        "label": r"raw_start_by_timestamp %Y-%m-%dT%H:%M:%S\.%3N",
    },
    {
        "regex": r'^start_time="\w{3}\s*\w{3}\s*\d{2}\s*\d{2}:\d{2}:\d{2}\s*\d{4}"',
        "label": 'raw_start_by start_time="%a %b %d %H:%M:%S %Y',
    },
    {
        "regex": r'^InsertedAt="\d{4}-\d{2}-\d{2}\s*\d{2}:\d{2}:\d{2}"',
        "label": 'raw_start_by InsertedAt="%Y-%m-%d %H:%M:%S',
    },
    {
        "regex": r"^\d{4}/\d{2}/\d{2}\s*\d{2}:\d{2}:\d{2}\s",
        "label": "raw_start_by_timestamp %Y/%m/%d %H:%M:%S",
    },
    {
        "regex": r"^\w{3}\s*\d{1,2}\s*\w{3}\s*\d{4}\s*\d{1,2}:\d{1,2}:\d{1,2}\s",
        "label": "raw_start_by_timestamp %a %d %b %Y %H:%M:%S",
    },
    {"regex": r".*", "label": "raw_not_identified"},
]
