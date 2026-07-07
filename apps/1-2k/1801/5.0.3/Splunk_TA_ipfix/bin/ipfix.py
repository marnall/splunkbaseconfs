# Copyright 2011-2014 Splunk, Inc.  All rights reserved
import sys

from IPFIX.ModInput import ModInput


if __name__ == "__main__":
    sys.exit(ModInput().run(sys.argv))
