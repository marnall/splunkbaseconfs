"""
Description:
    Splunk entry point for CylancePROTECT indicators

Authors:
    Peter Uys, Cylance Inc.
    Matt Maisel, Cylance Inc.
"""


import sys


from protect import get_data


def indicators(session_key):
    """ Download Threat Data Report for indicators and write data to Splunk. """
    get_data(session_key, 'indicators')


if __name__ == '__main__':

    session_key = sys.stdin.read()
    indicators(session_key)
