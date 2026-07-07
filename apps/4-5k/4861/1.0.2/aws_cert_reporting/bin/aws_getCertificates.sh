#!/bin/bash
aws iam list-server-certificates --max-items 10000000 --page-size 500
