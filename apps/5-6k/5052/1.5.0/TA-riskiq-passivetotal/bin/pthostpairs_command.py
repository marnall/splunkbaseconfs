from command_base import CommandBase

TAB = 'pthostpairs'
REQUIRED_PARAMS = ['query', 'direction']


CommandBase(TAB, REQUIRED_PARAMS).start()
