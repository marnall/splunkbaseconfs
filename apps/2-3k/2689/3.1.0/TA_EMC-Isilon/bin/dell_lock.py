import os
import time
import errno
import threading

SPLUNK_HOME = os.environ.get("SPLUNK_HOME")
myapp = "TA_EMC-Isilon"


class JLockNotAcquired(Exception):
    pass


class JLock(object):
    def __init__(self, account_name, logger):
        self.lock_path = os.path.join(
            SPLUNK_HOME, "etc", "apps", myapp, "local", "{}.lock".format(account_name)
        )
        self.logger = logger

    def __enter__(self):
        retry = 5
        for _ in range(600):
            try:
                fd = os.open(self.lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                with os.fdopen(fd, "w") as lockfile:
                    # write the PID of the current process so you can debug
                    # later if a lockfile can be deleted after a program crash
                    lockfile.write(
                        str(os.getpid()) + " - " + str(threading.current_thread().ident)
                    )
                break
            except OSError as e:
                if e.errno == errno.EEXIST:  # Failed as file already exists.
                    self.logger.debug("message=lock_file_exists | Lock file already exists.")
                    time.sleep(1)
                elif e.errno == errno.EACCES:  # Failed to read the file.
                    retry -= 1
                    if retry >= 0:
                        time.sleep(1)
                    else:
                        raise
                else:
                    raise
        else:
            os.remove(self.lock_path)
            self.logger.debug("message=lock_file_removed | Lock file removed")
            raise JLockNotAcquired("Could not acquire the authentication lock")

    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            os.remove(self.lock_path)
            self.logger.debug("message=lock_file_removed | Lock file removed")
        except Exception:
            pass
