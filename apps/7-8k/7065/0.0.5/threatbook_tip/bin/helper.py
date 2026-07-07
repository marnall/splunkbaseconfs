# -*- coding=utf-8 -*-
# import json


class Helper(object):

    @staticmethod
    def getv(src_dict, keypath, splitchr="."):

        def getsub(sitem, key_list):
            if not key_list:
                return None
            this_key = key_list.pop(0)
            # print(key_list)
            is_last = False if key_list else True
            if type(sitem) is list and not this_key.isnumeric():
                return None
            this_key = int(this_key) if type(sitem) == list else this_key
            try:
                if is_last:
                    return sitem[this_key]
                else:
                    next_sitem = sitem[this_key]
                    return getsub(next_sitem, key_list)
            except Exception:
                return None

        skey_list = keypath.split(splitchr)
        return getsub(src_dict, skey_list)

    @staticmethod
    def getv_with_nullstr(src_dict, keypath, splitchr="."):

        def getsub(sitem, key_list):
            if not key_list:
                return ""
            this_key = key_list.pop(0)
            # print(key_list)
            is_last = False if key_list else True
            if type(sitem) is list and not this_key.isnumeric():
                return ""
            this_key = int(this_key) if type(sitem) == list else this_key
            try:
                if is_last:
                    return sitem[this_key]
                else:
                    next_sitem = sitem[this_key]
                    return getsub(next_sitem, key_list)
            except Exception:
                return ""

        skey_list = keypath.split(splitchr)
        return getsub(src_dict, skey_list)

    @staticmethod
    def search_value_use_json(src_dict, key_word):

        def searchsub(sitem, key_word: str):
            return_list = []
            is_have = False
            if type(sitem) is list or type(sitem) is tuple:
                for i in range(0, len(sitem)):
                    v_str = str(sitem[i])
                    # print(v_str)
                    if key_word in v_str:
                        result, include_list = searchsub(sitem[i], key_word)
                        if result:
                            if len(include_list) == 0:
                                return_list.append(i)
                            else:
                                for sub_in in include_list:
                                    return_list.append("%d.%s" % (i, sub_in))
                            is_have = True
            elif type(sitem) is dict:
                for skey, sval in sitem.items():
                    v_str = str(sval)
                    if key_word in v_str:
                        result, include_list = searchsub(sval, key_word)
                        if result:
                            if len(include_list) == 0:
                                return_list.append(skey)
                            else:
                                for sub_in in include_list:
                                    return_list.append("%s.%s" % (skey, sub_in))
                            is_have = True
            else:
                if key_word in str(sitem):
                    is_have = True
            # print(return_list)
            return is_have, return_list

        result, re_list = searchsub(src_dict, key_word)
        return re_list


# if __name__ == "__main__":
#     sr = '{"project":{"id":10801},"status":{"name":"待补全信息","test":[{"1":"sss","ss":"cvvv"},[4,5,6,7],{"aa":"bbb"}]},"summary":"PythonTestIssue","description":"FangdongdongTest","issuetype":{"name":"设备流转"},"customfield_11202":{"requestType":{"name":"设备流转工单"}},"customfield_11404":{"value":"华东"},"customfield_11403":{"name":"fangdongdong"},"customfield_11405":[{"value":"TDP"}],"customfield_11406":[{"value":"微步设备"}],"customfield_11216":"94000000000000001"}'
#     i = json.loads(sr)
#     print(Helper.getv(i, "status.test.n0.1"))
