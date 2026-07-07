from command_base import CommandBase

TAB = 'whois'
REQUIRED_PARAMS = ['query']


CommandBase(TAB, REQUIRED_PARAMS).start()
