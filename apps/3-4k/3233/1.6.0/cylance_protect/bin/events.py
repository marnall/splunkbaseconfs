"""
Description:
    Splunk entry point for CylancePROTECT events

Authors:
    Peter Uys, Cylance Inc.
    Matt Maisel, Cylance Inc.
"""


import sys


from protect import get_data


def events(session_key):
    """ Download Threat Data Report for events and write data to Splunk. """
    get_data(session_key, 'events')


if __name__ == '__main__':

    session_key = sys.stdin.read()
    events(session_key)
