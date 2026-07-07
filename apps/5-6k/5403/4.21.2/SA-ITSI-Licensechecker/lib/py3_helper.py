# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

import sys
from splunk.clilib.bundle_paths import make_splunkhome_path

'''
py3_helper has some duplicated functions from similar helper in main ITSI application,
however we keep this duplication and eliminate any dependencies on other bundled ITSI apps and libraries
so that License checker module can be deployed separately in distributed setups
'''


############ i18n setup ################  # noqa: E266


def ugettext(message):
    """
    Translate a string message
    This method is also installed as "_" in builtins
    """
    return message


def ungettext(msgid1, msgid2, n):
    """
    Translate a string message with a number in it
    """
    return msgid1 if n == 1 else msgid2


# Check if i18n functions are available (or use stubs)
try:
    from splunk.appserver.mrsparkle.lib import i18n
    i18n.ugettext('test')  # try it out to check if it's functional
    ugettext = i18n.ugettext  # noqa: F811
    ungettext = i18n.ungettext  # noqa: F811
except Exception:
    '''No working i18n available - will use stubs for ugettext and ungettext'''

_ = ugettext

############ end of i18n setup ################  # noqa: E266


####################################################
# Python 3: specific types, functions and settings #
####################################################
string_type = (str, bytes)
ext_string_type = (str, bytes)

'''
Unicode type:
* in python3 it is a str, since strings are unicode by default
'''
unicode = str


def decode(string):
    '''
        a helper function to decode string:
        * in python3 decodes bytes into a str

        returns str
    '''
    if type(string) is bytes:
        return string.decode()
    return string


def to_bytes(string):
    '''
        a helper function to convert string to bytes:
        * in python3 converts string to bytes using UTF-8 encoding

        returns bytes
    '''
    if type(string) is str:
        return bytes(string, encoding='UTF-8')
    return string


import builtins
# global i18n definitions
builtins.__dict__['_'] = ugettext
builtins.__dict__['ungettext'] = ungettext
