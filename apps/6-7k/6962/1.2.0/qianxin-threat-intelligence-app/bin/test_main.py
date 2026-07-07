#!/usr/bin/python
# -*- coding: utf-8 -*-
# @ 南无阿弥陀佛，不要有太多bug……
# @ Author: tukechao
# @ Date: 2022-11-04 11:52:29
# @ LastEditors: tukechao
# @ LastEditTime: 2023-02-20 13:21:57
# @ FilePath: /splunk-app/bin/test_main.py
# @ description:test unit

import unittest
import time
import sys
import os
import random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "qianxin_ti")))

from qianxin_ti.model_log_detection_source import *
from qianxin_ti.model_tip_local import *
from qianxin_ti.model_log_detection import *
from qianxin_ti.common_request_util import requests_api
from cmd_qax_ti_log_detection import TipLogDetectionBackgroundWorker
from qianxin_ti.common_lib_entry import pysnooper
from qianxin_ti.common_indexes_helper import SplunkIndexesHelper, SplunkIndexConn
from qianxin_ti.common_util import QianxinConfHelper, MockApiHelper
from qianxin_ti.common_kvstore_helper import SplunkKvstoreHelper

from qianxin_ti.common_constants import *


class TestFunctions(unittest.TestCase):
    def setUp(self):
        self._service = QianxinConfHelper.get_splunk_service()

    def test_certification(self):
        print("~~~~Test TIP connection~~~~")
        tip_token_res = QianxinConfHelper.verify_current_tip_token()
        # make sure we can get tip connection
        self.assertNotEqual(tip_token_res, None)

    def test_index_operations(self):
        """
        :description: test index operations.
        :param self :
        :return:
        """
        idx_helper = SplunkIndexesHelper(self._service)
        # prepare
        name = "qax_ti_unit_test"
        if idx_helper._exist_index(name):
            self._service.indexes[name].enable()
            self._service.indexes.delete(name)

        # test create
        self.assertTrue(idx_helper.create(name), "create index")
        self.assertFalse(idx_helper.create(name), "duplicate create idx")
        # test event
        idx_conn = SplunkIndexConn(self._service, name)
        self.assertTrue(idx_conn.insert("this is test event"), "add event")
        self.assertEqual(idx_helper.list_index(name)[name], "1", "event count 1")
        time.sleep(1)
        idx_conn.roll_hot_buckets()
        self.assertTrue(idx_conn.insert("this is test event 2"), "add event")
        self.assertEqual(idx_helper.list_index(name)[name], "2", "event count")
        # test delete
        self.assertTrue(idx_helper.delete(name), "delete index")
        self.assertFalse(idx_helper._exist_index(name), "check deleted")

    def test_model_tip_local(self):
        """
        :description: test those apis
        :param self :
        :return:
        """
        # check the home_page_statistics
        hp_file = os.path.join(TIP_HOME_STATISTIC_FILE_PATH, TIP_HOME_STATISTIC_FILE_NAME)
        print(hp_file)
        self.assertTrue(os.path.exists(hp_file))

        # check each api
        _api = MockApiHelper()
        _api.args = dict(unit="week", type="url")
        self.assertTrue(IocManualModel, _api)
        _api.args = dict(unit="month")
        self.assertTrue(IntelligenceLevelModel, _api)
        _api.args = dict(type="compromise")
        self.assertTrue(StatisticMatchLogModel, _api)
        _api.args = dict(unit="day", type="compromise", view="compromise")
        self.assertTrue(StatisticVisualModel, _api)

        self.assertTrue(StatisticModel, _api)
        self.assertTrue(HotStaticModel, _api)
        self.assertTrue(VulnerabilityModel, _api)
        self.assertTrue(NoticeModel, _api)
        self.assertTrue(IocManualSummaryModel, _api)

    def _check_api_result(self, Model, api_obj):
        t = Model(api_obj)
        res = t.run()
        if res.get("status") == "2000":
            return True
        else:
            return False

    def tearDown(self) -> None:
        name = "qax_ti_unit_test"
        idx_helper = SplunkIndexesHelper(self._service)
        idx_helper.delete(name)


