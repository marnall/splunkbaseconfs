#!/bin/sh

echo "signature..."
date
od -An -tu4 -N40 /dev/urandom
