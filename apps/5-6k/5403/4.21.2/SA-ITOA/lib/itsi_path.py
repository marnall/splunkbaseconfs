# Copyright (C) 2005-2025 Splunk Inc. All Rights Reserved.

"""
Update as of ITSI-40383:
    Unfortunately, we don't have a perfect way of doing the `sys.path` hackery, since we need to add `SA-ITOA/lib/` to
    import this file to begin with. This means that the `sys.path` at some point in execution may be filled with
    multiple copies of `SA-ITOA/lib/` at the end to ensure no errors. I don't want to be copying `add_to_sys_path()` to
    like every file...

    In a better world, we would only use `sys.path` hackery in the entrance points to our code, but our libraries are
    not written cleanly like that.

    In a perfect world, we wouldn't be using `sys.path` hackery to begin with. Perhaps we could do something with
    modifying `$PYTHONPATH` in the future...
"""

import os
import sys

try:
    from splunk.clilib.bundle_paths import make_splunkhome_path
except ImportError:
    # Added the below method for DATF compatibility
    # TODO: [HX] Remove as part of DATF cleanup
    def make_splunkhome_path(path_list):
        relpath = os.path.normpath(os.path.join(*path_list))
        splunk_home = os.environ.get("SPLUNK_HOME", '')
        fullpath = os.path.normpath(os.path.join(splunk_home, relpath))
        # Check that we haven't escaped from intended parent directories.
        if os.path.relpath(fullpath, splunk_home)[0:2] == '..':
            raise ValueError('Illegal escape from parent directory "%s": %s' %
                             (splunk_home, fullpath))
        return fullpath


def add_to_sys_path(paths, prepend=False):
    for path in paths:
        if prepend:
            if path in sys.path:
                sys.path.remove(path)
            sys.path.insert(0, path)
        elif path not in sys.path:
            sys.path.append(path)


# Ensure the following paths are resolved first to avoid potential conflicts from other apps
add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib', 'SA_ITOA_app_common'])], prepend=True)

# Add import paths for other packages
add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-ITOA', 'lib'])])
add_to_sys_path([make_splunkhome_path(['etc', 'apps', 'SA-UserAccess', 'lib'])])
