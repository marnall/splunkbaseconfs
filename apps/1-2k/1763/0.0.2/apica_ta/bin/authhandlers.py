from requests.auth import AuthBase

"""
We may need this extension capability downstream; currently defaults to basic auth!
"""
class MyCustomAuth(AuthBase):
    def __init__(self,**args):
        pass
        
    def __call__(self, r):
        return r
