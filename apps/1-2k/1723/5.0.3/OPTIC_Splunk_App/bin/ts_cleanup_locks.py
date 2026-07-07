'''
Created on Mar 2, 2016
'''
from settings import get_working_dir
import os, traceback
SEARCH_RUN_LOCK = os.path.join(get_working_dir(), ".search_running")
BACKFILL_RUN_LOCK = os.path.join(get_working_dir(), ".backfill_running")
if __name__ == '__main__':
    try:
        if os.path.exists(SEARCH_RUN_LOCK):
            os.remove(SEARCH_RUN_LOCK)
            print("delete %s" % SEARCH_RUN_LOCK)
        if os.path.exists(BACKFILL_RUN_LOCK):
            os.remove(BACKFILL_RUN_LOCK)
            print("delete %s" % BACKFILL_RUN_LOCK)
    except Exception as e:
        print(traceback.format_exc())