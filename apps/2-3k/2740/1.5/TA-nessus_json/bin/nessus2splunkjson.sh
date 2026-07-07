#!/bin/bash

cd `dirname $(readlink -f $0)`
python nessus2splunkjson.py
