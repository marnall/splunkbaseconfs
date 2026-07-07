#!/bin/bash

# Provides the full path during execution so we can determine which 'apps' directory is being used dynamically
source=$BASH_SOURCE[0]
fullPath=`echo $source | grep -Eo '^.*/TA_certificate_checker'`

python3 ${fullPath}/bin/certificate_checker.py
