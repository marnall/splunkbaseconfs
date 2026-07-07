import pickle
import os
import gzip
import sys

class Checkpointer:
    def __init__(self, checkpoint_dir, name, ew):
        self.checkpoint_file_name = "%s/%s.checkpoint" % (checkpoint_dir, name)
        self.ew = ew

    @property
    # Method to load checkpoint file
    def load(self):
        f = self._open_checkpoint_file("rb")
        if f is None:
            return

        try:
            checkpoint_pickle = pickle.load(f)
            f.close()
            return checkpoint_pickle
        except Exception as e:
            log_message = "Checkpointer: Error reading checkpoint pickle file '%s': %s" % (self.checkpoint_file_name, e)
            self.ew.write("ERROR", log_message)
            return {}

    # Method to open checkpoint file
    def _open_checkpoint_file(self, mode):
        if not os.path.exists(self.checkpoint_file_name):
            return None
        # try to open this file
        try:
            f = gzip.open(self.checkpoint_file_name, mode)
            return f
        except Exception as e:
            log_message = "Checkpointer: Error opening '%s': %s" % (self.checkpoint_file_name, e)
            self.ew.log("ERROR", log_message)
            return None

    # Method to update checkpoint file
    def update(self, events_dict):
        tmp_file = "%s.tmp" % self.checkpoint_file_name

        try:
            f = gzip.open(tmp_file, "wb")
            pickle.dump(events_dict, f)
            f.close()
            if os.path.exists(self.checkpoint_file_name):
                os.remove(self.checkpoint_file_name) 
            os.rename(tmp_file, self.checkpoint_file_name)
        except Exception as e:
            log_message = "Checkpointer: Failed to update checkpoint file: %s" % e
            self.ew.log("ERROR", log_message)