
import json
from io import open

import pytest

from kv_store import KVStore
from tests.mockers import EventWriter, Helper, KVStoreObject, ExpanseObject


@pytest.fixture
def ew():
    return EventWriter()


@pytest.fixture
def helper():
    return Helper()


@pytest.fixture
def kv_store_mock():
    return KVStoreObject('user', 'pass')


@pytest.fixture
def expanse_mock():
    return ExpanseObject()


@pytest.fixture
def auth_config():
    with open('testconfig.json', 'r') as f:
        config = json.load(f)
        return {
            "token": config.get("token")
        }


@pytest.fixture
def api_base_url():
    with open('testconfig.json', 'r') as f:
        config = json.load(f)
        return config.get("api_base_url")


@pytest.fixture
def kv_store_config():
    with open('testconfig.json', 'r') as f:
        config = json.load(f)
        return {
            "username": config.get("kv_store_username"),
            "password": config.get("kv_store_password"),
            "collection": config.get("kv_store_collection"),
        }


@pytest.fixture
def kv_store_object():
    with open('testconfig.json', 'r') as f:
        config = json.load(f)
        return KVStore(
            username=config.get("kv_store_username"),
            password=config.get("kv_store_password"),
            collection=config.get("kv_store_collection"),
        )


@pytest.fixture()
def kv_store_get_splunk_uri():
    return "https://localhost:8089/servicesNS/nobody/TA-expanse/storage/collections"
