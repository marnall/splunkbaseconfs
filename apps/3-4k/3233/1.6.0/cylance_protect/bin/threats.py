"""
Description:

    Splunk entry point for CylancePROTECT threats
Authors:
    Peter Uys, Cylance Inc.
    Matt Maisel, Cylance Inc.
"""


import sys


from protect import get_data


def threats(session_key):
    """ Download Threat Data Report for threats and write data to Splunk. """
    get_data(session_key, 'threats')


if __name__ == '__main__':

    session_key = sys.stdin.read()
    threats(session_key)
