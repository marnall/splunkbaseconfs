#!/bin/bash

LC_ALL=C sadf -t -s $(date -d "2 min ago" +%H:%M:%S) -- -A
