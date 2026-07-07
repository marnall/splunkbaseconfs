import configparser
import os


ta_name = 'TA-crowdstrike-identities'
config_file = os.path.sep.join([os.path.dirname(os.path.dirname(__file__)), 'default', 'app.conf'])
config = configparser.ConfigParser()
config.read(config_file)
APP_VERSION = config.get('launcher', 'version')
