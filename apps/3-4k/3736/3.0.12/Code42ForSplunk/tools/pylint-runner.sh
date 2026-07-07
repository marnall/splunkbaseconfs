#!/usr/bin/env bash

cd "$(dirname "${BASH_SOURCE[0]}")"
find ../bin -maxdepth 1 -name "*.py" -exec pylint -E {} \;