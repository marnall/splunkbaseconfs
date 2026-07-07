import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))

import config
from axis_streamer_app import AxisStreamerApp, init_from_configuration

if __name__ == "__main__":
    settings = init_from_configuration(config)
    sys.exit(AxisStreamerApp(settings).run(sys.argv))
