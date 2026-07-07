import os
import sys

ta_name = 'TA-claroty-add-on-for-splunk'
ta_lib_name = 'lib'

pattern = os.path.sep + 'etc' + os.path.sep + 'apps' + os.path.sep
new_paths = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ta_lib_name)]

for new_path in new_paths:
    if new_path not in sys.path:
        sys.path.insert(0, new_path)
