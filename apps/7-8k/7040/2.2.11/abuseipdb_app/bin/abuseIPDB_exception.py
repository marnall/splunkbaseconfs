# This class is mainly used to raise exceptions in the AbuseIPDB custom script
# which don't need to have a stack trace printed
class AbuseIPDB_Exception(Exception):
    pass