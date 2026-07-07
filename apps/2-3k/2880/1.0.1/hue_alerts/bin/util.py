def merge(*dicts):
    res = dict()
    for d in dicts:
        res.update(d)
    return res