class TestLogDetectionSource(unittest.TestCase):
    def test_input_mapping(self):
        r = self._mapping_func(
            "post_source",
            "unit_test_" + str(random.randint(1, 1000000)),
            "unit test map " + str(random.randint(1, 1000)) + "|rename xx as destination_ip,xxx as source_ip",
        )
        self.assertTrue(r[0], "add new source mapping")
        cur_id = r[1]
        new_name = "unit_test" + str(random.randint(1, 1000000))
        new_map_str = "unit test map " + str(random.randint(1, 1000)) + "|rename xx as destination_ip,xxx as source_ip"
        r1 = self._mapping_func("put_source", new_name, new_map_str, id=cur_id)
        self.assertTrue(r1[0], "modify the mapping")
        r2 = self._mapping_func("delete_source", new_name, new_map_str, id=cur_id)
        self.assertFalse(r2[0], "delete the mapping")

    def _mapping_func(self, func, name, map_str, id=""):
        _api = MockApiHelper()
        _api.json.update({"string_mapping": map_str, "name": name})
        if id:
            _api.json.update({"id": id})
            _api.args.update({"id": id})
        _api.args.update({"offset": 0, "limit": 1000})
        lds = LogDetectionSourceModel(_api)
        func = getattr(lds, func)
        func()
        d = lds.get_source()
        data = parser_response(d)
        flag = False
        cur_map_list = data["items"]
        for m in cur_map_list:
            if m["name"] == name and m["string_mapping"] == map_str:
                flag = True
                _id = m["id"]
        print(flag)
        if flag:
            return (True, _id)
        else:
            return (False, "")


class TestLogDetection(unittest.TestCase):
    """Test case for LogDetection. As a result, this test case will generate a bunch of Test events and insert them into database."""

    def setUp(self):
        # first clean the current log
        self._service = QianxinConfHelper.get_splunk_service()
        self._index_helper = SplunkIndexesHelper(self._service)
        self._index_conn = SplunkIndexConn(self._service, MALICIOUS_LOG_INDEX_NAME)
        self._index_conn.clean_idx()
        # self._index_conn_http = SplunkIndexConn(self._service, "test_http_input")
        # self._index_conn_http.clean_idx()

    def test_file_input_events(self):
        worker = TipLogDetectionBackgroundWorker()
        self.assertTrue(worker._kv_helper.create_kv_if_not_exist(LD_SOURCE_KV_STORE))
        self.input_event()
        # filepath = os.path.abspath(os.path.join(os.path.dirname(__file__), "testcases", "input_log_example", "log.log"))
        one_map = 'index="test_http_input"|rename dip as destination_ip,sip as source_ip'
        maps = [one_map]
        iocs = worker.get_data_from_mapping(maps)
        worker.save_log_detection_summary(len(iocs))
        if QianxinConfHelper.get_current_base_version() == "local":
            events = worker.local_log_detection(iocs, maps)
        print(events)
        worker.submit_events(events)
        cnt = len(events)

    def input_event(self):
        token = "2375de41-bd05-409a-a088-c72d7ab7cfa5"
        url = "https://localhost:8088/services/collector/event"
        headers = {"Authorization": f"Splunk {token}"}
        body = dict(sip="123.123.123.123", dip="188.166.0.125")
        res = requests_api.query_common(url=url, method="POST", headers=headers, data=body)
        print(res)


class TdeIntegration(unittest.TestCase):
    def setUp(self):
        pass

    def test_malicious_family_data_import(self):
        _api = MockApiHelper()
        mf = LogDetectionMaliciousFamilyInfoModel(_api)
        mf.update_malicious_family_info_info()
        kv_conn = SplunkKvstoreHelper(MALICIOUS_FAMILY_INFO_KV_STORE)
        res = kv_conn.query_by_id("Morto")
        logger.debug(res)
        keys_l = ["platform", "description", "malicious_family", "malicious_type", "risk", "_key", "reference"]
        for k in res.keys():
            self.assertTrue(k not in keys_l, "mf key error")


class TdeRichData(unittest.TestCase):
    def setUp(self):
        pass

    def test_rich_data(self):
        test_cases = ["lbertussbau.com", "81.95.7.12"]
        raw = [{"destination_ip": "81.95.7.12", "source_ip": "5.5.5.5"}]
        h = TdeLDHelper()
        r = h.process_data(test_cases, raw)
        print(r)


def md5_base64_byte(string: str) -> str:
    m = hashlib.md5()
    m.update(string.encode("utf-8"))
    md5_str = m.digest()
    b64_str = base64.b64encode(md5_str)
    return b64_str.decode("utf-8")


def parser_response(res):
    return res.get("payload").get("data")


if __name__ == "__main__":
    # unittest.main()
    runner = unittest.TextTestRunner()
    log_source_suite = unittest.makeSuite(TestLogDetectionSource)
    log_detection_suite = unittest.makeSuite(TestLogDetection)
    tde_suite = unittest.makeSuite(TdeIntegration)
    tde_rich_suite = unittest.makeSuite(TdeRichData)
    # 日志源配置单元测试
    # runner.run(log_source_suite)
    # 日志检测单元测试
    # runner.run(log_detection_suite)
    # tde加载测试
    # runner.run(tde_suite)
    # 日志富化测试
    runner.run(tde_rich_suite)
