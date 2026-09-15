import os
import sys
from os.path import dirname

bin_dir = dirname(__file__)
app_dir = dirname(bin_dir)
ta_name = os.path.basename(app_dir)

# Standard UCC import order:
# 1. App-specific bin subdirectory, 2. app lib directory, 3. app bin directory.
sys.path.insert(0, bin_dir)
sys.path.insert(0, os.path.join(app_dir, "lib"))
sys.path.insert(0, os.path.join(bin_dir, ta_name))
