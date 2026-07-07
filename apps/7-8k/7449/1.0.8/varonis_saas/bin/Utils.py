import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "lib"))


def argToList(arg, separator='|', transform=None):
    if not arg:
        return []

    result = [s.strip() for s in arg.split(separator)]
    if 'All' in result:
        result = []

    if transform:
        return [transform(s) for s in result]

    return result
