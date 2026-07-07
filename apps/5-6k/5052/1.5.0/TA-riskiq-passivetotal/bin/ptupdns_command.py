from command_base import CommandBase

TAB = 'ptupdns'
REQUIRED_PARAMS = ['query']
OPTIONAL_PARAMS = ['earliest', 'latest']


CommandBase(TAB, REQUIRED_PARAMS, OPTIONAL_PARAMS).start()
