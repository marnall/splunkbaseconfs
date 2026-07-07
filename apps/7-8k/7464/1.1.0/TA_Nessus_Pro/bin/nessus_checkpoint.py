import json
from datetime import datetime


class NessusBaseCheckpoint(object):
    """
    The base class of Nessus checkpoint
    """
    def __init__(self, logger, checkpointer, nessus_url, start_date=None):
        self.logger = logger
        self.checkpointer = checkpointer
        self.url = nessus_url
        self.start_date = start_date
        self.contents = {}
        self._reset_check_point()
        self.read()


    def _reset_check_point(self):
        """
        The method to reset the checkpoint
        """
        raise NotImplementedError("Derived class shall implement the function")


    def _get_content(self):
        """
        The method to get the content of the checkpoint.
        """
        return self.contents


    def read(self):
        """
        The method to read the checkpoint.
        """
        content = self.checkpointer.get()
        if content:
            ckpt = json.loads(content)
            self.contents = ckpt
        else:
            self._reset_check_point()


    def write(self):
        """
        The method to write checkpoint file.
        """
        _new_content = json.dumps(self.contents)
        self.checkpointer.update(_new_content)


    def delete(self):
        return self._reset_check_point()



class NessusScanCheckpoint(NessusBaseCheckpoint):
    """
    The class of Nessus Scan Checkpoint.
    The name of the checkpoint is "nessus_scan_<-the stanza of the input->.ckpt"
    The formate of checkpoint file is :
    {
        url_1:{
            "start_date": xxxxxxx,
            "scans": {
                scan_id_i:{
                    "history_id": history_id_i
                    },

                scan_id_j:{
                    "history_id": history_id_j
                },
                ...
            },
            "vulnerabilities": {
                "host-id": {
                    "vul-plugin-id": "last-scan-id"
                },
                ...
            }
        },
        ...
    }
    """

    def _reset_check_point(self):
        self.contents[self.url] = {}
        self.contents[self.url]["scans"] = {}
        self.contents[self.url]["start_date"] = self.start_date


    def is_new_scan(self, s_id, cur_h_id):
        """
        Check if there is a new scan.
        If the h_id of current scan is larger than the one in the checkpoint, it is a new scan.
        """
        if cur_h_id is not None and self.url in self.contents:
            ckpt_of_this_url = self.contents[self.url]
            if str(s_id) in ckpt_of_this_url.get("scans", {}):
                his_id = ckpt_of_this_url.get("scans", {}).get(str(s_id), {}).get("history_id")
                return cur_h_id > his_id
        elif cur_h_id is None:
            return False
        return True


    def is_new_host_scan(self, last_scan_end_time):
        """
        Check if there is new scan occured on the host. 
        If the last_scan_end_time is later than the one in the checkpoint, it's a new host scan.
        """
        if last_scan_end_time=="":
            return True
        last_scan_end_time = datetime.strptime(last_scan_end_time, "%a %b %d %H:%M:%S %Y")
        _start_date = datetime.strptime(self.start_date, "%Y/%m/%d")
        return last_scan_end_time >= _start_date


class NessusPluginCheckpoint(NessusBaseCheckpoint):
    """
    The class of Plugin Checkpoint.
    The name of the checkpoint is "nessus_plugin_<-the url->.ckpt"
    The format of checkpoint file is:
    {
        "start_date":xxxxxxx,
        "last_process_time": xxxxxxx,
        "plugin_ids":[plugin_id_1,plugin_id_2,...plugin_id_n]
    }
    """
    def _reset_check_point(self):
        self.contents["last_process_time"] = None
        self.contents["plugin_ids"] = []
        self.contents["start_date"] = self.start_date


    def is_there_updated_plugin(self, last_modified_time):
        """
        The method to check whether is there any plugin updated after the last scan.
        """
        ls_time = self.contents["last_process_time"]
        st_time = self.contents["start_date"]
        if ls_time is None:
            return True
        st_time = datetime.strptime(st_time, '%Y/%m/%d')
        ls_time = datetime.strptime(ls_time, '%Y/%m/%d')
        lm_time = datetime.strptime(last_modified_time, '%Y/%m/%d')
        return lm_time >= ls_time and lm_time >= st_time
