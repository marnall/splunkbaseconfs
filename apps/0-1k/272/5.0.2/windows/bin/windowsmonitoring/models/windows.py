from splunk.models.base import SplunkAppObjModel
from splunk.models.field import Field, BoolField

'''
Provides object mapping for the unix conf file
'''

class Windows(SplunkAppObjModel):
    
    resource              = 'windows/windows_conf'
    has_ignored           = BoolField()
