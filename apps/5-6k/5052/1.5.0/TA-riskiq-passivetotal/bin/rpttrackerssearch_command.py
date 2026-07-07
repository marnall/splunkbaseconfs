from command_base import CommandBase

TAB = 'trackers_search'
REQUIRED_PARAMS = ['query', 'type']


CommandBase(TAB, REQUIRED_PARAMS).start()
