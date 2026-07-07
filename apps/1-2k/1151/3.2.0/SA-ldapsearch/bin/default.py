#!/usr/bin/env python
# coding=utf-8
#
# Copyright (C) 2009-2021 Splunk Inc. All Rights Reserved.

"""

This module is utilised to set the packages directory path

"""

from os import path
from sys import modules, path as sys_path, stderr

def initialize_app():

    module_dir = path.dirname(path.realpath(__file__))
    packages = path.join(module_dir, 'packages')
    lib_path = path.join(module_dir, '../lib')
    sys_path.insert(0, path.join(packages))
    sys_path.insert(0, path.join(lib_path))

initialize_app()
