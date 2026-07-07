
# encoding = utf-8

import os
import sys
import time
import datetime
import string
import json

from elasticsearch import Elasticsearch, serializer, compat, helpers

class JSONSerializer4Python(serializer.JSONSerializer):
    def dumps(self, data):
        if isinstance(data, compat.string_types):
            return data
        try:
            return json.dumps(data, default=self.default, ensure_ascii=True)

        except (ValueError, TypeError) as e:
            raise exceptions.SerializationError(data, e)

def isCheckpoint(check_file, _id):
    with open(check_file, 'r') as file:
        log_list = file.read().splitlines()
        return ( _id in log_list)

def write2Checkpoint(check_file, _id):
    with open(check_file,'a') as file:
        file.writelines( _id + '\n')

def write2Splunk(helper, ew, data, dt_time, opt_cust_source_type, opt_elasticsearch_indice):
    event = helper.new_event(data, time=dt_time, host=None, source=opt_elasticsearch_indice, sourcetype=opt_cust_source_type, done=True, unbroken=True)

    try:
        ew.write_event(event)
    except Exception as e:
        raise e

def search_index(instance_url, port, user, secret, index_name, datetime_field, from_date, size, from_number, ca_certs_path):
    """
    Args:
        index_name: name of the index to search.
        datetime_field: name of the datetime field to search.
        from_date: start date for the search.
        size: number of documents to return.
        from_number: starting index for pagination.

    Returns:
        A list of documents matching the query.
    """

    # Elasticsearch 8.8.1 compatible
    if ca_certs_path:
        client = Elasticsearch(
            hosts=[{
            "host": instance_url,
            "port": port,
            "scheme": "https",
        }],
            verify_certs=True,
            ca_certs=ca_certs_path,
            headers={"Content-Type": "application/json"},
            basic_auth=(user, secret)
        )
    else:
        client = Elasticsearch(
            hosts=[{
            "host": instance_url,
            "port": port,
            "scheme": "https",
        }],
            verify_certs=True,
            headers={"Content-Type": "application/json"},
            basic_auth=(user, secret)
        )

    # Create the initial search query.
    search_query = {
            "bool": {
                "must": [
                    {
                        "range": {
                            datetime_field: {
                                "gte": "now-" + from_date,
                                "lte": "now"
                            }
                        }
                    }
                ]
            }
    }

    search_params = {
        "index": index_name,
        "query": search_query,
        "size": size,
        "from": from_number,
    }

    # Perform the initial search.
    response = client.search(**search_params, scroll="1m")
    scroll_id = response["_scroll_id"]
    hits = response["hits"]["hits"]

    # Store the initial hits in a list
    all_hits = hits

    while len(hits) > 0:
        # Perform the scroll request
        response = client.scroll(scroll_id=scroll_id, scroll="1m")
        scroll_id = response["_scroll_id"]
        hits = response["hits"]["hits"]

        # Append the hits to the list
        all_hits.extend(hits)

    # Return the results.
    return all_hits


def validate_input(helper, definition):
     elasticsearch_instance_url = definition.parameters.get('elasticsearch_instance_url', None)
     port = definition.parameters.get('port', None)
     ca_certs_path = definition.parameters.get('ca_certs_path', None)
     user = definition.parameters.get('user', None)
     secret = definition.parameters.get('secret', None)
     elasticsearch_indice = definition.parameters.get('elasticsearch_indice', None)
     date_field_name = definition.parameters.get('date_field_name', None)
     time_preset = definition.parameters.get('time_preset', None)
     cust_source_type = definition.parameters.get('cust_source_type', None)

def collect_events(helper, ew):
    opt_elasticsearch_instance_url = helper.get_arg('elasticsearch_instance_url')
    opt_port = int(helper.get_arg('port'))
    opt_ca_certs_path = helper.get_arg('ca_certs_path')
    opt_user = helper.get_arg('user')
    opt_secret = helper.get_arg('secret')
    opt_elasticsearch_indice = helper.get_arg('elasticsearch_indice')
    opt_date_field_name = helper.get_arg('date_field_name')
    opt_time_preset = helper.get_arg('time_preset')
    opt_cust_source_type = helper.get_arg('cust_source_type')

    if opt_cust_source_type == '':
        opt_cust_source_type = 'json'

    opt_ca_certs_path = opt_ca_certs_path.strip()
    
    size = 1000
    from_number = 0


    results = search_index(opt_elasticsearch_instance_url, opt_port, opt_user, opt_secret, opt_elasticsearch_indice, opt_date_field_name, opt_time_preset, size, from_number, opt_ca_certs_path)

    check_file = os.path.join('/', os.path.dirname(os.path.abspath(__file__)), 'checkpoint', 'checkpointElastic')

    for doc in results:
        dt_time = doc['_source'][opt_date_field_name]
        _id = json.dumps(doc['_id'])

        data = json.dumps(doc['_source'], ensure_ascii=False)

        if data[:2] == "b'":
            data = data[2:-1]

        if not isCheckpoint(check_file, _id):
            write2Checkpoint(check_file, _id)

            write2Splunk(helper, ew, data, dt_time, opt_cust_source_type, opt_elasticsearch_indice)