# Copyright (C) 2005-2024 Splunk Inc. All Rights Reserved.


class UserAccessError(Exception):
    '''
    Set the status and msg on the response
    Ex: raise UserAccessError(status=500, message="Bad User name")
    '''

    def __init__(self, status=500, message=None):
        self.status = status = int(status)
        if status < 400 or status > 599:
            raise ValueError("status must be between 400 and 599.")
        # See http://www.python.org/dev/peps/pep-0352/
        # self.message = message
        self._message = message
        Exception.__init__(self, status, message)

    def __call__(self):
        raise self

# Following classes have been defined to help us filter out the different exception types...
class BadRequest(Exception):
    '''
    class to indicate a bad request
    '''
    pass
