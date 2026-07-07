#!/bin/bash
# Instructions for use:
## bash ./upgrade_sdk.md
### This is a non-executable file, that has the below command.
### Run this command to upgrade the SDK if needed.
pip install --upgrade carbon-black-cloud-sdk -t .
find . -name "*.yaml" -exec chmod -x {} \;