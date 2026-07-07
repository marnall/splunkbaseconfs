# -*_coding: utf8  -*-

import hashlib
import types
# import shelve
from datetime import datetime
import re
import urllib
from pprint import pformat
from obs import ObsClient


def uni2str(f):
    def wrapper(*args, **kwargs):
        ret = f(*args, **kwargs)
        if isinstance(ret, unicode):
            ret = ret.encode("utf8")
        return ret
    return wrapper


def _get_md5_str(src):
    md5 = hashlib.md5()
    md5.update(src)
    return md5.hexdigest()


def class_decorator(cls):
    for attr_name in dir(cls):
        attr = getattr(cls, attr_name)
        if isinstance(attr, (types.MethodType, types.FunctionType)):
            setattr(cls, attr_name, uni2str(attr))
        elif isinstance(attr, property):
            setattr(cls, attr_name, property(uni2str(attr.fget), attr.fset, attr.fdel))
    return cls


class HuaweiCloudOBS(object):

    CheckPointNotExist, CheckPointExisted, CheckPointObsolete = "NotExist", "Existed", "Obsolete"

    @staticmethod
    def extract_info_from_resp(resp):
        _reserved_key = ["status", "body", "reason"]
        return {_key: resp.get(_key) for _key in _reserved_key}

    @class_decorator
    class OBSObject(object):
        def __init__(self, bucket_name, list_resp_item):
            self.__bucket_name = bucket_name
            self._item = list_resp_item

        @property
        def info(self):
            return {"etag": self.etag, "size": self.size, "last_modified": self.last_modified}

        @property
        def bucket_name(self):
            return self.__bucket_name

        @property
        def etag(self):
            """
            :rtype: str
            """
            return self._item.etag.strip("\"'")

        @property
        def is_appendable(self):
            """
            :rtype: bool
            """
            return self._item.isAppendable

        @property
        def key(self):
            """
            :rtype: str
            """
            return self._item.key

        @property
        def last_modified(self):
            """
            :rtype: str
            """
            return self._item.lastModified

        @property
        def last_modified_dt(self):
            """
            :rtype: datetime
            :return:
            """
            return datetime.strptime(self.last_modified, "%Y/%m/%d %H:%M:%S")

        @property
        def owner(self):
            """
            :rtype: dict
            """
            return self._item.owner

        @property
        def size(self):
            """
            :rtype: int
            """
            return self._item.size

        @property
        def storge_class(self):
            """
            :rtype: str
            """
            return self._item.storageClass

    def __init__(self, obs_client, helper):
        self.client = obs_client  # type: ObsClient
        self.helper = helper

        # Initialize check_point file
        self.stanza_name = self.helper.get_input_stanza_names()
        # self.cp_name = "cp_%s.data" % self.stanza_name
        # self.data_file = shelve.open(self.cp_name)

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    def create_check_point(self, object_item):
        """

        :type object_item: HuaweiCloudOBS.OBSObject
        :param object_item:
        :return:
        """
        _bucket_name = _get_md5_str(object_item.bucket_name)
        _obj_key = _get_md5_str(object_item.key)
        _key = "%s:%s" % (_bucket_name, _obj_key)
        # self.data_file[_key] = object_item.info
        self.helper.save_check_point(_key, object_item.info)

    def load_check_point(self, object_item):
        """

        :type object_item: HuaweiCloudOBS.OBSObject
        :param object_item:
        :return:
        """
        _bucket_name = _get_md5_str(object_item.bucket_name)
        _obj_key = _get_md5_str(object_item.key)
        _key = "%s:%s" % (_bucket_name, _obj_key)
        _data = self.helper.get_check_point(_key)
        if not _data:
            return self.CheckPointNotExist

        if _data["last_modified"] != object_item.last_modified or _data["size"] != object_item.size:
            self.helper.log_warning("Object(%s) in bucket(%s) has been modified!"
                                    % (object_item.key, object_item.bucket_name))
            return self.CheckPointObsolete

        return self.CheckPointExisted

    def delete_check_point(self, object_item):
        _bucket_name = _get_md5_str(object_item.bucket_name)
        _obj_key = _get_md5_str(object_item.key)
        _key = "%s:%s" % (_bucket_name, _obj_key)
        self.helper.delete_check_point(_key)

    def check_obsclient_response(self, resp, msg_base, expect_status=200):
        _msg = "%(base)s: %(info)s" % dict(base=msg_base, info=HuaweiCloudOBS.extract_info_from_resp(resp))
        if resp.status != expect_status:
            raise RuntimeError(_msg)
        else:
            self.helper.log_debug(_msg)

    def build_events_for_object(self, obs_object, chunk_size=512 * 1024):
        """
        :type obs_object: HuaweiCloudOBS.OBSObject
        :param obs_object: OBSObject instance for one obs-object
        :param chunk_size: Chunk data size for each reading operation from remote ObsObject
        :return:
        """

        bucket_name = obs_object.bucket_name
        tmp_resp = self.client.getObject(bucket_name, obs_object.key, loadStreamInMemory=False)
        _msg_base = "Download object(%s) in bucket(%s)" % (obs_object.key, bucket_name)
        self.check_obsclient_response(tmp_resp, _msg_base)

        _url = urllib.quote("%s/%s" % (bucket_name, obs_object.key))
        # _source = "%(src)s:%(obj_url)s" % dict(src=self.helper.get_input_type(), obj_url=_url)
        _source = _url

        md5, read_size = hashlib.md5(), 0
        _reserved_line = None
        _events = []
        _chunk_size = max(64 * 1024, min(2 * 1024 ** 2, chunk_size))

        while True:
            _data = tmp_resp.body.response.read(_chunk_size)
            if not _data:
                break

            md5.update(_data)
            read_size += len(_data)
            _new_event = self.helper.new_event(
                source=_source,
                index=self.helper.get_output_index(),
                sourcetype=self.helper.get_sourcetype(),
                data=_data,
                done=False)

            _events.append(_new_event)

        expect_md5 = md5.hexdigest()
        real_etag = tmp_resp.body.etag.strip("\"'")
        if expect_md5 != real_etag:
            self.helper.log_warning("The object(%s) in bucket(%s) has invalid etag: expected_etag=%s, real_md5=%s" %
                                    (obs_object.key, bucket_name, expect_md5, real_etag))

        expect_size = tmp_resp.body.contentLength
        if read_size != expect_size:
            self.helper.log_error(
                "The bytes size of object(%s) in bucket(%s) is invalid: expected_size=%s, real_size=%s" %
                (obs_object.key, bucket_name, expect_size, read_size))
            return []
        return _events

    def send_events(self, event_writer, bucket_name, prefix=None, delimiter=None, object_name_pattern=None):
        """

        :param event_writer:
        :param bucket_name:
        :param prefix:
        :param delimiter:
        :param object_name_pattern:
        :return:
        """
        marker = None
        _obj_count = 0
        _obj_pattern = re.compile(object_name_pattern) if object_name_pattern else None

        def _is_key_match(_key):
            if _key == prefix:
                return False
            elif _obj_pattern and (not re.search(_obj_pattern, _key.split("/")[-1])):
                return False
            else:
                return True

        while True:
            resp = self.client.listObjects(bucket_name, prefix=prefix, delimiter=delimiter, max_keys=1000,
                                           marker=marker)
            self.check_obsclient_response(resp, "List objects of bucket(%s)" % bucket_name)
            self.helper.log_debug("List objects of bucket(%s): %s" % (bucket_name, pformat(resp)))

            for _obj in (HuaweiCloudOBS.OBSObject(bucket_name, _item) for _item in resp.body.contents
                         if _is_key_match(_item.key)):
                check_point_stat = self.load_check_point(_obj)
                if check_point_stat == self.CheckPointExisted:
                    self.helper.log_debug("Object(%s) in bucket(%s) has been indexed" % (_obj.key, _obj.bucket_name))
                    # self.delete_check_point(_obj)
                    continue

                _events = self.build_events_for_object(_obj)
                if len(_events) > 0:
                    self.create_check_point(_obj)
                    _obj_count += 1
                    _events[-1].done = True

                for _event in _events:
                    event_writer.write_event(_event)

            if not resp.body.is_truncated:
                break
            marker = resp.body.next_marker

        return _obj_count
