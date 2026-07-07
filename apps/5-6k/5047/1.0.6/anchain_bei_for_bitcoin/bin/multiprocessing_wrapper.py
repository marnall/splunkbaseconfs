import multiprocessing

def multiprocessor(pools, func, params):
    pool = multiprocessing.Pool(pools)
    #function = getattr(func)
    output = pool.map(func, *params)
    return output