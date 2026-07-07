#!/bin/bash

unset LD_LIBRARY_PATH

cd $( dirname "${BASH_SOURCE[0]}" )
./alert_json.py
