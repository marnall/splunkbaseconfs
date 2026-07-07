""" This module contains helper functions for JSON

"""
from __future__ import print_function
import json
from collections import OrderedDict

default_ignore_keys = ['epochUUID', 'epochWID', 'fabricUUID', 'fabric_id', 'uuid', 'links', 'ep_key',
                       'node_id', 'mos_md5', 'epoch_id', 'epoch_uuid', 'detection_time']


def sort_by_keys(json_string):
    """
    sorts JSON string by keys
    :param json_string:
    :return: decorated json string with sorted keys
    """
    json_obj = json.loads(json_string, object_pairs_hook=OrderedDict)
    return json.dumps(json_obj, sort_keys=True)


def remove_keys_from_dict(json_obj, keys):
    """
    Remove keys from input dictionary. Function removed keys recursively
    :param json_obj: Dictionary representation of valid JSON
    :param keys: Array containing keys
    :return: None
    """

    # 1. check if input is dictionary or not
    if not isinstance(json_obj, (dict, list)):
        return

    # 2. iterate through key and delete them in exist in dictionary
    if isinstance(json_obj, dict):
        for key in keys:
            if key in json_obj:
                del json_obj[key]

        # check if there is nested dictionary or list
        for element in json_obj.keys():
            if isinstance(json_obj[element], dict) or isinstance(json_obj[element], list):
                remove_keys_from_dict(json_obj[element], keys)

    # 3. iterate through list items and find if there are any dict or list
    if isinstance(json_obj, list):
        for item in json_obj:
            if isinstance(item, dict) or isinstance(item, list):
                remove_keys_from_dict(item, keys)


def remove_keys_from_json(json_string, keys):
    """
    Remove specified keys from input JSON. Function removed keys recursively
    :param json_string: Valid JSON in string format
    :param keys: Array containing keys
    :return:
    """
    json_dict = json.loads(json_string, object_pairs_hook=OrderedDict)
    remove_keys_from_dict(json_dict, keys)
    return json.dumps(json_dict, sort_keys=True)


# Sorts a json object
def ordered(obj, ignore_keys):
    if isinstance(obj, dict):
        return sorted((k, ordered(v, ignore_keys)) for k, v in obj.items() if k not in ignore_keys)
    if isinstance(obj, list):
        return sorted(ordered(x, ignore_keys) for x in obj)
    else:

        return obj


def is_equal(json_string1, json_string2, ignore_keys=None):
    """
    Compares the two JSONs
    :param json_string1: JSON in string format, all spaces/tabs/lines removed
    :param json_string2: JSON in string format, all spaces/tabs/lines removed
    :param ignore_keys: List of keys to be ignored while comparing, this is an optional parameter
    :return: True if JSONs are equal, False otherwise
    """
    if ignore_keys is not None:
        ignore_keys.extend(default_ignore_keys)
    else:
        ignore_keys = default_ignore_keys

    json_obj1 = json.loads(json_string1, encoding='utf-8', object_pairs_hook=OrderedDict)
    json_obj2 = json.loads(json_string2, encoding='utf-8', object_pairs_hook=OrderedDict)

    # If data length is not same, don't even compare them
    assert (json_obj1['value']['data_summary']['total_count'] == json_obj2['value']['data_summary']['total_count']),\
        'total_count in expected and actual JSON is NOT EQUAL' + '\n' +\
        "BOTH JSONs ARE NOT EQUAL\n Actual json ====>" + json_string1 \
        + "\n Expect json ====>" + json_string2

    out_json_obj1 = ordered(json_obj1, ignore_keys)
    out_json_obj2 = ordered(json_obj2, ignore_keys)
    # print 'ORDERED ACTUAL DICT ====>' + str(out_json_obj1)
    # print 'ORDERED EXPECT DICT ====>' + str(out_json_obj2)
    if out_json_obj1 == out_json_obj2:
        # print "BOTH JSONs ARE EQUAL"
        return True
    else:
        # print "BOTH JSONs ARE NOT EQUAL\n Actual json ====>" + json_string1 \
        #       + "\n Expect json ====>" + json_string2
        return False


def merge_pages(page_list):
    """
    Merge pages pages passed in as list at data[] level
    :param: page_list: list of JSON pages in string format
    :return: merged JSON
    """
    # all pages will be merged in first page
    total_pages = len(page_list)
    # print 'merging ' + str(total_pages) + ' pages'
    first_page_str = page_list[0]
    merged_pages_obj = json.loads(first_page_str)
    if total_pages > 1:
        for num in range(1, total_pages):
            next_page_obj = json.loads(page_list[num])
            merged_pages_obj.get('value', {}).get('data', []).extend(next_page_obj.get('value', {}).get('data', []))

    merged_json_str = json.dumps(merged_pages_obj, sort_keys=True)
    return merged_json_str


def check_if_two_json_files_are_same(file1, file2):
    """
    This function is only used for debugging when test case fails

    :param file1:
    :param file2:
    :return:
    """
    with open(file1) as json1_data:
        json1_str = json.dumps(json.load(json1_data))

    with open(file2) as json2_data:
        json2_str = json.dumps(json.load(json2_data))

    # print is_equal(json1_str, json2_str)


# main entry point to test functions
if __name__ == "__main__":
    """
    Main entry point. It essentially contains test code to test above functions
    """
    check_if_two_json_files_are_same('json1', 'json2')
    exit(0)

    # sort keys
    print(sort_by_keys('{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                       ' "bar": 2, "amazing":"qqq"}'))

    print(remove_keys_from_json('{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                                ' "bar": 2, "zebra": "yes", "amazing":"qqq",'
                                '  "array1":["a","b", {"foo":"f", "bar":"b"}]}', ['foo']))

    print(remove_keys_from_json('{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                                ' "bar": 2, "zebra": "yes", "amazing":"qqq", "field1":{"foo":"222", "bar":"111"},'
                                '  "array1":["a","b", {"foo":"f", "bar":"b"}]}', ['foo']))

    # remove foo
    print(remove_keys_from_json('{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                                ' "bar": 2, "zebra": "yes", "amazing":"qqq", "field1":{"foo":"222", "bar":"111"}}',
                                ['foo']))

    # remove foo and bar both
    print(remove_keys_from_json('{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                                ' "bar": 2, "zebra": "yes", "amazing":"qqq", "field1":{"foo":"222", "bar":"111"}}',
                                ['foo', 'bar']))

    # remove nothing
    print(remove_keys_from_json('{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                                ' "bar": 2, "zebra": "yes", "amazing":"qqq", "field1":{"foo":"222", "bar":"111"}}',
                                []))

    print(remove_keys_from_json('["zebra", "lion", {"foo": "f", "bar": "b"}]', ['foo']))

    print(remove_keys_from_json('{"array":["a","b", {"foo":"f", "bar":"b"}]}', ['foo']))

    # test if both JSONs are equal
    print(is_equal('{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                   ' "bar": 2, "amazing":"qqq", "junk":"junk"}',
                   '{"foo":{"zoo":5, "arrow":7, "embed": {"gift_card":"abc", "cool_stuff":"nnn"}},'
                   ' "bar": 2, "amazing":"qqq"}', ['junk']))