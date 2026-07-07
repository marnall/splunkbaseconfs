from command_base import CommandBase

TAB = 'whois_search'
REQUIRED_PARAMS = ['query', 'field']


CommandBase(TAB, REQUIRED_PARAMS).start()
