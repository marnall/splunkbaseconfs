import sys
from splunk import Intersplunk
from splunk_logger import setup_logging
from utils import load_pyden_config, write_pyden_config


def main(dist, env):
    pm_config, config = load_pyden_config()
    pyden_location = pm_config.get('appsettings', 'location')
    if dist:
        if dist in config.sections():
            write_pyden_config(pyden_location, config, "default-pys", "distribution", dist)
        else:
            Intersplunk.generateErrorResults("The Python version %s is not installed yet." % dist)
            sys.exit(1)
    if env:
        if env in config.sections():
            write_pyden_config(pyden_location, config, "default-pys", "environment", env)
        else:
            Intersplunk.generateErrorResults("The virtual environment %s does not exist." % env)
            sys.exit(1)
    Intersplunk.outputResults([{"message": "Successfully changed defaults"}])


if __name__ == "__main__":
    logger = setup_logging()
    distribution = False
    environment = False
    for arg in sys.argv:
        if "distribution" in arg:
            distribution = arg.split("=")[1]
        if "environment" in arg:
            environment = arg.split("=")[1]
    if not (distribution or environment):
        Intersplunk.generateErrorResults(
            "The changedefaultpys command requires at least one argument of distribution or environment")
        logger.error("The changedefaultpys command requires at least one argument of distribution or environment")
        sys.exit(1)
    else:
        main(distribution, environment)
