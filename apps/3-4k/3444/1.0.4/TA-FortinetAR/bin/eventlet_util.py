import os

import eventlet


def monkey_patch():
    # NOTE(slaweq): to workaround issue with import cycles in
    # eventlet < 0.22.0;
    # This issue is fixed in eventlet with patch
    # https://github.com/eventlet/eventlet/commit/b756447bab51046dfc6f1e0e299cc997ab343701
    # For details please check https://bugs.launchpad.net/neutron/+bug/1745013
    eventlet.hubs.get_hub()
    if os.name != 'nt':
        eventlet.monkey_patch()
    else:
        # eventlet monkey patching the os module causes subprocess.Popen to
        # fail on Windows when using pipes due to missing non-blocking IO
        # support.
        eventlet.monkey_patch(os=False)
