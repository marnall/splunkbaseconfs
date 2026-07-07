from command_base import CommandBase

TAB = 'certificates'
REQUIRED_PARAMS = ['query']
OPTIONAL_PARAMS = ['field']


CommandBase(TAB, REQUIRED_PARAMS, OPTIONAL_PARAMS).start()
