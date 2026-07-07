from command_base import CommandBase

TAB = 'hostpairs'
REQUIRED_PARAMS = ['query']
OPTIONAL_PARAMS = ['direction']


CommandBase(TAB, REQUIRED_PARAMS, OPTIONAL_PARAMS).start()
