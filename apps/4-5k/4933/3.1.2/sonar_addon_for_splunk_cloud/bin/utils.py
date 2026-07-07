import sys

if sys.version_info >= (3, 0):
    string = (str, bytes)
    number = int
else:
    import __builtin__
    string = __builtin__.basestring
    number = (int, long)
